# --- 修復版本的 ai_processor.py ---
# 這個文件修復了所有 genai.Client 的錯誤

import os
import json
import time
import base64
import asyncio
import concurrent.futures
from typing import List, Dict, Any, Tuple
import google.generativeai as genai
from google.generativeai import types
import pymysql

def get_all_drugs_from_db(db_config: dict):
    """從資料庫獲取所有藥物資訊"""
    try:
        connection = pymysql.connect(**db_config)
        with connection.cursor() as cursor:
            cursor.execute("SELECT drug_id, drug_name_zh, drug_name_en, main_use, side_effects FROM drug_info")
            return cursor.fetchall()
    except Exception as e:
        print(f"資料庫查詢失敗: {e}")
        return []
    finally:
        if 'connection' in locals():
            connection.close()

def analyze_prescription_with_ai(image_data: str, api_key: str) -> dict:
    """使用 Gemini AI 分析藥單圖片"""
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel("gemini-1.5-flash")

        prompt = """
你是一個專業的藥單分析助手。請分析以下藥單圖片中的資訊，並以JSON格式回傳結果。

請提取以下資訊：
1. 診所名稱 (clinic_name)
2. 醫師姓名 (doctor_name)  
3. 就診日期 (visit_date) - 格式: YYYY-MM-DD
4. 藥品天數 (days_supply) - 數字
5. 藥物清單 (medications) - 每個藥物包含:
   - drug_name_zh: 中文藥名
   - drug_name_en: 英文藥名 (如果有)
   - dose_quantity: 劑量 (如: "1錠", "5ml")
   - frequency_count_code: 頻率代碼 (如: "QD", "BID", "TID", "QID")
   - frequency_timing_code: 時間代碼 (如: "AC", "PC", "HS")
   - main_use: 主要用途
   - side_effects: 副作用

請確保回傳格式為有效的JSON，不要包含任何其他文字。
"""

        # 準備圖片內容
        image_part = {
            "mime_type": "image/jpeg", 
            "data": image_data
        }
        
        response = model.generate_content(
            [prompt, image_part],
            generation_config=genai.types.GenerationConfig(
                temperature=0.1,
                top_p=0.8,
                top_k=40,
                max_output_tokens=2048,
            )
        )

        if response.text:
            # 清理回應文字，移除可能的 markdown 標記
            clean_text = response.text.strip()
            if clean_text.startswith('```json'):
                clean_text = clean_text[7:]
            if clean_text.endswith('```'):
                clean_text = clean_text[:-3]
            
            return json.loads(clean_text.strip())
        else:
            return {"error": "AI 分析沒有回傳結果"}

    except json.JSONDecodeError as e:
        print(f"JSON 解析錯誤: {e}")
        return {"error": f"JSON 解析失敗: {str(e)}"}
    except Exception as e:
        print(f"AI 分析失敗: {e}")
        return {"error": f"AI 分析失敗: {str(e)}"}

def match_drugs_with_database(prescription_data: dict, drug_database: list, api_key: str) -> dict:
    """使用 AI 將藥單中的藥物與資料庫進行匹配"""
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel("gemini-1.5-flash")

        prompt = f"""
你是一個專業的藥物資料庫匹配助手。請將以下從藥單識別出的藥物資訊與提供的藥物資料庫進行匹配。

藥單識別結果：
{json.dumps(prescription_data, ensure_ascii=False, indent=2)}

藥物資料庫：
{json.dumps(drug_database, ensure_ascii=False, indent=2)}

請為每個藥物找到最佳匹配，並回傳JSON格式結果。匹配規則：
1. 優先匹配中文藥名
2. 其次匹配英文藥名
3. 考慮藥物用途的相似性
4. 如果找不到匹配，matched_drug_id 設為 null

回傳格式：
{{
  "matched_medications": [
    {{
      "original_drug_name_zh": "原始中文藥名",
      "original_drug_name_en": "原始英文藥名",
      "matched_drug_id": "匹配到的藥物ID或null",
      "confidence_score": 0.95,
      "match_reason": "匹配原因說明"
    }}
  ]
}}

請確保回傳有效的JSON格式。
"""

        response = model.generate_content(
            prompt,
            generation_config=genai.types.GenerationConfig(
                temperature=0.1,
                top_p=0.8,
                top_k=40,
                max_output_tokens=2048,
            )
        )

        if response.text:
            clean_text = response.text.strip()
            if clean_text.startswith('```json'):
                clean_text = clean_text[7:]
            if clean_text.endswith('```'):
                clean_text = clean_text[:-3]
            
            return json.loads(clean_text.strip())
        else:
            return {"error": "AI 匹配沒有回傳結果"}

    except json.JSONDecodeError as e:
        print(f"JSON 解析錯誤: {e}")
        return {"error": f"JSON 解析失敗: {str(e)}"}
    except Exception as e:
        print(f"AI 匹配失敗: {e}")
        return {"error": f"AI 匹配失敗: {str(e)}"}

