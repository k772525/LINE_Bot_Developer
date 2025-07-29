# --- START OF FILE: app/services/ai_processor.py (智能篩選優化版) ---

import os
import json
import time
import base64
import traceback
from typing import List, Dict, Any, Tuple
import google.generativeai as genai
from google.generativeai import types
import pymysql

def get_all_drugs_from_db(db_config: dict):
    """從資料庫獲取所有藥物"""
    try:
        # 確保 db_config 中的 port 是整數
        if 'port' in db_config and isinstance(db_config['port'], str):
            db_config['port'] = int(db_config['port'])
            
        conn = pymysql.connect(**db_config, cursorclass=pymysql.cursors.DictCursor)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT drug_id, drug_name_zh, drug_name_en, main_use, side_effects 
            FROM drug_info 
            ORDER BY drug_id
        """)
        
        all_drugs = cursor.fetchall()
        cursor.close()
        conn.close()
        
        print(f"[Smart Filter] 載入全部 {len(all_drugs)} 種藥物")
        return all_drugs
        
    except Exception as e:
        print(f"[Smart Filter] 資料庫連接失敗: {e}")
        return []

def get_frequency_database():
    """獲取頻率參考資料"""
    return [
        {"frequency_code": "QD", "frequency_name": "一日一次", "times_per_day": 1.0, "timing_description": "每日一次"},
        {"frequency_code": "BID", "frequency_name": "一日二次", "times_per_day": 2.0, "timing_description": "每日兩次"},
        {"frequency_code": "TID", "frequency_name": "一日三次", "times_per_day": 3.0, "timing_description": "每日三次"},
        {"frequency_code": "QID", "frequency_name": "一日四次", "times_per_day": 4.0, "timing_description": "每日四次"},
        {"frequency_code": "PRN", "frequency_name": "需要時使用", "times_per_day": 0.0, "timing_description": "按需使用"},
        {"frequency_code": "HS", "frequency_name": "睡前服用", "times_per_day": 1.0, "timing_description": "睡前"},
        {"frequency_code": "AC", "frequency_name": "飯前服用", "times_per_day": 0.0, "timing_description": "飯前"},
        {"frequency_code": "PC", "frequency_name": "飯後服用", "times_per_day": 0.0, "timing_description": "飯後"}
    ]

def extract_drug_keywords_batch(image_bytes_list: List[bytes], api_key: str) -> Tuple[List[str], int]:
    """使用單次API調用從多張圖片提取藥物關鍵字"""
    try:
        print(f"[Smart Filter] 批次提取 {len(image_bytes_list)} 張圖片的藥物關鍵字...")
        
        client = genai.Client(api_key=api_key)
        
        # 批次OCR prompt
        ocr_prompt = f"""請快速識別這{len(image_bytes_list)}張圖片中的藥物名稱關鍵字。
只需要提取藥物的英文名稱和中文名稱關鍵字，不需要其他資訊。
用逗號分隔，例如：ALPRAZOLAM,MOCALM,安柏寧,永康緒
請將所有圖片中的藥物關鍵字合併輸出。"""
        
        prompt_parts = [types.Part.from_text(text=ocr_prompt)]
        
        # 添加所有圖片
        for i, image_bytes in enumerate(image_bytes_list):
            prompt_parts.append(types.Part(
                inline_data=types.Blob(
                    mime_type='image/jpeg',
                    data=base64.b64encode(image_bytes).decode()
                )
            ))
        
        contents = [types.Content(role="user", parts=prompt_parts)]
        config = types.GenerateContentConfig(temperature=0)
        
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=contents,
            config=config
        )
        
        keywords_text = response.text if hasattr(response, 'text') else ""
        keywords = list(set([k.strip() for k in keywords_text.split(',') if k.strip()]))  # 去重
        
        # 統計OCR的TOKEN使用
        ocr_tokens = 0
        if hasattr(response, 'usage_metadata') and response.usage_metadata:
            ocr_tokens = getattr(response.usage_metadata, 'total_token_count', 0)
            print(f"[Smart Filter] 批次OCR Token使用: {ocr_tokens}")
        
        print(f"[Smart Filter] 批次提取關鍵字: {keywords}")
        return keywords, ocr_tokens
        
    except Exception as e:
        print(f"[Smart Filter] 批次關鍵字提取失敗: {e}")
        return [], 0

def extract_drug_keywords(image_bytes: bytes, api_key: str) -> Tuple[List[str], int]:
    """使用簡單OCR提取藥物關鍵字"""
    try:
        print("[Smart Filter] 提取藥物關鍵字...")
        
        client = genai.Client(api_key=api_key)
        
        # 簡單的OCR prompt
        ocr_prompt = """請快速識別圖片中的藥物名稱關鍵字。
