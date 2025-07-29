# app/routes/handlers/pill_handler.py

import io
import base64
import requests
import concurrent.futures
from PIL import Image
from flask import current_app
from linebot.models import TextSendMessage, FlexSendMessage
from linebot.v3.messaging import Configuration, ApiClient, MessagingApi, MessagingApiBlob, ReplyMessageRequest, TextMessage, FlexMessage, FlexContainer
from app import line_bot_api
from ...services.user_service import UserService
from ...utils.flex import pill as flex_pill

# 條件導入 kevin_model_handler，避免導入失敗影響整個模組
try:
    import kevin_model_handler
    KEVIN_MODEL_AVAILABLE = True
    print(f"✅ kevin_model_handler 導入成功")
except ImportError as e:
    print(f"❌ Warning: kevin_model_handler import failed (ImportError): {e}")
    kevin_model_handler = None
    KEVIN_MODEL_AVAILABLE = False
except Exception as e:
    print(f"❌ Warning: kevin_model_handler import failed (Other Error): {e}")
    import traceback
    traceback.print_exc()
    kevin_model_handler = None
    KEVIN_MODEL_AVAILABLE = False

# 全局变量定义
user_states = {}

# 可用模型配置
AVAILABLE_MODELS = {
    "1": {
        "name": "yolov12",
        "url": "https://yolo120724-712800774423.us-central1.run.app"
    },
    "2": {
        "name": "yolov11", 
        "url": "https://yolo110724-712800774423.us-central1.run.app"
    }
}

class PillDetectionClient:
    """药丸检测 API 客户端 - 简化版"""
    
    def __init__(self, base_urls, use_all_models=False):
        self.base_urls = [url.rstrip('/') for url in base_urls]
        self.use_all_models = use_all_models
        self.current_url_index = 0
        self.timeout = 60
    
    def _pil_image_to_base64(self, pil_image):
        """将 PIL Image 转换为 base64 编码"""
        try:
            buffer = io.BytesIO()
            if pil_image.mode in ('RGBA', 'LA', 'P'):
                pil_image = pil_image.convert('RGB')
            pil_image.save(buffer, format='JPEG', quality=85)
            image_data = buffer.getvalue()
            return base64.b64encode(image_data).decode('utf-8')
        except Exception as e:
            print(f"PIL 图片转换失败: {str(e)}")
            raise
    
    def detect_pills(self, pil_image):
        """检测药丸"""
        try:
            image_base64 = self._pil_image_to_base64(pil_image)
            payload = {"image": image_base64}
            
            if self.use_all_models and len(self.base_urls) > 1:
                return self._detect_with_all_models(payload)
            else:
                return self._detect_with_single_model(payload)
                
        except Exception as e:
            print(f"药丸检测失败: {str(e)}")
            raise
    
    def _detect_with_single_model(self, payload):
        """单模型检测"""
        url = self.base_urls[0]
        try:
            response = requests.post(f"{url}/api/detect", json=payload, timeout=self.timeout)
            response.raise_for_status()
            result = response.json()
            result['detection_mode'] = 'single'
            result['model_name'] = '药丸检测模型'
            
            # 确保单模型也有 predict_image_url 字段
            if 'annotated_image_url' in result and not result.get('predict_image_url'):
                result['predict_image_url'] = result['annotated_image_url']
            
            print(f"单模型检测结果: detections={len(result.get('detections', []))}, predict_image_url={bool(result.get('predict_image_url'))}")
            return result
        except Exception as e:
            print(f"单模型检测失败: {str(e)}")
            raise
    
    def _detect_with_all_models(self, payload):
        """多模型检测"""
        all_results = []
        successful_models = []
        
        for i, url in enumerate(self.base_urls):
            try:
                response = requests.post(f"{url}/api/detect", json=payload, timeout=self.timeout)
                response.raise_for_status()
                result = response.json()
                result['model_source'] = url
                result['model_index'] = i + 1
                all_results.append(result)
                successful_models.append(f"模型{i+1}")
            except Exception as e:
                print(f"模型 {i+1} 检测失败: {str(e)}")
                continue
        
        if not all_results:
            raise Exception("所有模型都无法进行检测")
        
        # 合并结果
        merged_result = self._merge_detection_results(all_results)
        merged_result['successful_models'] = successful_models
        merged_result['total_models_used'] = len(successful_models)
        merged_result['detection_mode'] = 'multi'
        
        return merged_result
    
    def _merge_detection_results(self, results):
        """合并多个检测结果"""
        if not results:
            return {"detections": [], "message": "没有检测结果"}
        
        if len(results) == 1:
            return results[0]
        
        all_detections = []
        all_annotated_urls = []
        
        for i, result in enumerate(results):
            detections = result.get('detections', [])
            
            for detection in detections:
                detection['model_source'] = result.get('model_source', f'模型{i+1}')
                detection['model_index'] = result.get('model_index', i+1)
                all_detections.append(detection)
            
            if 'annotated_image_url' in result:
                all_annotated_urls.append({
                    'model_index': result.get('model_index', i+1),
                    'model_source': result.get('model_source', f'模型{i+1}'),
                    'url': result['annotated_image_url']
                })
        
        merged_result = {
            "detections": all_detections,
            "total_detections": len(all_detections),
            "annotated_images": all_annotated_urls,
            "models_used": len(results),
            "message": f"使用 {len(results)} 个模型进行检测，总共找到 {len(all_detections)} 个药丸"
        }
        
        if results:
            first_result = results[0]
            for key, value in first_result.items():
                if key not in merged_result and key not in ['detections', 'annotated_image_url', 'model_source', 'model_index']:
                    merged_result[key] = value
        
        return merged_result