def parse_text_based_reminder_ultra_fast(text: str) -> dict:
    """
    超快速本地解析用藥提醒，避免API調用
    """
    import re
    
    # 快速檢查是否包含藥物關鍵字
    if not any(keyword in text for keyword in ['藥', '血壓', '血糖', '胃', '維他命', '鈣片']):
        return None
    
    result = {
        'member': '本人',
        'drug_name': None,
        'dose_quantity': None,
        'frequency_name': None,
        'time_slots': [],
        'notes': '語音輸入',
        'confidence': 0.8
    }
    
    # 快速藥物名稱提取
    drug_patterns = [
        r'血壓藥', r'血糖藥', r'胃藥', r'感冒藥', r'止痛藥', 
        r'維他命', r'鈣片', r'血脂藥', r'心臟藥'
    ]
    
    for pattern in drug_patterns:
        if re.search(pattern, text):
            result['drug_name'] = pattern
            break
    
    if not result['drug_name']:
        # 嘗試提取其他藥物名稱
        drug_match = re.search(r'([\w\u4e00-\u9fff]+)藥', text)
        if drug_match:
            result['drug_name'] = drug_match.group(0)
    
    # 快速時間提取
    time_patterns = [
        (r'(\d{1,2})點', lambda m: f"{int(m.group(1)):02d}:00"),
        (r'早上', '08:00'),
        (r'中午', '12:00'), 
        (r'下午', '14:00'),
        (r'晚上', '20:00'),
        (r'睡前', '22:00')
    ]
    
    times = []
    for pattern, replacement in time_patterns:
        if isinstance(pattern, str):
            if pattern in text:
                times.append(replacement)
        else:
            matches = re.finditer(pattern, text)
            for match in matches:
                times.append(replacement(match))
    
    result['time_slots'] = list(set(times))  # 去重
    
    # 快速劑量提取
    dose_match = re.search(r'(\d+)[顆粒錠片]', text)
    if dose_match:
        result['dose_quantity'] = f"{dose_match.group(1)}顆"
    else:
        result['dose_quantity'] = '1顆'  # 預設值
    
    # 快速頻率檢測
    if '早上' in text and '晚上' in text:
        result['frequency_name'] = 'BID'
    elif any(word in text for word in ['每天', '一天一次']):
        result['frequency_name'] = 'QD'
    elif '三次' in text:
        result['frequency_name'] = 'TID'
    else:
        result['frequency_name'] = 'QD'
    
    return result if result['drug_name'] else None

def parse_text_based_reminder(text: str, api_key: str) -> dict:
    """解析文字形式的用藥提醒"""
    if not api_key:
        print("警告: 未提供 GEMINI_API_KEY，無法使用 AI 解析功能")
        return None

    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel("gemini-1.5-flash")

        prompt = f"""
你是一個專業的用藥提醒分析助手。請分析以下文字，提取用藥提醒的相關資訊。

輸入文字："{text}"

請提取以下資訊並以JSON格式回傳：
{{
  "member": "提醒對象 (如：本人、媽媽、爸爸等)",
  "drug_name": "藥物名稱",
  "dose_quantity": "劑量 (如：1錠、5ml等)",
  "frequency_name": "頻率描述 (如：一天三次、每天早晚等)",
  "time_slots": ["具體時間1", "具體時間2", ...],
  "notes": "備註或特殊說明",
  "confidence": 0.95
}}

注意事項：
1. 如果沒有明確指定對象，member 設為 "本人"
2. 時間格式使用 HH:MM (24小時制)
3. 如果只有頻率沒有具體時間，time_slots 可以為空陣列
4. confidence 表示解析的信心度 (0-1)

請確保回傳有效的JSON格式。
"""

        response = model.generate_content(
            prompt,
            generation_config=genai.types.GenerationConfig(
                temperature=0.1,
                top_p=0.8,
                top_k=40,
                max_output_tokens=1024,
            )
        )

        if response.text:
            clean_text = response.text.strip()
            if clean_text.startswith('```json'):
                clean_text = clean_text[7:]
            if clean_text.endswith('```'):
                clean_text = clean_text[:-3]
            
            result = json.loads(clean_text.strip())
            
            # 驗證結果
            if result.get('confidence', 0) > 0.7:
                return result
            else:
                print(f"AI 解析信心度過低: {result.get('confidence', 0)}")
                return None

    except json.JSONDecodeError as e:
        print(f"JSON 解析錯誤: {e}")
        return None
    except Exception as e:
        print(f"AI 解析失敗: {e}")
        return None