只需要提取藥物的英文名稱和中文名稱關鍵字，不需要其他資訊。
用逗號分隔，例如：ALPRAZOLAM,MOCALM,安柏寧,永康緒"""
        
        prompt_parts = [types.Part.from_text(text=ocr_prompt)]
        prompt_parts.append(types.Part(
            inline_data=types.Blob(
                mime_type='image/jpeg',
                data=base64.b64encode(image_bytes).decode()
            )
        ))
        
        contents = [types.Content(role="user", parts=prompt_parts)]
        config = types.GenerateContentConfig(temperature=0)
        
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=contents,
            config=config
        )
        
        keywords_text = response.text if hasattr(response, 'text') else ""
        keywords = [k.strip() for k in keywords_text.split(',') if k.strip()]
        
        # 統計OCR的TOKEN使用
        ocr_tokens = 0
        if hasattr(response, 'usage_metadata') and response.usage_metadata:
            ocr_tokens = getattr(response.usage_metadata, 'total_token_count', 0)
            print(f"[Smart Filter] OCR Token使用: {ocr_tokens}")
        
        print(f"[Smart Filter] 提取關鍵字: {keywords}")
        return keywords, ocr_tokens
        
    except Exception as e:
        print(f"[Smart Filter] 關鍵字提取失敗: {e}")
        return [], 0

def smart_filter_drugs(all_drugs: List[Dict], keywords: List[str]) -> List[Dict]:
    """根據關鍵字智能篩選藥物"""
    if not keywords:
        print("[Smart Filter] 沒有關鍵字，使用前20種藥物")
        return all_drugs[:20]
    
    filtered_drugs = []
    
    for drug in all_drugs:
        drug_zh = drug.get('drug_name_zh', '').lower()
        drug_en = drug.get('drug_name_en', '').lower()
        
        # 檢查是否包含任何關鍵字
        for keyword in keywords:
            keyword_lower = keyword.lower()
            if (keyword_lower in drug_zh or 
                keyword_lower in drug_en or
                any(k in drug_zh for k in keyword_lower.split()) or
                any(k in drug_en for k in keyword_lower.split())):
                filtered_drugs.append(drug)
                break
    
    # 如果篩選結果太少，補充一些常用藥物
    if len(filtered_drugs) < 5:
        print(f"[Smart Filter] 篩選結果太少({len(filtered_drugs)})，補充常用藥物")
        common_drugs = all_drugs[:15]
        for drug in common_drugs:
            if drug not in filtered_drugs:
                filtered_drugs.append(drug)
                if len(filtered_drugs) >= 15:
                    break
    
    print(f"[Smart Filter] 篩選結果: {len(filtered_drugs)} 種藥物")
    return filtered_drugs

def run_analysis(image_bytes_list: List[bytes], db_config: dict, api_key: str) -> Tuple[Dict | None, Dict | None]:
    """
    智能篩選版頻率導向分析 - 節省30%TOKEN並保持完整功能
    """
    start_time = time.time()
    print("[Smart Filter] 開始智能篩選頻率導向分析...")
    
    if not image_bytes_list:
        print("[Smart Filter] 錯誤：沒有提供任何圖片資料。")
        return None, None

    try:
        # 第1步：獲取所有藥物
        all_drugs = get_all_drugs_from_db(db_config)
        if not all_drugs:
            return None, {"error": "資料庫連線失敗"}
        
        # 第2步：提取關鍵字（一次API調用處理所有圖片）
        ocr_start = time.time()
        keywords, total_ocr_tokens = extract_drug_keywords_batch(image_bytes_list, api_key)
        ocr_time = time.time() - ocr_start
        print(f"[Smart Filter] 一次API調用從 {len(image_bytes_list)} 張圖片提取到 {len(keywords)} 個唯一關鍵字")
        
        # 第3步：智能篩選
        filtered_drugs = smart_filter_drugs(all_drugs, keywords)
        
        # 第4步：獲取頻率參考
        freq_codes = get_frequency_database()
        
        # 第5步：構建完整的頻率導向分析 Prompt
        drug_ref_str = json.dumps(filtered_drugs, ensure_ascii=False, indent=2, default=str)
        freq_ref_str = json.dumps(freq_codes, ensure_ascii=False, indent=2, default=str)
        
        complete_prompt = f"""