def _standardize_and_get_db_info(raw_results):
    """标准化检测结果并从数据库获取药品信息"""
    if not raw_results:
        return [], 0
    
    # --- DEBUG: 印出收到的原始結果 ---
    print(f"--- DEBUG: _standardize_and_get_db_info received raw_results ---")
    import json
    print(json.dumps(raw_results, indent=2, ensure_ascii=False))
    print(f"----------------------------------------------------------------")
    # --- END DEBUG ---

    
    standardized_results = []
    total_time = 0
    
    for result in raw_results:
        if not result.get('success'):
            continue
            
        detections = result.get('detections', [])
        if not detections:
            continue
            
        # 从数据库获取药品详细信息 (只匹配前十碼)
        drug_id_prefixes = []
        for detection in detections:
            drug_id = None
            if 'drug_id' in detection:
                drug_id = str(detection['drug_id'])
            elif 'class_name' in detection:
                # 從 class_name (例如 A006271100_front) 中提取 ID
                drug_id = str(detection['class_name']).split('_')[0]
            
            if drug_id:
                prefix = drug_id[:10]  # 只取前十碼
                if prefix not in drug_id_prefixes:
                    drug_id_prefixes.append(prefix)
        
        pill_details = []  # 初始化為空列表
        if drug_id_prefixes:
            from ...utils.db import DB
            # 使用前綴匹配查詢藥品詳細資訊
            pill_details = []
            print(f"    - 調試: 查詢前綴 {drug_id_prefixes}")
            for prefix in drug_id_prefixes:
                # 查詢所有以此前綴開頭的藥品
                matching_pills = DB.get_pills_details_by_prefix(prefix)
                print(f"    - 調試: 前綴 '{prefix}' 找到 {len(matching_pills)} 個藥品")
                pill_details.extend(matching_pills)
            print(f"    - 調試: 總共找到 {len(pill_details)} 個藥品詳細資訊")
            
            # 将数据库信息合并到检测结果中 (前十碼匹配)
            for detection in detections:
                detected_drug_id = str(detection.get('drug_id', ''))
                detected_prefix = detected_drug_id[:10]
                for pill_detail in pill_details:
                    db_drug_id = str(pill_detail.get('drug_id', ''))
                    db_prefix = db_drug_id[:10]
                    if detected_prefix == db_prefix:
                        detection.update(pill_detail)
                        break
        
        standardized_result = {
            'detections': detections,
            'model_name': result.get('model_name', '未知模型'),
            'elapsed_time': result.get('elapsed_time', 0),
            'annotated_image_url': result.get('annotated_image_url'),
            'predict_image_url': result.get('predict_image_url') or result.get('annotated_image_url'),
            'pills_info': pill_details  # 添加藥品詳細資訊
        }
        
        standardized_results.append(standardized_result)
        total_time += result.get('elapsed_time', 0)
    
    return standardized_results, total_time