def run_analysis(image_bytes_list, db_config, api_key):
    """智能分析模式的主要入口函數"""
    try:
        print(f"[Smart Analysis] 開始智能分析，處理 {len(image_bytes_list)} 張圖片")
        
        # 使用第一張圖片進行分析
        if not image_bytes_list:
            raise ValueError("沒有提供圖片資料")
        
        # 將圖片轉換為 base64
        image_b64 = base64.b64encode(image_bytes_list[0]).decode('utf-8')
        
        # 使用 AI 分析藥單
        analysis_result = analyze_prescription_with_ai(image_b64, api_key)
        
        if analysis_result.get('error'):
            raise RuntimeError(analysis_result['error'])
        
        # 獲取藥物資料庫
        drug_database = get_all_drugs_from_db(db_config)
        
        # 進行藥物匹配
        if analysis_result.get('medications'):
            match_result = match_drugs_with_database(analysis_result, drug_database, api_key)
            
            if not match_result.get('error'):
                # 更新藥物資訊
                matched_medications = match_result.get('matched_medications', [])
                for i, med in enumerate(analysis_result.get('medications', [])):
                    if i < len(matched_medications):
                        matched_med = matched_medications[i]
                        med['matched_drug_id'] = matched_med.get('matched_drug_id')
                        med['confidence_score'] = matched_med.get('confidence_score', 0.8)
        
        # 添加統計資訊
        medications = analysis_result.get('medications', [])
        successful_matches = len([med for med in medications if med.get('matched_drug_id')])
        
        analysis_result.update({
            'successful_match_count': successful_matches,
            'frequency_stats': {
                'total': len(medications),
                'with_frequency': len(medications),
                'frequency_rate': 1.0 if medications else 0
            },
            'completeness_type': 'smart_analysis',
            'is_successful': len(medications) > 0,
            'user_message': f"智能分析完成，識別 {len(medications)} 種藥物，成功匹配 {successful_matches} 種。"
        })
        
        # 使用統計
        usage_info = {
            'model': 'smart_analysis',
            'version': 'gemini-1.5-flash',
            'execution_time': 0,  # 簡化版本不計算時間
            'total_tokens': 0,    # 簡化版本不計算 tokens
            'api_status': 'success',
            'processing_mode': 'smart_filter'
        }
        
        print(f"[Smart Analysis] 分析完成，識別 {len(medications)} 種藥物")
        return analysis_result, usage_info
        
    except Exception as e:
        print(f"[Smart Analysis] 分析失敗: {e}")
        error_result = {
            'clinic_name': None,
            'doctor_name': None,
            'visit_date': None,
            'days_supply': None,
            'medications': [],
            'successful_match_count': 0,
            'is_successful': False,
            'user_message': f"分析失敗: {str(e)}"
        }
        usage_info = {
            'model': 'smart_analysis',
            'api_status': 'error',
            'error': str(e)
        }
        return error_result, usage_info

# 其他輔助函數
def _preprocess_voice_text(text: str) -> str:
    """預處理語音轉文字的常見錯誤"""
    corrections = {
        '亮血壓': '量血壓',
        '記體重': '記體重', 
        '血壓要': '血壓藥',
        '血糖要': '血糖藥',
        '胃要': '胃藥',
        '西西': 'ml',
        'CC': 'ml'
    }
    
    corrected = text
    for wrong, correct in corrections.items():
        corrected = corrected.replace(wrong, correct)
    
    return corrected