# 任務與角色
你是一位頂尖的醫療資訊分析師。你的任務是分析我提供的{len(image_bytes_list)}張藥單圖片，並結合參考資料，將結果結構化為一個單一的 JSON 物件。

**重要提醒：我提供了{len(image_bytes_list)}張圖片，請分析所有圖片中的藥物資訊，並將所有藥物合併到同一個medications列表中。**

# 參考資料
1. **藥品資料庫參考清單 (請從中選擇)**:
{drug_ref_str}

2. **用藥頻率參考清單 (這是你唯一的頻率判斷依據)**:
{freq_ref_str}

# 輸出要求 (嚴格遵守)
請返回一個**單一的 JSON 物件**。這個物件必須包含全域資訊以及一個 `medications` 列表。列表中每一個物件對應圖片中的一筆藥物。

## 全域欄位
- `clinic_name`: (字串) 診所名稱（從任一張圖片中提取）。
- `doctor_name`: (字串) 醫師姓名（從任一張圖片中提取）。
- `visit_date`: (字串) 看診日期，必須轉為 `YYYY-MM-DD` 格式（從任一張圖片中提取）。
- `days_supply`: (字串) 總給藥天數（從任一張圖片中提取）。

## `medications` 列表中的物件欄位
**請將所有{len(image_bytes_list)}張圖片中的藥物都加入到medications列表中，不要遺漏任何一種藥物。**

- `matched_drug_id`: (字串或null) 從「藥品資料庫」中選出的最匹配藥物的 `drug_id`。如果找不到合理的匹配，此欄位必須為 `null`。
- `drug_name_zh`: (字串) 匹配到的藥物中文名，若無匹配則從圖片中提取。
- `drug_name_en`: (字串) 匹配到的藥物英文名，若無匹配則從圖片中提取。
- `main_use`: (字串) 匹配到的藥物主要用途。
- `side_effects`: (字串) 匹配到的藥物常見副作用。
- `dose_quantity`: (字串) 從圖片中解析出的「單次劑量」，包含數值和單位 (例如: '1 顆', '0.5 錠')。
- `source_image`: (整數) 該藥物來自第幾張圖片 (1, 2, 3...)。

