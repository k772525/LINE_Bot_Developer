import os
import tempfile
import traceback
import asyncio
import concurrent.futures
import threading
from io import BytesIO
from typing import Optional, Tuple
import hashlib
import time

from google.cloud import speech
from pydub import AudioSegment
from pydub.exceptions import CouldntDecodeError
import pymysql

from ..utils.db import DB
from flask import current_app

# 全域變數來追蹤 FFmpeg 警告是否已顯示
_ffmpeg_warning_shown = False

# 語音快取系統
_voice_cache = {}
_cache_lock = threading.Lock()
CACHE_EXPIRY_SECONDS = 300  # 5分鐘快取

class VoiceService:
    """語音輸入處理服務"""
    
    def __init__(self):
        self.speech_client = speech.SpeechClient()
    
    @staticmethod
    def download_audio_content(message_id: str, line_bot_api) -> Optional[bytes]:
        """
        從LINE下載語音檔案內容
        
        Args:
            message_id: LINE消息ID
            line_bot_api: LINE Bot API實例
            
        Returns:
            語音檔案的bytes內容，失敗時返回None
        """
        try:
            download_start_time = time.time()
            message_content = line_bot_api.get_message_content(message_id)
            api_call_time = time.time() - download_start_time
            
            audio_content = BytesIO()
            bytes_read = 0
            
            read_start_time = time.time()
            for chunk in message_content.iter_content():
                audio_content.write(chunk)
                bytes_read += len(chunk)
            read_time = time.time() - read_start_time
            
            result = audio_content.getvalue()
            total_time = time.time() - download_start_time
            
            current_app.logger.info(f"[語音下載] API呼叫: {api_call_time:.3f}秒, 數據讀取: {read_time:.3f}秒, 總計: {total_time:.3f}秒, 大小: {len(result)} bytes")
            
            return result
        except Exception as e:
            current_app.logger.error(f"下載語音檔案失敗: {e}")
            return None
    
    @staticmethod
    def convert_audio_format(audio_bytes: bytes) -> Optional[bytes]:
        """
        優化的音檔格式轉換，使用快取和智能格式檢測
        
        Args:
            audio_bytes: 原始音檔bytes
            
        Returns:
            轉換後的wav格式bytes，失敗時返回None
        """
        # 產生快取鍵值
        cache_key = hashlib.md5(audio_bytes).hexdigest()
        
        # 檢查快取
        with _cache_lock:
            if cache_key in _voice_cache:
                cached_data, timestamp = _voice_cache[cache_key]
                if time.time() - timestamp < CACHE_EXPIRY_SECONDS:
                    current_app.logger.info("使用快取的音檔轉換結果")
                    return cached_data
        try:
            # 首先嘗試使用 pydub 進行轉換
            try:
                # LINE語音訊息通常是m4a格式
                audio = AudioSegment.from_file(BytesIO(audio_bytes), format="m4a")
                
                # 轉換為單聲道16kHz WAV (Google Speech-to-Text推薦格式)
                audio = audio.set_channels(1).set_frame_rate(16000)
                
                # 轉換為wav格式
                wav_buffer = BytesIO()
                audio.export(wav_buffer, format="wav")
                
                current_app.logger.info("使用 pydub 成功轉換音頻格式")
                result = wav_buffer.getvalue()
                
                # 儲存到快取
                with _cache_lock:
                    _voice_cache[cache_key] = (result, time.time())
                    # 清理過期快取
                    current_time = time.time()
                    expired_keys = [k for k, (_, ts) in _voice_cache.items() 
                                  if current_time - ts >= CACHE_EXPIRY_SECONDS]
                    for k in expired_keys:
                        del _voice_cache[k]
                
                return result
                
            except Exception as pydub_error:
                current_app.logger.warning(f"pydub 轉換失敗，嘗試備用方法: {pydub_error}")
                
                # 檢查是否是 FFmpeg 問題 - 更準確的檢測
                error_str = str(pydub_error).lower()
                if ("ffmpeg" in error_str or "ffprobe" in error_str or 
                    "winerror 2" in error_str or "系統找不到指定的檔案" in error_str or
                    "no such file or directory" in error_str):
                    
                    # 使用全域變數確保警告只顯示一次
                    global _ffmpeg_warning_shown
                    if not _ffmpeg_warning_shown:
                        current_app.logger.warning(
                            "FFmpeg 未安裝或不在 PATH 中。語音功能將使用備用方法處理音頻，"
                            "建議在生產環境安裝 FFmpeg 以獲得更好的音頻支援。"
                        )
                        _ffmpeg_warning_shown = True
                    else:
                        # 後續只記錄簡單的日誌
                        current_app.logger.info("使用備用音頻處理方法（FFmpeg 不可用）")
                
                # 備用方法：嘗試簡單的格式轉換
                current_app.logger.info("嘗試使用備用音頻處理方法")
                try:
                    # 嘗試將 m4a 轉換為基本的 wav 格式
                    audio = AudioSegment.from_file(BytesIO(audio_bytes))
                    # 設置為 Google Speech API 推薦的格式
                    audio = audio.set_channels(1).set_frame_rate(16000).set_sample_width(2)
                    
                    wav_buffer = BytesIO()
                    audio.export(wav_buffer, format="wav")
                    current_app.logger.info("備用方法轉換成功")
                    result = wav_buffer.getvalue()
                    
                    # 儲存到快取
                    with _cache_lock:
                        _voice_cache[cache_key] = (result, time.time())
                    
                    return result
                except:
                    # 如果所有轉換都失敗，返回原始音頻讓 API 嘗試處理
                    current_app.logger.info("使用原始音頻格式")
                    return audio_bytes
                
        except CouldntDecodeError:
            current_app.logger.error("無法解碼音頻檔案")
            return None
        except Exception as e:
            current_app.logger.error(f"音頻格式轉換失敗: {e}")
            return None
    
    def transcribe_audio_fast(self, audio_bytes: bytes, language_code: str = "zh-TW") -> Optional[str]:
        """
        超快速語音識別，極簡化配置
        """
        # 檢查轉錄快取
        cache_key = f"transcript_{hashlib.md5(audio_bytes).hexdigest()}"
        with _cache_lock:
            if cache_key in _voice_cache:
                cached_data, timestamp = _voice_cache[cache_key]
                if time.time() - timestamp < CACHE_EXPIRY_SECONDS:
                    current_app.logger.info("使用快取的語音轉錄結果")
                    return cached_data

        try:
            # 最簡化配置，不檢測格式，直接使用最通用設定
            config = speech.RecognitionConfig(
                encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
                sample_rate_hertz=16000,
                language_code=language_code,
                enable_automatic_punctuation=False,  # 關閉標點符號處理加快速度
                max_alternatives=1,
                use_enhanced=False  # 關閉增強模型加快速度
            )
            
            audio = speech.RecognitionAudio(content=audio_bytes)
            
            # 執行語音識別
            response = self.speech_client.recognize(config=config, audio=audio)
            
            if response.results:
                transcript = response.results[0].alternatives[0].transcript
                confidence = response.results[0].alternatives[0].confidence
                
                current_app.logger.info(f"超快速語音識別: '{transcript}' (信心度: {confidence:.2f})")
                
                if confidence > 0.2:  # 進一步降低信心度閾值加快速度
                    result = transcript.strip()
                    # 儲存轉錄結果到快取
                    with _cache_lock:
                        _voice_cache[cache_key] = (result, time.time())
                    return result
                    
        except Exception as e:
            current_app.logger.warning(f"超快速語音識別失敗: {e}")
        
        return None
    
    def _get_best_encoding_attempt(self, audio_bytes: bytes) -> dict:
        """
        根據音檔特徵選擇最佳的編碼格式（單一選擇）
        """
        is_wav_format = audio_bytes.startswith(b'RIFF') and b'WAVE' in audio_bytes[:20]
        
        if is_wav_format:
            return {
                'encoding': speech.RecognitionConfig.AudioEncoding.LINEAR16,
                'sample_rate_hertz': 16000,
                'description': 'WAV/LINEAR16'
            }
        else:
            # 非WAV格式，使用最通用的編碼
            return {
                'encoding': speech.RecognitionConfig.AudioEncoding.LINEAR16,
                'sample_rate_hertz': 16000,
                'description': 'LINEAR16_FAST'
            }

    def transcribe_audio(self, audio_bytes: bytes, language_code: str = "zh-TW") -> Optional[str]:
        """
        優化的語音轉文字，使用智能格式選擇和快取
        
        Args:
            audio_bytes: 音檔bytes (可能是wav或原始格式)
            language_code: 語言代碼，預設為繁體中文
            
        Returns:
            轉換後的文字，失敗時返回None
        """
        # 檢查轉錄快取
        cache_key = f"transcript_{hashlib.md5(audio_bytes).hexdigest()}"
        with _cache_lock:
            if cache_key in _voice_cache:
                cached_data, timestamp = _voice_cache[cache_key]
                if time.time() - timestamp < CACHE_EXPIRY_SECONDS:
                    current_app.logger.info("使用快取的語音轉錄結果")
                    return cached_data
        # 智能格式檢測和優化的編碼嘗試順序
        encoding_attempts = self._get_optimal_encoding_attempts(audio_bytes)
        
        # 嘗試每種編碼格式
        for attempt in encoding_attempts:
            try:
                current_app.logger.info(f"嘗試使用 {attempt['description']} 格式進行語音識別")
                
                # 建立配置
                config_params = {
                    'encoding': attempt['encoding'],
                    'language_code': language_code,
                    'enable_automatic_punctuation': True,
                    'max_alternatives': 1,
                    'profanity_filter': True,
                    'speech_contexts': [
                        speech.SpeechContext(phrases=[
                            # 健康指標
                            "血壓", "血糖", "體重", "體溫", "血氧", "心跳", "心率",
                            
                            # 時間與頻率
                            "早上", "中午", "下午", "晚上", "睡前", "凌晨", "半夜",
                            "每天", "每週", "每月", "一天一次", "一天兩次", "一天三次", "一天四次",
                            "飯前", "飯後", "空腹", "隨餐", "每六小時", "每八小時", "每十二小時",
                            "點", "點半", "分",
                            
                            # 單位
                            "毫克", "mg", "公克", "g", "單位", "IU", "毫升", "ml", "cc",
                            "公斤", "kg", "度", "°C", "百分比", "%", "bpm",
                            "一顆", "一粒", "一錠", "一包", "一瓶", "一劑", "一次",
                            
                            # 藥物與動作
                            "藥物", "藥品", "處方", "藥水", "藥膏", "膠囊", "錠劑",
                            "服用", "使用", "塗抹", "注射", "吸入", "吃藥",
                            "提醒", "設定", "新增", "查詢", "刪除", "修改",
                            
                            # 家庭成員與關係
                            "爸爸", "媽媽", "兒子", "女兒", "家人", "自己", "本人",
                            "爺爺", "奶奶", "外公", "外婆", "孫子", "孫女",
                            
                            # 主要功能指令
                            "藥單辨識", "掃描藥單", "拍藥單",
                            "藥品辨識", "掃描藥品", "拍藥品", "這是什麼藥",
                            "用藥提醒", "設定提醒", "吃藥提醒",
                            "家人綁定", "新增家人",
                            "健康紀錄", "記錄血壓", "記錄血糖",
                            "我的藥歷", "查詢藥歷"
                        ], boost=15) # 增加權重
                    ]
                }
                
                # 只有在有sample_rate_hertz時才添加
                if attempt['sample_rate_hertz']:
                    config_params['sample_rate_hertz'] = attempt['sample_rate_hertz']
                
                config = speech.RecognitionConfig(**config_params)
                audio = speech.RecognitionAudio(content=audio_bytes)
                
                # 執行語音識別
                response = self.speech_client.recognize(config=config, audio=audio)
                
                if response.results:
                    # 回傳第一個識別結果
                    transcript = response.results[0].alternatives[0].transcript
                    confidence = response.results[0].alternatives[0].confidence
                    
                    current_app.logger.info(f"語音識別成功 ({attempt['description']}): '{transcript}' (信心度: {confidence:.2f})")
                    
                    # 只有信心度夠高才回傳結果
                    if confidence > 0.6:
                        result = transcript.strip()
                        # 儲存轉錄結果到快取
                        with _cache_lock:
                            _voice_cache[cache_key] = (result, time.time())
                        return result
                    else:
                        current_app.logger.warning(f"語音識別信心度過低: {confidence:.2f}, 內容: '{transcript.strip()}', 編碼: {attempt['description']}")
                        continue  # 嘗試下一種編碼
                else:
                    current_app.logger.warning(f"{attempt['description']} 格式語音識別沒有結果")
                    continue  # 嘗試下一種編碼
                    
            except Exception as e:
                error_msg = str(e)
                if "sample rate" in error_msg.lower() and "0" in error_msg:
                    current_app.logger.warning(f"{attempt['description']} 格式語音識別失敗: 採樣率問題 - {e}")
                elif "invalid recognition" in error_msg.lower():
                    current_app.logger.warning(f"{attempt['description']} 格式語音識別失敗: 格式不支援 - {e}")
                else:
                    current_app.logger.warning(f"{attempt['description']} 格式語音識別失敗: {e}")
                continue  # 嘗試下一種編碼格式
        
        # 所有編碼都失敗了
        current_app.logger.error("所有音頻編碼格式都無法識別語音")
        return None
    
    @staticmethod
    def process_voice_input(user_id: str, audio_bytes: bytes, line_bot_api) -> Tuple[bool, str, dict]:
        """
        激進優化的語音輸入處理流程，目標 < 3秒
        
        Args:
            user_id: 用戶ID
            audio_bytes: 語音檔案bytes
            line_bot_api: LINE Bot API實例
            
        Returns:
            (成功標記, 轉換後的文字或錯誤訊息, 額外數據字典)
        """
        start_time = time.time()
        
        # 0. 快速指令檢測（適用於短音檔）
        quick_command = VoiceService.quick_command_detection(audio_bytes)
        if quick_command:
            current_app.logger.info(f"快速指令檢測成功: {quick_command}，耗時: {time.time() - start_time:.2f}秒")
            return True, quick_command, {'is_menu_command': True, 'menu_command': quick_command}
        
        voice_service = VoiceService()
        
        # 1. 並行處理：音檔轉換 + AI優化準備
        format_start = time.time()
        wav_bytes = voice_service.convert_audio_format(audio_bytes)
        if not wav_bytes:
            return False, "無法處理此語音格式，請重新錄製", {}
        format_time = time.time() - format_start
        
        # 2. 使用更快的語音識別設定
        transcript_start = time.time()
        transcript = voice_service.transcribe_audio_fast(wav_bytes)
        if not transcript:
            return False, "無法識別語音內容，請重新錄製", {}
        transcript_time = time.time() - transcript_start
        
        # 3. 最小化AI處理 - 只對複雜指令使用
        enhance_start = time.time()
        if VoiceService._should_enhance_with_ai(transcript):
            # 使用更快的AI優化
            enhanced_transcript = VoiceService._enhance_with_gemini_fast(transcript)
            final_transcript = enhanced_transcript or transcript
        else:
            final_transcript = VoiceService._local_text_optimization(transcript)
        enhance_time = time.time() - enhance_start
        
        # 4. 非同步記錄（不計入主要時間）
        try:
            VoiceService._log_voice_recognition_async(user_id, final_transcript, transcript)
        except:
            pass  # 忽略記錄錯誤
        
        # 5. 快速檢測選單指令
        menu_start = time.time()
        menu_command = VoiceService.detect_menu_command_fast(final_transcript)
        extra_data = {}
        
        if menu_command:
            extra_data = {
                'menu_command': menu_command,
                'postback_data': VoiceService.get_menu_postback_data(menu_command),
                'response_message': VoiceService.get_menu_response_message(menu_command),
                'is_menu_command': True
            }
            
            # 快取簡單指令結果
            if len(audio_bytes) < 50000:
                VoiceService.cache_quick_command(audio_bytes, menu_command)
            
            current_app.logger.info(f"用戶 {user_id} 語音呼叫: {menu_command}")
        else:
            extra_data = {'is_menu_command': False}
        
        menu_time = time.time() - menu_start
        total_time = time.time() - start_time
        
        current_app.logger.info(f"[語音優化] 格式:{format_time:.2f}s, 識別:{transcript_time:.2f}s, 增強:{enhance_time:.2f}s, 選單:{menu_time:.2f}s, 總計:{total_time:.2f}s")
        
        return True, final_transcript, extra_data
    
    @staticmethod
    def _should_enhance_with_ai(transcript: str) -> bool:
        """
        判斷是否需要使用AI優化，避免對簡單指令的不必要API呼叫
        """
        # 如果是常見的簡單指令，不需要AI優化
        simple_commands = [
            "選單", "主選單", "藥單辨識", "藥品辨識", "用藥提醒", 
            "健康紀錄", "家人綁定", "查詢本人", "查詢家人", "新增提醒"
        ]
        
        transcript_clean = transcript.replace(" ", "").replace("，", "").replace("。", "")
        
        for cmd in simple_commands:
            if cmd in transcript_clean:
                return False
        
        # 如果包含複雜的藥物或時間資訊，則使用AI優化
        complex_keywords = ["每天", "早上", "晚上", "顆", "粒", "錠", "藥", "點"]
        return any(keyword in transcript for keyword in complex_keywords)

    @staticmethod
    def _enhance_with_gemini_fast(transcript: str) -> str:
        """
        更快的Gemini AI優化，減少token和處理時間
        """
        try:
            from flask import current_app
            import google.generativeai as genai
            
            api_key = current_app.config.get('GEMINI_API_KEY')
            if not api_key:
                return VoiceService._local_text_optimization(transcript)
            
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel('gemini-2.5-flash')
            
            # 最簡化的提示詞
            prompt = f"修正錯字: {transcript}"
            
            response = model.generate_content(
                prompt,
                generation_config=genai.types.GenerationConfig(
                    temperature=0.01,        # 最低溫度提高一致性
                    top_p=0.9,
                    top_k=20,               # 減少選擇範圍
                    candidate_count=1,
                    max_output_tokens=50    # 最小化token數量
                ),
                safety_settings=[
                    {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
                    {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
                    {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
                    {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"}
                ]
            )
            
            enhanced_text = response.text.strip() if response.text else ""
            
            if enhanced_text and 0.5 * len(transcript) <= len(enhanced_text) <= 1.5 * len(transcript):
                current_app.logger.info(f"Gemini快速優化: '{transcript}' → '{enhanced_text}'")
                return enhanced_text
            else:
                return VoiceService._local_text_optimization(transcript)
                
        except Exception as e:
            current_app.logger.warning(f"Gemini快速優化失敗: {e}")
            return VoiceService._local_text_optimization(transcript)

    @staticmethod
    def _enhance_with_gemini(transcript: str) -> str:
        """
        使用Gemini AI優化語音識別結果，特別針對用藥相關內容
        """
        try:
            from flask import current_app
            import google.generativeai as genai
            
            # 檢查是否有Gemini API金鑰
            api_key = current_app.config.get('GEMINI_API_KEY')
            if not api_key:
                current_app.logger.warning("未設定GEMINI_API_KEY，跳過語音優化")
                return transcript
            
            
            # 初始化Gemini
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel('gemini-2.5-flash')  # 使用更穩定的模型版本
            
            # 建立語音優化提示
            prompt = f"""請修正以下語音識別結果中的錯字和語法問題，特別注意用藥相關詞彙：

語音識別結果：{transcript}

修正後結果："""
            
            # 呼叫Gemini API，加入更寬鬆的設定和安全配置
            response = model.generate_content(
                prompt,
                generation_config=genai.types.GenerationConfig(
                    max_output_tokens=100,  # 增加輸出長度以支援中文
                    temperature=0.1,        # 稍微增加創造性但保持準確
                    top_p=0.9,
                    top_k=40,
                    candidate_count=1       # 只生成一個候選回應
                ),
                safety_settings=[
                    {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
                    {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
                    {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
                    {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"}
                ]
            )
            
            # 檢查 API 回應
            current_app.logger.debug(f"Gemini API 原始回應: {response}")
            
            # 檢查是否因為 token 限制被截斷
            if hasattr(response, 'candidates') and response.candidates:
                candidate = response.candidates[0]
                finish_reason = getattr(candidate, 'finish_reason', None)
                current_app.logger.debug(f"Gemini finish_reason: {finish_reason}")
                
                if finish_reason == 'MAX_TOKENS':
                    current_app.logger.warning(f"Gemini API 回應被截斷 (MAX_TOKENS)，使用本地優化")
                    return VoiceService._local_text_optimization(transcript)
                elif finish_reason in ['SAFETY', 'RECITATION', 'OTHER']:
                    current_app.logger.warning(f"Gemini API 回應被阻止 ({finish_reason})，使用本地優化")
                    return VoiceService._local_text_optimization(transcript)
            
            enhanced_text = response.text.strip() if response.text else ""
            current_app.logger.debug(f"回應文字內容: '{enhanced_text}'")
            
            # 驗證優化結果
            if enhanced_text and len(enhanced_text.strip()) > 0:
                # 更寬鬆的長度檢查：允許結果長度在原文的0.5倍到3倍之間
                min_length = max(1, len(transcript) // 2)
                max_length = len(transcript) * 3
                
                if min_length <= len(enhanced_text) <= max_length:
                    current_app.logger.info(f"Gemini語音優化成功: '{transcript}' → '{enhanced_text}'")
                    return enhanced_text
                else:
                    current_app.logger.warning(f"Gemini語音優化結果長度異常，使用本地優化")
                    return VoiceService._local_text_optimization(transcript)
            else:
                current_app.logger.warning(f"Gemini語音優化結果為空，使用本地優化")
                return VoiceService._local_text_optimization(transcript)
                
        except Exception as e:
            current_app.logger.error(f"Gemini語音優化失敗: {e}")
            return VoiceService._local_text_optimization(transcript)

    @staticmethod
    def _local_text_optimization(transcript: str) -> str:
        """
        本地文字優化，當 Gemini API 失敗時使用
        """
        try:
            import re
            
            # 基本的文字優化
            optimized = transcript
            
            # 1. 中文數字轉阿拉伯數字
            chinese_numbers = {
                '一': '1', '二': '2', '三': '3', '四': '4', '五': '5',
                '六': '6', '七': '7', '八': '8', '九': '9', '十': '10',
                '兩': '2', '零': '0'
            }
            
            for chinese, arabic in chinese_numbers.items():
                optimized = optimized.replace(f'{chinese}點', f'{arabic}點')
                optimized = optimized.replace(f'{chinese}顆', f'{arabic}顆')
                optimized = optimized.replace(f'{chinese}粒', f'{arabic}粒')
                optimized = optimized.replace(f'{chinese}錠', f'{arabic}錠')
                optimized = optimized.replace(f'{chinese}次', f'{arabic}次')
            
            # 2. 常見錯字修正
            corrections = {
                '亮血壓': '量血壓',
                '記體重': '記體重',
                '血壓要': '血壓藥',
                '血糖要': '血糖藥',
                '胃要': '胃藥'
            }
            
            for wrong, correct in corrections.items():
                optimized = optimized.replace(wrong, correct)
            
            # 3. 單位標準化
            optimized = optimized.replace('西西', 'ml')
            optimized = optimized.replace('CC', 'ml')
            
            current_app.logger.info(f"本地語音優化: '{transcript}' → '{optimized}'")
            return optimized
            
        except Exception as e:
            current_app.logger.error(f"本地語音優化失敗: {e}")
            return transcript

    def _get_optimal_encoding_attempts(self, audio_bytes: bytes) -> list:
        """
        根據音檔特徵選擇最佳的編碼嘗試順序
        """
        # 檢測音頻格式
        is_wav_format = audio_bytes.startswith(b'RIFF') and b'WAVE' in audio_bytes[:20]
        is_m4a_format = audio_bytes[4:8] == b'ftyp'
        
        if is_wav_format:
            # WAV格式，直接使用LINEAR16
            return [{
                'encoding': speech.RecognitionConfig.AudioEncoding.LINEAR16,
                'sample_rate_hertz': 16000,
                'description': 'WAV/LINEAR16'
            }]
        elif is_m4a_format:
            # M4A格式（LINE常用），優先嘗試這些編碼
            return [
                {
                    'encoding': speech.RecognitionConfig.AudioEncoding.LINEAR16,
                    'sample_rate_hertz': 16000,
                    'description': 'M4A_TO_LINEAR16'
                },
                {
                    'encoding': speech.RecognitionConfig.AudioEncoding.ENCODING_UNSPECIFIED,
                    'sample_rate_hertz': None,
                    'description': 'M4A_AUTO_DETECT'
                }
            ]
        else:
            # 其他格式，使用通用嘗試列表
            return [
                {
                    'encoding': speech.RecognitionConfig.AudioEncoding.ENCODING_UNSPECIFIED,
                    'sample_rate_hertz': None,
                    'description': 'AUTO_DETECT'
                },
                {
                    'encoding': speech.RecognitionConfig.AudioEncoding.LINEAR16,
                    'sample_rate_hertz': 16000,
                    'description': 'LINEAR16_16K'
                },
                {
                    'encoding': speech.RecognitionConfig.AudioEncoding.FLAC,
                    'sample_rate_hertz': 16000,
                    'description': 'FLAC'
                }
            ]

    @staticmethod
    def _log_voice_recognition_async(user_id: str, transcript: str, original_transcript: str = None):
        """
        非同步記錄語音識別結果，使用簡化的方法避免上下文問題
        """
        def log_in_thread():
            try:
                # 使用簡化的資料庫連接，避免 Flask 上下文問題
                import pymysql
                from flask import current_app
                
                # 嘗試獲取資料庫配置
                try:
                    # 如果有應用程式上下文，使用配置
                    db_config = {
                        'host': current_app.config.get('DB_HOST'),
                        'user': current_app.config.get('DB_USER'),
                        'password': current_app.config.get('DB_PASSWORD'),
                        'database': current_app.config.get('DB_NAME'),
                        'port': current_app.config.get('DB_PORT', 3306),
                        'charset': 'utf8mb4'
                    }
                except RuntimeError:
                    # 如果沒有應用程式上下文，使用環境變數
                    import os
                    db_config = {
                        'host': os.environ.get('DB_HOST'),
                        'user': os.environ.get('DB_USER'),  
                        'password': os.environ.get('DB_PASS'),
                        'database': os.environ.get('DB_NAME'),
                        'port': int(os.environ.get('DB_PORT', 3306)),
                        'charset': 'utf8mb4'
                    }
                
                # 檢查必要的配置是否存在
                if not all([db_config['host'], db_config['user'], db_config['password'], db_config['database']]):
                    print("語音記錄: 資料庫配置不完整，跳過記錄")
                    return
                
                # 建立資料庫連接
                connection = pymysql.connect(**db_config)
                cursor = connection.cursor()
                
                # 確保表存在
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS voice_recognition_logs (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        user_id VARCHAR(255) NOT NULL COMMENT 'LINE用戶ID',
                        transcript TEXT NOT NULL COMMENT '最終語音識別結果文字',
                        original_transcript TEXT DEFAULT NULL COMMENT '原始語音識別結果',
                        confidence_score DECIMAL(4,3) DEFAULT NULL COMMENT '識別信心度',
                        enhanced_by_ai BOOLEAN DEFAULT FALSE COMMENT '是否經過AI優化',
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '創建時間',
                        INDEX idx_user_id (user_id),
                        INDEX idx_created_at (created_at)
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
                """)
                
                # 插入記錄
                enhanced_by_ai = original_transcript is not None and original_transcript != transcript
                cursor.execute("""
                    INSERT INTO voice_recognition_logs 
                    (user_id, transcript, original_transcript, enhanced_by_ai, created_at)
                    VALUES (%s, %s, %s, %s, NOW())
                """, (user_id, transcript, original_transcript, enhanced_by_ai))
                
                connection.commit()
                cursor.close()
                connection.close()
                
                print(f"語音識別記錄已保存: {user_id} -> {transcript[:50]}...")
                
            except Exception as e:
                print(f"記錄語音識別失敗: {e}")
                import traceback
                print(f"錯誤詳情: {traceback.format_exc()}")
        
        # 在背景執行緒中執行
        threading.Thread(target=log_in_thread, daemon=True).start()

    @staticmethod
    def _log_voice_recognition(user_id: str, transcript: str, original_transcript: str = None):
        """記錄語音識別結果到資料庫，包含原始和優化後的結果"""
        try:
            from ..utils.db import get_db_connection
            db = get_db_connection()
            if db:
                cursor = db.cursor()
                
                # 確保表存在
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS voice_recognition_logs (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        user_id VARCHAR(255) NOT NULL COMMENT 'LINE用戶ID',
                        transcript TEXT NOT NULL COMMENT '最終語音識別結果文字',
                        original_transcript TEXT DEFAULT NULL COMMENT '原始語音識別結果',
                        confidence_score DECIMAL(4,3) DEFAULT NULL COMMENT '識別信心度',
                        enhanced_by_ai BOOLEAN DEFAULT FALSE COMMENT '是否經過AI優化',
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '創建時間',
                        INDEX idx_user_id (user_id),
                        INDEX idx_created_at (created_at)
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
                """)
                
                # 插入記錄
                enhanced_by_ai = original_transcript is not None and original_transcript != transcript
                cursor.execute("""
                    INSERT INTO voice_recognition_logs 
                    (user_id, transcript, original_transcript, enhanced_by_ai, created_at)
                    VALUES (%s, %s, %s, %s, NOW())
                """, (user_id, transcript, original_transcript, enhanced_by_ai))
                
                db.commit()
                cursor.close()
                current_app.logger.info(f"語音識別記錄已保存: {user_id} -> {transcript[:50]}...")
            
        except Exception as e:
            current_app.logger.error(f"記錄語音識別失敗: {e}")
            # 不影響主要功能，繼續執行
    
    @staticmethod
    def quick_command_detection(audio_bytes: bytes) -> str:
        """
        快速指令檢測，適用於短音檔
        
        Args:
            audio_bytes: 音檔bytes
            
        Returns:
            如果檢測到快速指令則返回指令，否則返回None
        """
        # 檢查音檔大小，小於50KB的音檔可能是短指令
        if len(audio_bytes) > 50000:
            return None
            
        # 檢查快取中是否有這個音檔的結果
        cache_key = f"quick_cmd_{hashlib.md5(audio_bytes).hexdigest()}"
        with _cache_lock:
            if cache_key in _voice_cache:
                cached_data, timestamp = _voice_cache[cache_key]
                if time.time() - timestamp < CACHE_EXPIRY_SECONDS:
                    current_app.logger.info("使用快取的快速指令結果")
                    return cached_data
        
        # 對於非常短的音檔（小於15KB），跳過處理加快速度
        if len(audio_bytes) < 15000:
            return None
            
        return None  # 暫時返回None，讓主要流程處理
    
    @staticmethod
    def cache_quick_command(audio_bytes: bytes, command: str):
        """
        快取快速指令結果
        
        Args:
            audio_bytes: 音檔bytes
            command: 檢測到的指令
        """
        cache_key = f"quick_cmd_{hashlib.md5(audio_bytes).hexdigest()}"
        with _cache_lock:
            _voice_cache[cache_key] = (command, time.time())

    @staticmethod  
    def detect_menu_command_fast(transcript: str) -> str:
        """
        快速檢測語音中的選單呼叫指令，使用簡化的匹配
        """
        # 只保留最常用的指令，減少檢查時間
        clean_text = transcript.replace(" ", "").replace("，", "").replace("。", "")
        
        # 超快速預檢測 - 檢查關鍵字
        if "查詢" in clean_text:
            if "本人" in clean_text or "我的" in clean_text:
                return "query_self_reminders"
            elif "家人" in clean_text:
                return "query_family_reminders"
        
        # 簡化的指令匹配（按使用頻率排序）
        fast_commands = {
            "query_self_reminders": ["查詢本人", "我的提醒", "本人提醒"],
            "query_family_reminders": ["查詢家人", "家人提醒", "查看家人"],
            "reminder": ["新增提醒", "設定提醒", "用藥提醒", "提醒我吃", "幫我新增"],
            "prescription_scan": ["藥單辨識", "掃描藥單", "辨識藥單"],
            "pill_scan": ["藥品辨識", "這是什麼藥"],
            "health": ["健康紀錄", "記錄體重", "記錄血壓"]
        }
        
        for menu_type, commands in fast_commands.items():
            for command in commands:
                if command in clean_text:
                    return menu_type
        
        return None

    @staticmethod  
    def detect_menu_command(transcript: str) -> str:
        """
        檢測語音中的選單呼叫指令
        
        Args:
            transcript: 語音轉換的文字
            
        Returns:
            對應的選單功能代碼，如果沒有匹配則返回None
        """
        # 清理文字，移除標點符號和空格
        clean_text = transcript.replace(" ", "").replace("，", "").replace("。", "").replace("！", "").replace("？", "")
        
        # 定義語音指令對應的選單功能
        menu_commands = {
            # 藥單辨識相關指令
            "prescription_scan": [
                "藥單辨識", "掃描藥單", "辨識藥單", "藥單掃描", "處方辨識", "處方掃描",
                "我要掃描藥單", "我要辨識藥單", "幫我掃描藥單", "幫我辨識藥單",
                "拍照辨識藥單", "拍藥單", "掃藥單"
            ],
            # 藥品辨識相關指令  
            "pill_scan": [
                "藥品辨識", "掃描藥品", "辨識藥品", "藥品掃描", "藥物辨識", "藥物掃描",
                "我要掃描藥品", "我要辨識藥品", "幫我掃描藥品", "幫我辨識藥品",
                "拍照辨識藥品", "拍藥品", "掃藥品", "這是什麼藥"
            ],
            # 用藥提醒相關指令
            "reminder": [
                "用藥提醒", "藥物提醒", "設定提醒", "提醒設定", "吃藥提醒",
                "我要設定提醒", "幫我設定提醒", "新增提醒", "建立提醒",
                "提醒我吃藥", "設定吃藥時間"
            ],
            # 家人綁定相關指令
            "family": [
                "家人綁定", "綁定家人", "新增家人", "加入家人", "家庭成員",
                "我要綁定家人", "我要新增家人", "幫我綁定家人", "幫我新增家人",
                "家人管理", "成員管理"
            ],
            # 藥歷查詢相關指令
            "history": [
                "我的藥歷", "我的藥單", "藥歷查詢", "用藥紀錄", "藥物紀錄", "服藥紀錄",
                "查看藥歷", "查詢藥歷", "我要看藥歷", "顯示藥歷",
                "用藥歷史", "服藥歷史", "查看藥單", "我要看藥單"
            ],
            # 健康紀錄相關指令
            "health": [
                "健康紀錄", "健康記錄", "生理數據", "健康數據", "身體數據",
                "我要記錄健康", "新增健康紀錄", "記錄健康數據", "輸入健康數據",
                "血壓記錄", "血糖記錄", "體重記錄", "體溫記錄"
            ],
            # 查詢本人提醒相關指令
            "query_self_reminders": [
                "查詢本人", "查看本人", "本人提醒", "我的提醒", "查詢我的提醒",
                "查看我的提醒", "本人用藥提醒", "我的用藥提醒", "查詢本人提醒",
                "查看本人提醒", "本人的提醒", "我的所有提醒"
            ],
            # 查詢家人提醒相關指令
            "query_family_reminders": [
                "查詢家人", "查看家人", "家人提醒", "查詢家人提醒", "查看家人提醒",
                "家人用藥提醒", "查詢所有家人", "查看所有家人", "全部家人提醒",
                "所有成員提醒", "查詢成員提醒", "查看成員提醒", "家庭成員提醒"
            ],
            # 新增本人提醒相關指令
            "add_self_reminder": [
                "新增本人", "新增本人提醒", "新增我的提醒", "為本人新增提醒",
                "本人新增提醒", "我要新增提醒", "新增個人提醒", "設定本人提醒",
                "本人設定提醒", "我要設定提醒", "新增自己的提醒"
            ],
            # 語音新增提醒對象相關指令
            "add_reminder_member": [
                "新增提醒對象", "新增家人", "建立提醒對象", "新增成員",
                "我要新增提醒對象", "我要新增家人", "我要建立提醒對象",
                "幫我新增提醒對象", "幫我新增家人", "新增家庭成員"
            ]
        }
        
        # 檢查每個指令類別
        for menu_type, commands in menu_commands.items():
            for command in commands:
                if command in clean_text:
                    current_app.logger.info(f"檢測到選單指令: '{transcript}' -> {menu_type}")
                    return menu_type
        
        return None
    
    @staticmethod
    def get_menu_postback_data(menu_type: str) -> str:
        """
        根據選單類型返回對應的postback數據
        
        Args:
            menu_type: 選單功能類型
            
        Returns:
            對應的postback數據字符串
        """
        menu_postback_map = {
            "prescription_scan": "action=prescription_scan",
            "pill_scan": "action=pill_scan", 
            "reminder": "action=reminder_menu",
            "family": "action=family_menu",
            "history": "action=prescription_history",
            "health": "action=health_record",
            "query_self_reminders": "action=view_existing_reminders&member=本人",
            "query_family_reminders": "管理提醒對象",
            "add_self_reminder": "LIFF_MANUAL_REMINDER",
            "add_reminder_member": "action=add_reminder_member"
        }
        
        return menu_postback_map.get(menu_type, "")
    
    @staticmethod
    def get_menu_response_message(menu_type: str) -> str:
        """
        根據選單類型返回對應的回應訊息
        
        Args:
            menu_type: 選單功能類型
            
        Returns:
            對應的回應訊息
        """
        menu_messages = {
            "prescription_scan": "📋 正在為您開啟藥單辨識功能，請拍照上傳您的處方籤",
            "pill_scan": "💊 正在為您開啟藥品辨識功能，請拍照上傳您的藥品",
            "reminder": "⏰ 正在為您開啟用藥提醒設定功能",
            "family": "👨‍👩‍👧‍👦 正在為您開啟家人綁定功能",
            "history": "📊 正在為您開啟藥歷查詢功能",
            "health": "🏥 正在為您開啟健康紀錄功能",
            "query_self_reminders": "🔍 正在為您查詢本人的所有用藥提醒",
            "query_family_reminders": "👨‍👩‍👧‍👦 正在為您查詢所有家人的用藥提醒",
            "add_self_reminder": "➕ 正在為您開啟新增本人提醒功能",
            "add_reminder_member": "👥 正在為您開啟新增提醒對象功能"
        }
        
        return menu_messages.get(menu_type, "")

    @staticmethod
    def parse_add_member_command(transcript: str) -> dict:
        """
        解析語音新增提醒對象指令，提取成員名稱
        
        Args:
            transcript: 語音轉換的文字
            
        Returns:
            包含解析結果的字典，格式：
            {
                'is_add_member_command': bool,
                'member_name': str or None,
                'command_type': str or None  # 'add_reminder_target', 'add_family', 'create_reminder_target'
            }
        """
        import re
        
        # 清理文字
        clean_text = transcript.replace(" ", "").replace("，", "").replace("。", "").replace("！", "").replace("？", "")
        
        # 定義匹配模式
        patterns = [
            # 新增提醒對象 + 名稱
            (r"新增提醒對象(.+)", "add_reminder_target"),
            (r"建立提醒對象(.+)", "create_reminder_target"),
            # 新增家人 + 名稱
            (r"新增家人(.+)", "add_family"),
            (r"我要新增家人(.+)", "add_family"),
            (r"幫我新增家人(.+)", "add_family"),
            # 其他變體
            (r"新增成員(.+)", "add_member"),
            (r"我要新增提醒對象(.+)", "add_reminder_target"),
            (r"我要建立提醒對象(.+)", "create_reminder_target"),
            (r"幫我新增提醒對象(.+)", "add_reminder_target"),
            (r"新增家庭成員(.+)", "add_family"),
        ]
        
        for pattern, command_type in patterns:
            match = re.search(pattern, clean_text)
            if match:
                member_name = match.group(1).strip()
                
                # 過濾掉無效的名稱
                if member_name and len(member_name) <= 10 and member_name not in ['我', '你', '他', '她', '它']:
                    current_app.logger.info(f"語音指令解析成功: '{transcript}' -> 成員名稱: '{member_name}', 指令類型: {command_type}")
                    return {
                        'is_add_member_command': True,
                        'member_name': member_name,
                        'command_type': command_type
                    }
        
        return {
            'is_add_member_command': False,
            'member_name': None,
            'command_type': None
        }

    @staticmethod
    def process_add_member_command(user_id: str, member_name: str, command_type: str) -> tuple:
        """
        處理語音新增提醒對象指令
        
        Args:
            user_id: 用戶ID
            member_name: 成員名稱
            command_type: 指令類型
            
        Returns:
            (success: bool, message: str, extra_data: dict)
        """
        try:
            from ..services.user_service import UserService
            
            # 檢查成員名稱是否已存在
            existing_members = UserService.get_user_members(user_id)
            existing_names = [member['member'] for member in existing_members]
            
            if member_name in existing_names:
                return False, f"❌ 提醒對象「{member_name}」已存在，請使用其他名稱。", {}
            
            # 檢查名稱長度和有效性
            if len(member_name) > 10:
                return False, "❌ 成員名稱不能超過10個字元，請重新輸入。", {}
            
            if not member_name.strip():
                return False, "❌ 成員名稱不能為空，請重新輸入。", {}
            
            # 新增成員
            try:
                success = UserService.add_new_member(user_id, member_name)
                
                if success:
                    current_app.logger.info(f"語音新增成員成功: 用戶 {user_id} 新增成員 '{member_name}'")
                    
                    # 根據指令類型返回不同的回應訊息
                    if command_type in ['add_family', 'add_member']:
                        message = f"✅ 成功新增家人「{member_name}」！\n\n您現在可以為「{member_name}」設定用藥提醒了。"
                    else:
                        message = f"✅ 成功新增提醒對象「{member_name}」！\n\n您現在可以為「{member_name}」設定用藥提醒了。"
                    
                    return True, message, {
                        'member_added': True,
                        'member_name': member_name,
                        'command_type': command_type
                    }
                else:
                    return False, f"❌ 新增提醒對象「{member_name}」失敗，請稍後再試。", {}
                    
            except ValueError as ve:
                # UserService.add_new_member 拋出的 ValueError（如成員已存在）
                current_app.logger.warning(f"語音新增成員被拒絕: {ve}")
                return False, f"❌ {str(ve)}", {}
            except Exception as add_error:
                current_app.logger.error(f"新增成員時發生錯誤: {add_error}")
                return False, f"❌ 新增提醒對象「{member_name}」失敗，請稍後再試。", {}
                
        except Exception as e:
            current_app.logger.error(f"處理語音新增成員指令失敗: {e}")
            return False, "❌ 系統錯誤，請稍後再試。", {}

    @staticmethod
    def get_voice_input_suggestions(context: str = None) -> list:
        """
        根據上下文提供語音輸入建議
        
        Args:
            context: 當前上下文 (如: health_record, reminder_setting, etc.)
            
        Returns:
            語音輸入建議列表
        """
        base_suggestions = [
            "請清楚說出您想要輸入的內容",
            "支援中文語音輸入",
            "錄製時請保持安靜的環境"
        ]
        
        context_suggestions = {
            "health_record": [
                "例如：體重65.5公斤",
                "例如：血壓130/80",
                "例如：血糖120",
                "例如：體溫36.5度"
            ],
            "reminder_setting": [
                "例如：每天早上8點提醒",
                "例如：一天三次飯前服用",
                "例如：血壓藥早晚各一次"
            ],
            "family_binding": [
                "例如：我的媽媽",
                "例如：大兒子",
                "例如：外婆"
            ],
            "menu_commands": [
                "例如：藥單辨識",
                "例如：我要設定提醒",
                "例如：查看我的藥歷",
                "例如：新增家人",
                "例如：記錄健康數據"
            ]
        }
        
        if context and context in context_suggestions:
            base_suggestions.extend(context_suggestions[context])
        
        return base_suggestions