def handle(event):
    """處理藥丸辨識相關的訊息和事件"""
    user_id = event.source.user_id
    print(f"🔍 [Pill Handler] 處理事件，用戶: {user_id}")
    
    # 處理文字訊息
    if hasattr(event, 'message') and hasattr(event.message, 'text') and event.message.text is not None:
        # 確保 text 不為 None 才執行 strip()
        message_text = event.message.text
        if message_text is None:
            print(f"⚠️ [Pill Handler] 收到 None 文字訊息 - 用戶: {user_id}")
            return
        
        text = message_text.strip()
        print(f"🔍 [Pill Handler] 收到文字訊息: '{text}'")
        
        if text in ["藥丸辨識", "藥品辨識"]:
            print(f"✅ [Pill Handler] 匹配到藥品辨識指令: '{text}'")
            # 顯示藥丸辨識主選單
            UserService.clear_user_complex_state(user_id)
            UserService.delete_user_simple_state(user_id)
            
            menu_message = flex_pill.generate_pill_identification_menu()
            line_bot_api.reply_message(event.reply_token, menu_message)
            print(f"✅ [Pill Handler] 已發送藥丸辨識選單")
            return
    
    # 處理 Postback 事件
    if hasattr(event, 'postback'):
        data = event.postback.data
        
        if data.startswith("action=select_model_mode"):
            mode = data.split("&mode=")[-1]
            if mode == "single":
                # 显示单一模型选择菜单
                menu_message = flex_pill.generate_single_model_selection_menu()
                line_bot_api.reply_message(event.reply_token, menu_message)
            elif mode == "multi":
                # 设置多模型模式状态
                UserService.save_user_simple_state(user_id, 'pill_detection_multi', minutes=10)
                guide_message = flex_pill.generate_camera_guide_menu()
                line_bot_api.reply_message(event.reply_token, guide_message)
        
        elif data.startswith("action=use_single_model"):
            model_id = data.split("&model=")[-1]
            # 设置单模型模式状态
            UserService.save_user_simple_state(user_id, f'pill_detection_single_{model_id}', minutes=10)
            guide_message = flex_pill.generate_camera_guide_menu()
            
            # 自定義模型顯示名稱
            model_display_names = {
                '1': '🧠 高精度模型',
                '2': '⚡ 高效率模型', 
                '3': '🎯 Kevin模型'
            }
            
            model_name = model_display_names.get(model_id, f'模型 {model_id}')
            reply_text = f"✅ 已選擇 {model_name}\n\n現在請拍攝藥丸照片："
            
            line_bot_api.reply_message(event.reply_token, [
                TextSendMessage(text=reply_text),
                guide_message
            ])
        
        elif data.startswith("action=get_pill_info"):
            drug_ids_str = data.split("=")[-1]
            drug_ids = drug_ids_str.split(',')
            
            print(f"    - 調試: 查詢藥品詳細資訊，drug_ids: {drug_ids}")
            
            # 从数据库查询药品详细信息，支援前綴匹配
            from ...utils.db import DB
            pill_details_list = []
            
            for drug_id in drug_ids:
                if drug_id == 'unknown' or drug_id.startswith('Detected:') or drug_id.startswith('檢測到:'):
                    continue
                    
                # 先嘗試完整匹配
                exact_match = DB.get_pills_details_by_ids([drug_id])
                if exact_match:
                    pill_details_list.extend(exact_match)
                else:
                    # 如果沒有完整匹配，嘗試前綴匹配
                    prefix = drug_id[:10] if len(drug_id) >= 10 else drug_id
                    prefix_matches = DB.get_pills_details_by_prefix(prefix)
                    if prefix_matches:
                        pill_details_list.extend(prefix_matches[:3])  # 最多取前3個匹配結果
            
            print(f"    - 調試: 找到 {len(pill_details_list)} 個藥品詳細資訊")
            
            if not pill_details_list:
                reply_message = TextSendMessage(text="抱歉，在資料庫中找不到這些藥品的詳細資訊。可能需要更新藥品資料庫或檢查藥品編號。")
            else:
                # 生成药品信息轮播
                carousel_message = flex_pill.generate_pill_info_carousel(pill_details_list)
                reply_message = carousel_message
            
            line_bot_api.reply_message(event.reply_token, reply_message)
        
        elif data == "action=show_model_info":
            info_message = flex_pill.generate_model_info_card()
            line_bot_api.reply_message(event.reply_token, info_message)
        
        elif data == "action=back_to_model_menu":
            menu_message = flex_pill.generate_pill_identification_menu()
            line_bot_api.reply_message(event.reply_token, menu_message)