- **【頻率解析演算法 (極其重要，你必須嚴格遵循此分層邏輯)】**:

    **第一步：確定全域天數 (`Global_Days`)**
    從圖片中找到總天數（例如 '本單發藥 3 日份'），將其數值（`3`）記錄為 `Global_Days`。這是後續計算的基礎。

    **第二步：對每種藥物進行分層判斷**

    *   **情況 A (明確指令詞)**: 如果藥物用法中包含明確的指令詞，如 `HS` (睡前), `BID` (早晚), 或 `PRN` (需要時)，請**直接**使用「用藥頻率參考清單」進行查找並填寫以下欄位。這是最高優先級。
        - `frequency_text`: 根據查到的 `frequency_name` 生成，例如 '一日二次' 或 '睡前服用'。
        - `frequency_count_code`: 填寫查到的 `frequency_code`，例如 `BID` 對應 `BID`。
        - `frequency_timing_code`: 如果有，則填寫 (例如 `AC`, `PC`)，否則為 `null`。

    *   **情況 B (需要計算)**: 如果藥物用法中**沒有**明確的指令詞 (例如只有 '飯前服用')，你**必須**啟用計算模式：
        1.  從該藥物行的用法欄中，找到總次數或總量（例如 `9.00/9` 中的 `9`）。將此記錄為 `Total_Doses`。
        2.  執行計算：`Daily_Count = Total_Doses / Global_Days`。 (例如: `9 / 3 = 3`)
        3.  使用計算出的 `Daily_Count` 值（`3`），去「用藥頻率參考清單」中查找 `times_per_day` 為 `3.0` 的項目，得到其 `frequency_code` (`TID`) 和 `frequency_name` ('一日三次')。
        4.  根據計算和查找結果，填寫以下欄位：
            - `frequency_text`: 組合 `frequency_name` 和圖片上的時機文字。例如 '一日三次 飯前服用'。
            - `frequency_count_code`: 填寫查到的 `frequency_code`，例如 `TID`。
            - `frequency_timing_code`: 從圖片的時機文字 ('飯前服用') 推斷出代碼，例如 `AC`。

請確保你的輸出是一個格式完全正確的 JSON 物件，並用 ```json ... ``` 包圍。
"""

        # API設定
        client = genai.Client(api_key=api_key)
        model_name = "gemini-2.5-flash"
        
        config = types.GenerateContentConfig(
            temperature=0,
            thinking_config=types.ThinkingConfig(thinking_budget=0),
            response_mime_type="application/json"
        )
        
        # 構建請求（包含所有圖片）
        prompt_parts = [types.Part.from_text(text=complete_prompt)]
        
        for i, image_bytes in enumerate(image_bytes_list):
            prompt_parts.append(types.Part(
                inline_data=types.Blob(
                    mime_type='image/jpeg',
                    data=base64.b64encode(image_bytes).decode()
                )
            ))
        
        contents = [types.Content(role="user", parts=prompt_parts)]
        
        # 執行分析
        print("[Smart Filter] 發送分析請求...")
        analysis_start = time.time()
        
        response = client.models.generate_content(
            model=model_name,
            contents=contents,
            config=config
        )
        
        analysis_time = time.time() - analysis_start
        
        # 處理回應
        response_text = response.text if hasattr(response, 'text') else ""
        if not response_text:
            print("[Smart Filter] 模型沒有回傳任何文字內容。")
            return None, None

        # 解析JSON
        try:
            if response_text.startswith('```json'):
                json_start = response_text.find('{')
                json_end = response_text.rfind('}') + 1
                clean_json = response_text[json_start:json_end]
                analysis_result = json.loads(clean_json)
            else:
                analysis_result = json.loads(response_text)
        except json.JSONDecodeError as e:
            print(f"[Smart Filter] JSON解析失敗: {e}")
            return None, None
        
        # 完整性評估和統計（原始邏輯）
        medications = analysis_result.get('medications', [])
        total_meds = len(medications)
        
        # 計算成功匹配數
        successful_matches = []
        for med in medications:
            matched_id = med.get('matched_drug_id')
            if matched_id and str(matched_id).lower() not in ['null', 'none', ''] and str(matched_id).strip():
                successful_matches.append(med)
        
        analysis_result['successful_match_count'] = len(successful_matches)
        
        # 頻率統計
        with_frequency = 0
        for med in medications:
            freq_text = med.get('frequency_text', '')
            freq_code = med.get('frequency_count_code', '')
            if (freq_text and freq_text not in ['null', 'N/A', None]) or \
               (freq_code and freq_code not in ['null', 'N/A', None]):
                with_frequency += 1
        
        frequency_rate = with_frequency / total_meds if total_meds > 0 else 0
        
        analysis_result['frequency_stats'] = {
            'total': total_meds,
            'with_frequency': with_frequency,
            'frequency_rate': frequency_rate
        }
        
        # 完整性評估
        if frequency_rate > 0.5:
            completeness_type = "complete_prescription"
        elif frequency_rate > 0:
            completeness_type = "partial_prescription"
        else:
            completeness_type = "drug_photo_only"
        
        analysis_result['completeness_type'] = completeness_type
        analysis_result['is_successful'] = frequency_rate > 0
        analysis_result['user_message'] = f"智能篩選分析完成，識別{total_meds}種藥物，{with_frequency}種有頻率資訊。"
        
        # 統計分析階段的TOKEN
        analysis_tokens = 0
        if hasattr(response, 'usage_metadata') and response.usage_metadata:
            analysis_prompt_tokens = getattr(response.usage_metadata, 'prompt_token_count', 0)
            analysis_completion_tokens = getattr(response.usage_metadata, 'candidates_token_count', 0)
            analysis_tokens = getattr(response.usage_metadata, 'total_token_count', 0)
        
        # 計算總TOKEN（OCR + 分析）
        total_tokens = total_ocr_tokens + analysis_tokens
        
        # 使用統計
        end_time = time.time()
        usage_info = {
            "model": model_name,
            "version": "smart_filter",
            "execution_time": end_time - start_time,
            "ocr_time": ocr_time,
            "analysis_time": analysis_time,
            "total_drugs_in_db": len(all_drugs),
            "filtered_drugs_count": len(filtered_drugs),
            "filter_ratio": len(filtered_drugs) / len(all_drugs),
            "medications_found": total_meds,
            "successful_matches": len(successful_matches),
            "frequency_rate": frequency_rate,
            "completeness_type": completeness_type,
            "is_successful": analysis_result['is_successful'],
            "images_processed": len(image_bytes_list),
            "api_calls_used": 2,  # OCR批次 + 分析
            "api_calls_saved": len(image_bytes_list) - 1,  # 節省的OCR調用次數
            "ocr_tokens": total_ocr_tokens,
            "analysis_tokens": analysis_tokens,
            "total_tokens": total_ocr_tokens + analysis_tokens,
            "token_savings": f"{((6964 - total_tokens) / 6964 * 100):.1f}%" if total_tokens > 0 else "N/A"
        }
        
        print(f"[Smart Filter] 資料庫篩選: {len(all_drugs)} → {len(filtered_drugs)} ({usage_info['filter_ratio']:.1%})")
        print(f"[Smart Filter] API調用優化: {len(image_bytes_list)}張圖片僅用2次API調用 (OCR批次+分析)")
        print(f"[Smart Filter] Token使用: OCR({total_ocr_tokens}) + 分析({analysis_tokens}) = {total_tokens}")
        print(f"[Smart Filter] 處理圖片數量: {len(image_bytes_list)}")
        print(f"[Smart Filter] Token節省: {usage_info['token_savings']}")
        print(f"[Smart Filter] 執行時間: {end_time - start_time:.4f}s")
        print(f"[Smart Filter] 成功匹配: {len(successful_matches)}/{total_meds}")
        print(f"[Smart Filter] 頻率完整度: {frequency_rate:.1%}")
        print(f"[Smart Filter] 完整性類型: {completeness_type}")
        
        return analysis_result, usage_info

    except Exception as e:
        print(f"[Smart Filter] 分析處理錯誤: {e}")
        traceback.print_exc()
        return None, None

# --- END OF FILE: app/services/ai_processor.py (智能篩選優化版) ---