def start_loading_animation(user_id, seconds=55):
    """启动 LINE Chat Loading 动画"""
    try:
        import requests
        from flask import current_app
        
        loading_url = "https://api.line.me/v2/bot/chat/loading/start"
        headers = {
            "Authorization": f"Bearer {current_app.config['LINE_CHANNEL_ACCESS_TOKEN']}",
            "Content-Type": "application/json"
        }
        data = {
            "chatId": user_id,
            "loadingSeconds": min(max(seconds, 10), 60)
        }
        
        response = requests.post(loading_url, headers=headers, json=data)
        if response.status_code == 202:
            print(f"✅ 已為用戶 {user_id} 啟動載入動畫 ({data['loadingSeconds']} 秒)")
        else:
            print(f"⚠️ 載入動畫啟動失敗: {response.status_code}")
    except Exception as e:
        print(f"❌ 載入動畫啟動異常: {e}")

def handle_image_message(event):
    """
    處理使用者傳送的圖片訊息，使用多模型 API 進行藥品辨識
    返回 True 表示已處理，False 表示未處理
    """
    # ⏱️ 開始計時：整個流程的總時間
    import time
    total_start_time = time.time()
    
    user_id = event.source.user_id
    simple_state = UserService.get_user_simple_state(user_id)
    
    # 檢查是否處於藥丸辨識狀態
    if not simple_state or not (simple_state.startswith('pill_detection_')):
        return False  # 不是藥丸辨識狀態，不處理
    from config import Config
    configuration = Configuration(access_token=Config.LINE_CHANNEL_ACCESS_TOKEN)
    line_bot_api_v3 = MessagingApi(ApiClient(configuration))
    line_bot_blob_api = MessagingApiBlob(ApiClient(configuration))
    message_id = event.message.id
    user_id = event.source.user_id
    
    start_loading_animation(user_id) # 启用加载动画
    print(f"--- [圖片訊息] 收到來自 {user_id} 的圖片 (Message ID: {message_id}) ---")
    print(f"⏱️ [時間測量] 開始處理時間: {time.strftime('%H:%M:%S', time.localtime(total_start_time))}")

    try:
        # 步驟 1 & 2: 下載並處理圖片
        step1_start = time.time()
        print("    - 步驟 1: 正在下載圖片...")
        message_content = line_bot_blob_api.get_message_content(message_id=message_id)
        image_bytes = message_content if isinstance(message_content, bytes) else b"".join(message_content.iter_content())
        if not image_bytes:
            raise ValueError("下載的圖片內容為空。")
        img_pil = Image.open(io.BytesIO(image_bytes)).convert('RGB')
        step1_end = time.time()
        step1_duration = step1_end - step1_start
        print(f"    - 步驟 1-2: 圖片處理完畢。耗時: {step1_duration:.2f} 秒")

        # 步驟 3: 根據使用者選擇的模式進行檢測
        step3_start = time.time()
        print("    - 步驟 3: 正在進行藥丸檢測...")
        print(f"    - 調試: simple_state = {simple_state}")
        
        # 從 simple_state 判斷檢測模式
        if simple_state.startswith('pill_detection_single_'):
            detection_mode = 'single'
            selected_model = simple_state.split('_')[-1]  # 提取模型ID
            print(f"    - 檢測模式: 單一模型, 選擇的模型: {selected_model}")
        elif simple_state == 'pill_detection_multi':
            detection_mode = 'multi'
            selected_model = None
            print(f"    - 檢測模式: 多模型")
        else:
            # 預設為多模型
            detection_mode = 'multi'
            selected_model = None
            print(f"    - 檢測模式: 預設多模型")
        
        all_results_for_carousel = []
        total_elapsed_time = 0
        models_status = None  # 初始化模型狀態變數

        if detection_mode == 'single':
            # --- 單一模型辨識邏輯 ---
            raw_result = None
            print(f"    - 單一模型辨識，模型ID: {selected_model}")
            
            if selected_model == '3':
                print("    - 使用單一模型: kevin模型")
                if KEVIN_MODEL_AVAILABLE:
                    raw_result = kevin_model_handler.detect_pills(pil_image=img_pil)
                else:
                    print(f"    - ❌ kevin模型不可用，KEVIN_MODEL_AVAILABLE = {KEVIN_MODEL_AVAILABLE}")
                    print(f"    - 🔄 自動切換到高精度模型作為備用")
                    # 自動使用高精度模型作為備用
                    model_info = AVAILABLE_MODELS["1"]
                    client = PillDetectionClient([model_info['url']], use_all_models=False)
                    raw_result = client.detect_pills(img_pil)
                    if raw_result: 
                        raw_result['model_name'] = f"{model_info['name']} (kevin模型備用)"
            elif selected_model in AVAILABLE_MODELS:
                model_info = AVAILABLE_MODELS[selected_model]
                print(f"    - 使用單一模型: {model_info['name']}")
                client = PillDetectionClient([model_info['url']], use_all_models=False)
                raw_result = client.detect_pills(img_pil)
                if raw_result: raw_result['model_name'] = model_info['name']
            
            if not raw_result or not raw_result.get('success'):
                raise Exception(f"模型處理失敗: {raw_result.get('error', '未知錯誤')}")
            
            all_results_for_carousel, total_elapsed_time = _standardize_and_get_db_info([raw_result])
            step3_end = time.time()
            step3_duration = step3_end - step3_start
            print(f"    - 步驟 3: 單一模型檢測完成。耗時: {step3_duration:.2f} 秒")
            
            # 為單一模型也設置狀態資訊
            model_name = raw_result.get('model_name', f'模型{selected_model}')
            models_status = {
                'total': 1,
                'successful': 1,
                'failed': 0,
                'successful_models': [model_name],
                'failed_models': []
            }

        else: # detection_mode == 'multi'
            # --- ✨ 多模型並行辨識邏輯 (包含 kevin 模型) ---
            print("    - 使用多模型同時辨識 (高精度 + 高速度 + kevin模型)")
            all_raw_results = []
            successful_models = []
            failed_models = []
            total_models = 0
            
            with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
                # 準備要執行的任務
                future_to_model = {}
                
                # 任務1: 高精度模型
                client1 = PillDetectionClient([AVAILABLE_MODELS["1"]["url"]], use_all_models=False)
                future1 = executor.submit(client1.detect_pills, img_pil)
                future_to_model[future1] = AVAILABLE_MODELS["1"]["name"]
                total_models += 1
                
                # 任務2: 高速度模型
                client2 = PillDetectionClient([AVAILABLE_MODELS["2"]["url"]], use_all_models=False)
                future2 = executor.submit(client2.detect_pills, img_pil)
                future_to_model[future2] = AVAILABLE_MODELS["2"]["name"]
                total_models += 1
                
                # 任務3: kevin模型 (如果可用)
                if KEVIN_MODEL_AVAILABLE:
                    future3 = executor.submit(kevin_model_handler.detect_pills, img_pil)
                    future_to_model[future3] = "Transformer"
                    total_models += 1

                # 等待所有任務完成並收集結果
                for future in concurrent.futures.as_completed(future_to_model):
                    model_name = future_to_model[future]
                    try:
                        result = future.result()
                        if result and result.get('success'):
                            # 為每個模型的結果加上名稱，以便後續處理
                            result['model_name'] = model_name
                            all_raw_results.append(result)
                            successful_models.append(model_name)
                            print(f"    - ✅ 模型 '{model_name}' 辨識成功")
                        else:
                            failed_models.append(model_name)
                            print(f"    - ❌ 模型 '{model_name}' 辨識失敗或無結果: {result.get('error') if result else '無回應'}")
                    except Exception as exc:
                        failed_models.append(model_name)
                        print(f"    - ❌ 模型 '{model_name}' 執行時發生嚴重錯誤: {exc}")
            
            # 將所有成功模型的結果合併並標準化
            all_results_for_carousel, total_elapsed_time = _standardize_and_get_db_info(all_raw_results)
            step3_end = time.time()
            step3_duration = step3_end - step3_start
            print(f"    - 步驟 3: 多模型檢測完成。耗時: {step3_duration:.2f} 秒")
            
            # 記錄模型狀態供後續使用
            models_status = {
                'total': total_models,
                'successful': len(successful_models),
                'failed': len(failed_models),
                'successful_models': successful_models,
                'failed_models': failed_models
            }
            
            print(f"    - 模型執行狀態總結:")
            print(f"      - 總模型數: {models_status['total']}")
            print(f"      - 成功模型: {models_status['successful']} ({', '.join(models_status['successful_models'])})")
            print(f"      - 失敗模型: {models_status['failed']} ({', '.join(models_status['failed_models'])})")

        # 步驟 4 & 5: 準備並回覆訊息
        step4_start = time.time()
        print("    - 步驟 4: 準備回覆訊息...")
        messages = []
        if not all_results_for_carousel:
            # 生成更友好的「找到 0 個藥丸」訊息
            reply_text = """🔍 很抱歉，我們沒有在您的圖片中檢測到任何藥丸。

💡 建議您可以嘗試：
• 確保圖片清晰且光線充足
• 將藥丸放在乾淨的背景上
• 避免手指遮擋藥丸
• 嘗試從不同角度拍攝

🔄 您可以重新拍攝一張照片，或選擇其他功能。"""
            messages.append(TextMessage(text=reply_text))
            # 生成字典格式的選單並轉換為 FlexContainer
            menu_dict = {
                "type": "bubble",
                "body": {
                    "type": "box",
                    "layout": "vertical",
                    "contents": [
                        {"type": "text", "text": "🤖 選擇辨識模型", "weight": "bold", "size": "lg", "align": "center"},
                        {"type": "text", "text": "請先選擇要使用的 AI 模型：", "wrap": True, "size": "sm", "margin": "md", "align": "center"}
                    ]
                },
                "footer": {
                    "type": "box",
                    "layout": "vertical",
                    "spacing": "sm",
                    "contents": [
                        {"type": "button", "style": "primary", "color": "#FF6B6B", "action": {"type": "postback", "label": "🎯 單一模型辨識", "data": "action=select_model_mode&mode=single"}},
                        {"type": "button", "style": "primary", "color": "#4ECDC4", "action": {"type": "postback", "label": "🚀 多模型同時辨識", "data": "action=select_model_mode&mode=multi"}}
                    ]
                }
            }
            messages.append(FlexMessage(alt_text="藥丸辨識選單", contents=FlexContainer.from_dict(menu_dict)))
        else:
            total_detections = sum(len(result['detections']) for result in all_results_for_carousel)
            models_count = len(all_results_for_carousel)
            
            if detection_mode == 'single':
                summary_text = f"🎯 單一模型檢測完成！\n"
                if models_status and models_status['successful_models']:
                    summary_text += f"🤖 使用模型：{models_status['successful_models'][0]}\n"
                else:
                    summary_text += f"🤖 使用模型：{all_results_for_carousel[0]['model_name']}\n"
            else:
                summary_text = f"🚀 多模型並行檢測完成！\n"
                if models_status:
                    summary_text += f"📊 {models_status['successful']}/{models_status['total']} 個模型成功回傳結果\n"
                    
                    # 顯示成功的模型
                    if models_status['successful'] > 0:
                        summary_text += f"✅ 成功模型：{', '.join(models_status['successful_models'])}\n"
                    
                    # 如果有模型失敗，添加詳細說明
                    if models_status['failed'] > 0:
                        summary_text += f"⚠️ 失敗模型：{', '.join(models_status['failed_models'])}\n"
                        summary_text += f"   ({models_status['failed']} 個模型無法辨識或發生錯誤)\n"
                else:
                    summary_text += f"📊 使用了 {models_count} 個模型\n"

            # 計算到目前為止的總處理時間
            current_time = time.time()
            current_total_duration = current_time - total_start_time
            summary_text += f"⏱️ 總耗時約 {current_total_duration:.2f} 秒\n\n"
            summary_text += "👆 請查看下方的詳細檢測結果"
            
            messages.append(TextMessage(text=summary_text))
            
            # 生成卡片輪播效果
            try:
                carousel_bubbles = []
                for result in all_results_for_carousel:
                    pills_info = result.get('pills_info', [])
                    print(f"    - 調試: 模型 {result.get('model_name')} 的結果:")
                    print(f"      - detections: {len(result.get('detections', []))}")
                    print(f"      - pills_info: {len(pills_info)}")
                    if pills_info:
                        print(f"      - 第一個藥品: {pills_info[0]}")
                    card_dict = flex_pill.generate_yolo_result_card_v2_dict(result, pills_info)
                    
                    # 添加模型名稱到 header
                    card_dict['header'] = {
                        "type": "box",
                        "layout": "vertical",
                        "contents": [
                            {"type": "text", "text": f"模型: {result.get('model_name', '未知模型')}", "weight": "bold", "size": "lg", "color": "#FFFFFF"}
                        ],
                        "backgroundColor": "#4A90E2",
                        "paddingAll": "16px"
                    }
                    carousel_bubbles.append(card_dict)
                
                # 創建輪播容器
                if len(carousel_bubbles) == 1:
                    # 只有一個結果，直接顯示單個卡片
                    messages.append(FlexMessage(alt_text="藥丸辨識結果", contents=FlexContainer.from_dict(carousel_bubbles[0])))
                else:
                    # 多個結果，使用輪播
                    carousel_dict = {
                        "type": "carousel",
                        "contents": carousel_bubbles
                    }
                    messages.append(FlexMessage(alt_text="藥丸辨識結果輪播", contents=FlexContainer.from_dict(carousel_dict)))
                    
            except Exception as e:
                print(f"    - 生成輪播卡片時發生錯誤: {e}")
                # 如果生成輪播失敗，使用簡化版本
                simple_dict = {
                    "type": "bubble",
                    "body": {
                        "type": "box",
                        "layout": "vertical",
                        "contents": [
                            {"type": "text", "text": "🔍 辨識完成", "weight": "bold", "size": "lg"},
                            {"type": "text", "text": f"使用了 {models_count} 個模型", "wrap": True, "size": "sm", "color": "#666666"}
                        ]
                    }
                }
                messages.append(FlexMessage(alt_text="藥丸辨識結果", contents=FlexContainer.from_dict(simple_dict)))
        
        # 步驟 6: 回覆訊息
        step6_start = time.time()
        print("    - 步驟 6: 正在發送回覆訊息...")
        line_bot_api_v3.reply_message(ReplyMessageRequest(reply_token=event.reply_token, messages=messages))
        step6_end = time.time()
        step4_duration = step6_end - step4_start
        
        # ⏱️ 計算總時間
        total_end_time = time.time()
        total_duration = total_end_time - total_start_time
        
        print(f"    - 步驟 4-6: Flex Message 準備與發送完成。耗時: {step4_duration:.2f} 秒")
        print("--- [圖片訊息] 處理流程成功結束 ---")
        print(f"⏱️ [時間測量] 總處理時間: {total_duration:.2f} 秒")
        print(f"⏱️ [時間分解] 圖片下載: {step1_duration:.2f}s | 模型檢測: {step3_duration:.2f}s | 回覆準備: {step4_duration:.2f}s")
        print(f"⏱️ [結束時間] {time.strftime('%H:%M:%S', time.localtime(total_end_time))}")

        # 清除使用者狀態
        if user_id in user_states:
            del user_states[user_id]
            print(f"    - 已清除使用者 {user_id} 的模型選擇狀態")
        
        # 清除簡單狀態
        UserService.delete_user_simple_state(user_id)
        return True  # 成功處理

    except Exception as e:
        print(f"!!!!!! [嚴重錯誤] 在 handle_image_message 中發生錯誤: {e} !!!!!!")
        
        # 計算錯誤發生時的總時間
        error_time = time.time() - total_start_time
        print(f"⏱️ [錯誤時間] 處理失敗，耗時: {error_time:.2f} 秒")
        
        line_bot_api_v3.reply_message(
            ReplyMessageRequest(
                reply_token=event.reply_token, 
                messages=[TextMessage(text=f"抱歉，處理您的圖片時發生內部錯誤，我們將盡快修復！")]
            )
        )
        # 清除簡單狀態
        UserService.delete_user_simple_state(user_id)
        return True  # 即使出錯也表示已處理