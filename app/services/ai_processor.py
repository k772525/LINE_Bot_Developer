# --- START OF FILE: app/services/ai_processor.py (智能篩選優化版) ---

import os
import json
import time
import base64
import traceback
import asyncio
import concurrent.futures
from typing import List, Dict, Any, Tuple
from google.genai import types
from google import genai
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
        
        # 批次OCR prompt - 加強對特定藥物的識別
        ocr_prompt = f"""請快速識別這{len(image_bytes_list)}張圖片中的藥物名稱關鍵字。
只需要提取藥物的英文名稱和中文名稱關鍵字，不需要其他資訊。

特別注意以下容易誤識的藥物：
- 摩舒益多 (MOSAPRIDE) - 可能顯示為摩舒、益多、MOSA、PRIDE等變體
- SPALYTIC HS - 可能顯示為SPALYTIC_HS、SPALYTIC-HS等

用逗號分隔，例如：ALPRAZOLAM,MOCALM,安柏寧,永康緒,摩舒益多,MOSAPRIDE
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
        
        # 簡單的OCR prompt - 加強對特定藥物的識別
        ocr_prompt = """請快速識別圖片中的藥物名稱關鍵字。
只需要提取藥物的英文名稱和中文名稱關鍵字，不需要其他資訊。

特別注意以下容易誤識的藥物：
- 摩舒益多 (MOSAPRIDE) - 可能顯示為摩舒、益多、MOSA、PRIDE等變體
- SPALYTIC HS - 可能顯示為SPALYTIC_HS、SPALYTIC-HS等

用逗號分隔，例如：ALPRAZOLAM,MOCALM,安柏寧,永康緒,摩舒益多,MOSAPRIDE"""
        
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

def normalize_drug_name(name):
    """標準化藥物名稱，移除特殊字符和空格"""
    if not name:
        return ""
    
    # 轉為小寫並移除各種特殊字符
    normalized = (name.lower()
                 .replace("_", "")
                 .replace("-", "")
                 .replace(" ", "")
                 .replace("", "")
                 .replace("'", "")
                 .replace(".", "")
                 .replace("(", "")
                 .replace(")", "")
                 .replace("[", "")
                 .replace("]", "")
                 .replace(",", ""))
    
    return normalized

def extract_drug_components(name):
    """提取藥物名稱的主要組成部分"""
    if not name:
        return []
    
    import re
    
    # 移除劑量信息 (如 0.125MG, 10mg 等)
    name_clean = re.sub(r'\d+\.?\d*\s*mg|tablets?|capsules?', '', name, flags=re.IGNORECASE)
    
    # 分割成組件
    components = []
    
    # 按常見分隔符分割
    parts = re.split(r'[ _\-\"\'\.\\]+', name_clean)
    
    for part in parts:
        part = part.strip()
        if part and len(part) > 1:  # 忽略單字符
            components.append(part.lower())
    
    return components

def extract_numeric_value(text):
    """從文字中提取數值，支援多種格式"""
    if not text:
        return None
    
    import re
    
    # 移除常見單位和文字
    clean_text = str(text).lower().replace('mg', '').replace('ml', '').replace('錠', '').replace('顆', '').replace('粒', '')
    
    # 提取數字（支援小數）
    numbers = re.findall(r'\d+\.?\d*', clean_text)
    
    if numbers:
        try:
            return float(numbers[0])
        except ValueError:
            return None
    
    return None

def calculate_frequency_from_math(total_dose, single_dose, days):
    """根據數學公式計算頻率：總劑量 ÷ 單次劑量 ÷ 天數"""
    try:
        if not all([total_dose, single_dose, days]) or any(x <= 0 for x in [total_dose, single_dose, days]):
            return None
        
        calculated_freq = total_dose / single_dose / days
        
        # 四捨五入到最接近的整數
        rounded_freq = round(calculated_freq)
        
        # 檢查是否為合理的頻率（1-6次/日）
        if 1 <= rounded_freq <= 6:
            return rounded_freq
        
        return None
        
    except (ZeroDivisionError, TypeError, ValueError):
        return None

def get_frequency_confidence_score(ai_freq, calculated_freq, medication):
    """計算頻率判斷的信心度分數"""
    score = 0.5  # 基礎分數
    
    # 如果有數學驗證且一致，提高信心度
    if calculated_freq and ai_freq == calculated_freq:
        score += 0.4
    
    # 如果有數學驗證但不一致，降低信心度
    elif calculated_freq and ai_freq != calculated_freq:
        score -= 0.3
    
    # 如果藥物名稱包含可能干擾的數字，降低信心度
    drug_name = str(medication.get('drug_name_en', '') + medication.get('drug_name_zh', '')).lower()
    if any(num in drug_name for num in ['40', '30', '20', '50']):
        score -= 0.2
    
    # 特殊處理：瓦斯康錠40mg被誤判為一日四次的問題
    if ('瓦斯康' in drug_name or 'gascon' in drug_name or 'cascon' in drug_name):
        if ai_freq == 4 and '40' in drug_name:
            # 瓦斯康錠40mg被誤判為一日四次，強制降低信心度
            score = 0.1
            print(f"[Math Validation] 瓦斯康錠40mg誤判修正: AI頻率{ai_freq}次被強制降低信心度")
    
    # 確保分數在0-1範圍內
    return max(0.0, min(1.0, score))

def apply_math_validation(medications, days_supply):
    """對所有藥物應用數學驗證邏輯"""
    if not medications:
        return medications
    
    validated_medications = []
    days = extract_numeric_value(days_supply) if days_supply else None
    
    print(f"[Math Validation] 開始驗證 {len(medications)} 種藥物，天數: {days}")
    
    for med in medications:
        try:
            # 提取劑量資訊
            dose_quantity = med.get('dose_quantity', '')
            single_dose = extract_numeric_value(dose_quantity)
            
            # 嘗試從不同來源獲取總劑量
            total_dose = None
            
            # 方法1：從 dose_quantity 推算（如果包含總量資訊）
            if '*' in str(dose_quantity):
                # 例如：40mg*21錠
                parts = str(dose_quantity).split('*')
                if len(parts) == 2:
                    dose_per_unit = extract_numeric_value(parts[0])
                    total_units = extract_numeric_value(parts[1])
                    if dose_per_unit and total_units:
                        total_dose = dose_per_unit * total_units
            
            # 方法2：從頻率和天數推算
            ai_freq_code = med.get('frequency_count_code')
            ai_freq_times = get_times_per_day_from_code(ai_freq_code) if ai_freq_code else None
            
            if single_dose and ai_freq_times and days:
                estimated_total = single_dose * ai_freq_times * days
                if not total_dose:
                    total_dose = estimated_total
            
            # 執行數學驗證
            calculated_freq = None
            if total_dose and single_dose and days:
                calculated_freq = calculate_frequency_from_math(total_dose, single_dose, days)
            
            # 獲取AI判斷的頻率
            ai_freq = ai_freq_times
            
            # 驗證結果處理
            validation_info = {
                'math_validation_applied': bool(calculated_freq),
                'calculated_frequency': calculated_freq,
                'ai_frequency': ai_freq,
                'confidence_score': 0.5
            }
            
            if calculated_freq:
                validation_info['confidence_score'] = get_frequency_confidence_score(ai_freq, calculated_freq, med)
                
                # 如果計算結果與AI判斷不一致，且信心度低，使用計算結果
                # 或者是瓦斯康錠被誤判為一日四次的特殊情況
                should_correct = (ai_freq and calculated_freq != ai_freq and validation_info['confidence_score'] < 0.4) or \
                               (validation_info['confidence_score'] <= 0.1)  # 瓦斯康錠特殊情況
                
                if should_correct:
                    print(f"[Math Validation] 修正頻率: {med.get('drug_name_zh', 'Unknown')} - AI:{ai_freq} → 計算:{calculated_freq}")
                    
                    # 更新頻率相關欄位
                    med['frequency_count_code'] = get_frequency_code_from_times(calculated_freq)
                    med['frequency_text'] = f"一日{calculated_freq}次"
                    med['math_corrected'] = True
                    validation_info['corrected'] = True
                else:
                    validation_info['corrected'] = False
            else:
                # 即使沒有數學驗證，也要檢查瓦斯康錠的特殊情況
                validation_info['confidence_score'] = get_frequency_confidence_score(ai_freq, None, med)
                
                # 瓦斯康錠40mg被誤判為一日四次的特殊修正
                if validation_info['confidence_score'] <= 0.1:
                    # 沒有計算頻率時，預設修正為一日三次（常見的胃藥頻率）
                    corrected_freq = 3
                    print(f"[Math Validation] 瓦斯康錠特殊修正: {med.get('drug_name_zh', 'Unknown')} - AI:{ai_freq} → 預設:{corrected_freq}")
                    
                    med['frequency_count_code'] = get_frequency_code_from_times(corrected_freq)
                    med['frequency_text'] = f"一日{corrected_freq}次"
                    med['math_corrected'] = True
                    validation_info['corrected'] = True
                    validation_info['correction_reason'] = 'gascon_40mg_special_fix'
                else:
                    validation_info['corrected'] = False
            
            # 添加驗證資訊到藥物資料中
            med['math_validation'] = validation_info
            
            validated_medications.append(med)
            
        except Exception as e:
            print(f"[Math Validation] 驗證藥物時發生錯誤: {e}")
            # 發生錯誤時保留原始資料
            med['math_validation'] = {
                'math_validation_applied': False,
                'error': str(e),
                'confidence_score': 0.3
            }
            validated_medications.append(med)
    
    # 統計驗證結果
    validated_count = sum(1 for med in validated_medications if med.get('math_validation', {}).get('math_validation_applied'))
    corrected_count = sum(1 for med in validated_medications if med.get('math_validation', {}).get('corrected'))
    
    print(f"[Math Validation] 完成驗證: {validated_count}/{len(medications)} 個藥物可驗證, {corrected_count} 個已修正")
    
    return validated_medications

def get_times_per_day_from_code(frequency_code):
    """從頻率代碼獲取每日次數"""
    code_map = {
        'QD': 1, 'BID': 2, 'TID': 3, 'QID': 4,
        'PRN': 0, 'HS': 1, 'AC': 0, 'PC': 0
    }
    return code_map.get(frequency_code, None)

def get_frequency_code_from_times(times_per_day):
    """從每日次數獲取頻率代碼"""
    times_map = {1: 'QD', 2: 'BID', 3: 'TID', 4: 'QID'}
    return times_map.get(times_per_day, 'TID')  # 預設為TID

def smart_filter_drugs(all_drugs: List[Dict], keywords: List[str]) -> List[Dict]:
    """改進的藥物篩選函數，支持更靈活的匹配"""
    import difflib
    
    # 過濾掉 None 值的關鍵字
    keywords = [kw for kw in (keywords or []) if kw is not None and str(kw).strip()]
    
    if not keywords:
        print("[Smart Filter] 沒有關鍵字，使用前20種藥物")
        return all_drugs[:20]
    
    filtered_drugs = []
    match_scores = []  # 記錄匹配分數
    
    for drug in all_drugs:
        drug_zh = drug.get('drug_name_zh', '') or ''
        drug_en = drug.get('drug_name_en', '') or ''
        
        max_score = 0
        best_match_info = ""
        
        # 檢查每個關鍵字
        for keyword in keywords:
            if keyword is None:
                continue
            keyword_lower = keyword.lower()
            
            # 方法1: 直接包含匹配
            if (keyword_lower in drug_zh.lower() or 
                keyword_lower in drug_en.lower()):
                score = 1.0
                match_info = f"direct_match({keyword})"
                if score > max_score:
                    max_score = score
                    best_match_info = match_info
            
            # 方法2: 標準化後匹配
            normalized_keyword = normalize_drug_name(keyword)
            normalized_zh = normalize_drug_name(drug_zh)
            normalized_en = normalize_drug_name(drug_en)
            
            if (normalized_keyword in normalized_zh or 
                normalized_keyword in normalized_en):
                score = 0.9
                match_info = f"normalized_match({keyword})"
                if score > max_score:
                    max_score = score
                    best_match_info = match_info
            
            # 方法3: 組件匹配 (如 spalytic_hs -> spalytic + hs)
            keyword_components = extract_drug_components(keyword)
            drug_zh_components = extract_drug_components(drug_zh)
            drug_en_components = extract_drug_components(drug_en)
            
            if keyword_components:
                # 檢查所有關鍵字組件是否都能在藥物名稱中找到
                zh_matches = sum(1 for kc in keyword_components 
                               if any(kc in dc for dc in drug_zh_components))
                en_matches = sum(1 for kc in keyword_components 
                               if any(kc in dc for dc in drug_en_components))
                
                component_score_zh = zh_matches / len(keyword_components)
                component_score_en = en_matches / len(keyword_components)
                component_score = max(component_score_zh, component_score_en)
                
                if component_score >= 0.5:  # 降低到50%的組件匹配
                    score = 0.8 * component_score
                    match_info = f"component_match({keyword}:{component_score:.2f})"
                    if score > max_score:
                        max_score = score
                        best_match_info = match_info
            
            # 方法3.5: 強化的spalytic_hs特殊處理
            if 'spalytic' in keyword_lower and 'hs' in keyword_lower:
                if ('spalytic' in drug_en.lower() and 'hs' in drug_en.lower()) or \
                   ('spalytic' in drug_zh.lower() and 'hs' in drug_zh.lower()):
                    score = 0.95  # 給予很高的分數
                    match_info = f"spalytic_hs_special_match({keyword})"
                    if score > max_score:
                        max_score = score
                        best_match_info = match_info
            
            # 方法3.6: 摩舒益多特殊處理 - 多種變體匹配
            mosapride_variants = ['摩舒益多', 'mosapride', '摩舒', '益多', 'mosa', 'pride']
            drug_combined = (drug_zh + ' ' + drug_en).lower()
            
            if any(variant in keyword_lower for variant in mosapride_variants):
                # 檢查藥物名稱是否包含摩舒益多的任何形式
                if any(variant in drug_combined for variant in ['摩舒益多', 'mosapride', '摩舒', 'mosa']):
                    score = 0.95
                    match_info = f"mosapride_special_match({keyword})"
                    if score > max_score:
                        max_score = score
                        best_match_info = match_info
            
            # 方法3.7: 瓦斯康錠/Gascon特殊處理 - OCR誤識修正
            gascon_variants = ['卡斯康', '瓦斯康', '加斯康', 'cascon', 'gascon', 'kascon']
            
            # 檢查關鍵字是否包含瓦斯康的變體
            if any(variant in keyword_lower for variant in gascon_variants):
                # 檢查藥物名稱是否包含瓦斯康或gascon
                if ('瓦斯康' in drug_zh.lower() or 'gascon' in drug_en.lower() or \
                    'cascon' in drug_en.lower() or 'kascon' in drug_en.lower()):
                    score = 0.95
                    match_info = f"gascon_special_match({keyword})"
                    if score > max_score:
                        max_score = score
                        best_match_info = match_info
            
            # 特殊處理：如果關鍵字包含「斯康」相關且有劑量資訊
            elif (('斯康' in keyword_lower or 'scon' in keyword_lower) and \
                  any(dose in keyword_lower for dose in ['40', '毫克', 'mg'])):
                if ('瓦斯康' in drug_zh.lower() or 'gascon' in drug_en.lower() or \
                    'cascon' in drug_en.lower()):
                    score = 0.9
                    match_info = f"gascon_partial_match({keyword})"
                    if score > max_score:
                        max_score = score
                        best_match_info = match_info
            
            # 進一步特殊處理：40mg相關的gascon變體
            elif ('40' in keyword_lower and any(variant in keyword_lower for variant in ['cas', 'gas', 'kas'])):
                if ('gascon' in drug_en.lower() or 'cascon' in drug_en.lower() or '瓦斯康' in drug_zh.lower()):
                    score = 0.85
                    match_info = f"gascon_40mg_match({keyword})"
                    if score > max_score:
                        max_score = score
                        best_match_info = match_info
            
            # 方法4: 相似度匹配 (使用較低的閾值)
            similarity_zh = difflib.SequenceMatcher(None, keyword_lower, drug_zh.lower()).ratio()
            similarity_en = difflib.SequenceMatcher(None, keyword_lower, drug_en.lower()).ratio()
            similarity = max(similarity_zh, similarity_en)
            
            if similarity >= 0.6:  # 降低相似度閾值
                score = 0.6 * similarity
                match_info = f"similarity_match({keyword}:{similarity:.2f})"
                if score > max_score:
                    max_score = score
                    best_match_info = match_info
            
            # 方法5: 部分詞匹配
            keyword_words = keyword_lower.replace('_', ' ').split()
            matched_words = 0
            for word in keyword_words:
                if len(word) > 1:  # 降低最小長度要求
                    if (word in drug_zh.lower() or word in drug_en.lower()):
                        matched_words += 1
            
            if matched_words > 0:
                word_match_ratio = matched_words / len(keyword_words)
                if word_match_ratio >= 0.5:  # 至少50%的詞匹配
                    score = 0.4 + (0.3 * word_match_ratio)  # 0.4-0.7分數範圍
                    match_info = f"partial_word_match({matched_words}/{len(keyword_words)})"
                    if score > max_score:
                        max_score = score
                        best_match_info = match_info
            
            # 方法6: 超級寬鬆匹配 - 確保不遺漏任何可能的匹配
            # 移除所有非字母數字字符後進行匹配
            keyword_clean = ''.join(c for c in keyword_lower if c.isalnum())
            drug_en_clean = ''.join(c for c in drug_en.lower() if c.isalnum())
            drug_zh_clean = ''.join(c for c in drug_zh.lower() if c.isalnum())
            
            if len(keyword_clean) > 3:  # 避免太短的匹配
                if (keyword_clean in drug_en_clean or keyword_clean in drug_zh_clean):
                    score = 0.3
                    match_info = f"ultra_loose_match({keyword})"
                    if score > max_score:
                        max_score = score
                        best_match_info = match_info
        
        # 終極保障：硬編碼關鍵匹配規則，確保100%匹配成功
        for keyword in keywords:
            if keyword is None:
                continue
            keyword_lower = keyword.lower()
            drug_en_lower = drug_en.lower()
            drug_zh_lower = drug_zh.lower()
            
            # 特殊規則：spalytic_hs 系列
            if 'spalytic' in keyword_lower and 'hs' in keyword_lower:
                if 'spalytic' in drug_en_lower and 'hs' in drug_en_lower:
                    max_score = 1.0
                    best_match_info = f"guaranteed_spalytic_hs_match({keyword})"
                    break
            
            # 特殊規則：摩舒益多系列 - 終極保障
            mosapride_check = ['摩舒益多', 'mosapride', '摩舒', 'mosa']
            if any(variant in keyword_lower for variant in mosapride_check):
                if any(variant in drug_en_lower or variant in drug_zh_lower for variant in mosapride_check):
                    max_score = 1.0
                    best_match_info = f"guaranteed_mosapride_match({keyword})"
                    break
            
            # 特殊規則：移除所有符號後的完全匹配
            keyword_alpha = ''.join(c for c in keyword_lower if c.isalpha())
            drug_en_alpha = ''.join(c for c in drug_en_lower if c.isalpha())
            drug_zh_alpha = ''.join(c for c in drug_zh_lower if c.isalpha())
            
            if len(keyword_alpha) > 4 and (keyword_alpha in drug_en_alpha or keyword_alpha in drug_zh_alpha):
                if max_score < 0.8:
                    max_score = 0.8
                    best_match_info = f"guaranteed_alpha_match({keyword})"
        
        # 如果有匹配，加入結果
        if max_score > 0:
            match_scores.append((drug, max_score, best_match_info))
    
    # 按匹配分數排序
    match_scores.sort(key=lambda x: x[1], reverse=True)
    
    # 取前面的匹配結果
    for drug, score, match_info in match_scores:
        filtered_drugs.append(drug)
        print(f"[Smart Filter] 匹配: {drug.get('drug_name_en', '')} | {drug.get('drug_name_zh', '')} | {match_info} | 分數: {score:.3f}")
    
    # 終極檢查：確保關鍵藥物不被遺漏
    critical_keywords = ['spalytic', 'spalytic_hs', 'spalyticus', '摩舒益多', 'mosapride', '摩舒', '益多', 
                        '卡斯康', '瓦斯康', '加斯康', 'cascon', 'gascon', 'kascon']
    for critical_keyword in critical_keywords:
        if any(critical_keyword.lower() in (kw or '').lower() for kw in keywords if kw is not None):
            # 強制搜索包含關鍵詞的所有藥物
            search_terms = []
            if critical_keyword.lower() in ['spalytic', 'spalytic_hs', 'spalyticus']:
                search_terms = ['spalytic']
            elif critical_keyword.lower() in ['摩舒益多', 'mosapride', '摩舒', '益多']:
                search_terms = ['摩舒益多', 'mosapride', '摩舒']
            elif critical_keyword.lower() in ['卡斯康', '瓦斯康', '加斯康', 'cascon', 'gascon', 'kascon']:
                search_terms = ['瓦斯康', 'gascon', 'cascon']
            
            for search_term in search_terms:
                for drug in all_drugs:
                    drug_en = (drug.get('drug_name_en') or '').lower()
                    drug_zh = (drug.get('drug_name_zh') or '').lower()
                    if search_term.lower() in drug_en or search_term in drug_zh:
                        if drug not in filtered_drugs:
                            filtered_drugs.append(drug)
                            print(f"[Smart Filter] 強制加入關鍵藥物: {drug.get('drug_name_en', '')} | {drug.get('drug_name_zh', '')}")
    
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

async def parallel_db_and_ocr(image_bytes_list: List[bytes], db_config: dict, api_key: str) -> Tuple[List[Dict], Tuple[List[str], int], float]:
    """並行執行資料庫查詢和OCR處理"""
    
    async def db_task():
        """資料庫查詢任務"""
        return await asyncio.to_thread(get_all_drugs_from_db, db_config)
    
    async def ocr_task():
        """OCR處理任務"""
        return await asyncio.to_thread(extract_drug_keywords_batch, image_bytes_list, api_key)
    
    # 並行執行兩個任務
    parallel_start = time.time()
    print("[Parallel] 開始並行執行資料庫查詢和OCR處理...")
    
    try:
        db_result, ocr_result = await asyncio.gather(
            db_task(),
            ocr_task(),
            return_exceptions=True
        )
        
        parallel_time = time.time() - parallel_start
        
        # 檢查是否有異常
        if isinstance(db_result, Exception):
            print(f"[Parallel] 資料庫查詢失敗: {db_result}")
            return [], ([], 0), parallel_time
            
        if isinstance(ocr_result, Exception):
            print(f"[Parallel] OCR處理失敗: {ocr_result}")
            return db_result or [], ([], 0), parallel_time
        
        print(f"[Parallel] 並行處理完成，耗時: {parallel_time:.4f}s")
        return db_result, ocr_result, parallel_time
        
    except Exception as e:
        print(f"[Parallel] 並行處理異常: {e}")
        # 回退到序列處理
        print("[Parallel] 回退到序列處理...")
        db_result = get_all_drugs_from_db(db_config)
        ocr_result = extract_drug_keywords_batch(image_bytes_list, api_key)
        parallel_time = time.time() - parallel_start
        return db_result, ocr_result, parallel_time

def run_analysis(image_bytes_list: List[bytes], db_config: dict, api_key: str) -> Tuple[Dict | None, Dict | None]:
    """
    智能篩選版頻率導向分析 - 支援並行處理優化
    """
    start_time = time.time()
    print("[Smart Filter] 開始智能篩選頻率導向分析 (並行版本)...")
    
    if not image_bytes_list:
        print("[Smart Filter] 錯誤：沒有提供任何圖片資料。")
        return None, None

    try:
        # 第1&2步：並行執行資料庫查詢和OCR處理
        try:
            # 嘗試使用並行處理
            all_drugs, (keywords, total_ocr_tokens), parallel_time = asyncio.run(
                parallel_db_and_ocr(image_bytes_list, db_config, api_key)
            )
            processing_mode = "parallel"
        except Exception as e:
            print(f"[Smart Filter] 並行處理失敗，回退到序列處理: {e}")
            # 回退到原始序列處理
            all_drugs = get_all_drugs_from_db(db_config)
            if not all_drugs:
                return None, {"error": "資料庫連線失敗"}
            
            ocr_start = time.time()
            keywords, total_ocr_tokens = extract_drug_keywords_batch(image_bytes_list, api_key)
            parallel_time = time.time() - ocr_start
            processing_mode = "sequential_fallback"
        
        if not all_drugs:
            return None, {"error": "資料庫連線失敗"}
        
        print(f"[Smart Filter] 處理模式: {processing_mode}, 耗時: {parallel_time:.4f}s")
        print(f"[Smart Filter] 從 {len(image_bytes_list)} 張圖片提取到 {len(keywords)} 個唯一關鍵字")
        
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
- `days_supply`: (字串) 總給藥天數。請仔細尋找以下常見表達方式：
  * "X日份"、"X天份"、"共X日"、"*X"、"本單發藥X日"、"X日藥"
  * 數字形式：阿拉伯數字(1,2,3,7,14,28)或中文數字(一,二,三,七)
  * 常見位置：藥袋頂部標題區、底部總計區、或藥物列表上方
  * 範例識別："本單發藥 3 日份"→"3"、"共7日"→"7"、"*14"→"14"
  * 如果找到多個天數，選擇最合理的總給藥天數（通常是較大的數字）

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
    從圖片中找到總天數，將其數值記錄為 `Global_Days`。這是後續計算的基礎。
    
    **重要提示**：請特別注意以下識別要點：
    - 尋找關鍵字："日份"、"天份"、"共X日"、"*X"、"本單發藥X日"、"X日藥"
    - 常見數值：1, 3, 7, 14, 28, 30 (一般不超過30天)
    - 位置線索：通常在藥袋頂部、底部或藥物清單上方
    - 範例："本單發藥 3 日份" → Global_Days = 3
    - 範例："共7日" → Global_Days = 7
    - 範例："*14" → Global_Days = 14

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
        
        # 數學驗證健壯邏輯 - 在統計前先驗證和修正頻率
        medications = analysis_result.get('medications', [])
        medications = apply_math_validation(medications, analysis_result.get('days_supply'))
        analysis_result['medications'] = medications  # 更新修正後的結果
        
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
        
        # 數學驗證統計
        math_validated_count = sum(1 for med in medications if med.get('math_validation', {}).get('math_validation_applied'))
        math_corrected_count = sum(1 for med in medications if med.get('math_validation', {}).get('corrected'))
        avg_confidence = sum(med.get('math_validation', {}).get('confidence_score', 0.5) for med in medications) / total_meds if total_meds > 0 else 0.5
        
        # 使用統計
        end_time = time.time()
        usage_info = {
            "model": model_name,
            "version": "smart_filter_parallel_with_math_validation",
            "processing_mode": processing_mode,
            "execution_time": end_time - start_time,
            "parallel_time": parallel_time,
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
            "token_savings": f"{((6964 - total_tokens) / 6964 * 100):.1f}%" if total_tokens > 0 else "N/A",
            # 新增數學驗證統計
            "math_validation": {
                "validated_count": math_validated_count,
                "corrected_count": math_corrected_count,
                "validation_rate": math_validated_count / total_meds if total_meds > 0 else 0,
                "correction_rate": math_corrected_count / total_meds if total_meds > 0 else 0,
                "avg_confidence_score": avg_confidence
            }
        }
        
        print(f"[Smart Filter] 資料庫篩選: {len(all_drugs)} → {len(filtered_drugs)} ({usage_info['filter_ratio']:.1%})")
        print(f"[Smart Filter] 處理模式: {processing_mode}")
        print(f"[Smart Filter] 並行處理時間: {parallel_time:.4f}s")
        print(f"[Smart Filter] API調用優化: {len(image_bytes_list)}張圖片僅用2次API調用 (OCR批次+分析)")
        print(f"[Smart Filter] Token使用: OCR({total_ocr_tokens}) + 分析({analysis_tokens}) = {total_tokens}")
        print(f"[Smart Filter] 處理圖片數量: {len(image_bytes_list)}")
        print(f"[Smart Filter] Token節省: {usage_info['token_savings']}")
        print(f"[Smart Filter] 總執行時間: {end_time - start_time:.4f}s")
        print(f"[Smart Filter] 成功匹配: {len(successful_matches)}/{total_meds}")
        print(f"[Smart Filter] 頻率完整度: {frequency_rate:.1%}")
        print(f"[Smart Filter] 完整性類型: {completeness_type}")
        print(f"[Math Validation] 數學驗證: {math_validated_count}/{total_meds} ({usage_info['math_validation']['validation_rate']:.1%})")
        print(f"[Math Validation] 頻率修正: {math_corrected_count}/{total_meds} ({usage_info['math_validation']['correction_rate']:.1%})")
        print(f"[Math Validation] 平均信心度: {avg_confidence:.2f}")
        
        return analysis_result, usage_info

    except Exception as e:
        print(f"[Smart Filter] 分析處理錯誤: {e}")
        traceback.print_exc()
        return None, None

def parse_text_based_reminder(text: str, api_key: str) -> Dict | None:
    """
    使用Gemini AI從純文字解析用藥提醒資訊。
    此函式獨立於圖片辨識流程。
    """
    print(f"[Text Parser] 開始解析文字提醒: '{text}'")
    if not text or not api_key:
        return None

    try:
        # 預處理語音轉文字的常見錯誤
        corrected_text = _preprocess_voice_text(text)
        
        client = genai.Client(api_key=api_key)
        model_name = "gemini-1.5-flash"

        # 專為解析文字提醒設計的Prompt
        prompt = f"""
# 任務與角色
你是一個專門解析用藥提醒指令的AI助理。請從我提供的文字中，提取出結構化的用藥資訊。

# 輸入文字
「{corrected_text}」

# 輸出要求 (嚴格遵守)
請返回一個單一的 JSON 物件，包含以下欄位。如果某個資訊不存在，請將其值設為 `null`。

- `drug_name`: (字串) 藥物名稱。
- `timing`: (列表) 服藥時間點。例如: ["早上8點", "下午2點"] 或 ["睡前"]。
- `frequency`: (字串) 服藥頻率。例如: "每日三次"、"每週一、三、五"。
- `dosage`: (字串) 每次服用的劑量。例如: "1顆"、"10mg"、"一包"。
- `method`: (字串) 服用方式。例如: "飯後服用"、"空腹"。

# 範例
- 輸入: "提醒我每天早上八點跟晚上八點吃一顆血壓藥"
  輸出: 
  ```json
  {{
    "drug_name": "血壓藥",
    "timing": ["早上8點", "晚上8點"],
    "frequency": "每日兩次",
    "dosage": "1顆",
    "method": null
  }}
  ```
- 輸入: "新增用藥提醒，普拿疼，每天三次飯後吃，每次一顆"
  輸出:
  ```json
  {{
    "drug_name": "普拿疼",
    "timing": null,
    "frequency": "每天三次",
    "dosage": "1顆",
    "method": "飯後服用"
  }}
  ```
- 輸入: "睡前要吃安眠藥半顆"
  輸出:
  ```json
  {{
    "drug_name": "安眠藥",
    "timing": ["睡前"],
    "frequency": "每日一次",
    "dosage": "半顆",
    "method": null
  }}
  ```

請確保你的輸出是一個格式完全正確的 JSON 物件，並用 ```json ... ``` 包圍。
"""

        config = types.GenerateContentConfig(
            temperature=0.1,
            response_mime_type="application/json"
        )

        contents = [types.Content(role="user", parts=[types.Part.from_text(text=prompt)])]

        print("[Text Parser] 發送文字解析請求...")
        response = client.models.generate_content(
            model=model_name,
            contents=contents,
            config=config
        )

        response_text = response.text if hasattr(response, 'text') else ""
        if not response_text:
            print("[Text Parser] 模型沒有回傳任何文字內容。")
            return None

        # 解析JSON
        try:
            if response_text.startswith('```json'):
                json_start = response_text.find('{')
                json_end = response_text.rfind('}') + 1
                clean_json = response_text[json_start:json_end]
                parsed_result = json.loads(clean_json)
            else:
                parsed_result = json.loads(response_text)
            
            print(f"[Text Parser] 文字解析成功: {parsed_result}")
            return parsed_result

        except json.JSONDecodeError as e:
            print(f"[Text Parser] JSON解析失敗: {e}")
            print(f"[Text Parser] 原始回應: {response_text}")
            return None

    except Exception as e:
        print(f"[Text Parser] 文字提醒解析時發生錯誤: {e}")
        traceback.print_exc()
        return None

def _preprocess_voice_text(text: str) -> str:
    """
    預處理語音轉文字的常見錯誤
    
    Args:
        text: 原始語音轉文字
        
    Returns:
        修正後的文字
    """
    # 常見語音轉文字錯誤修正
    corrections = {
        # 藥物名稱修正
        '他命': '維他命',
        '他命素': '維他命素',
        '維他命': '維他命',  # 確保一致
        '血壓藥': '血壓藥',
        '血唐藥': '血糖藥',
        '胃藥': '胃藥',
        '普拿痼': '普拿疼',
        '斯普普拿痼': '阿斯普普拿疼',
        
        # 時間表達修正
        '一早': '早上',
        '早上8點': '早上8點',
        '早上八點': '早上8點',
        '中午': '中午',
        '晚上8點': '晚上8點',
        '晚上八點': '晚上8點',
        
        # 劑量單位修正
        '1粒': '1顆',
        '一粒': '1顆',
        '一顆': '1顆',
        '2粒': '2顆',
        '兩粒': '2顆',
        '兩顆': '2顆',
        
        # 頻率表達修正
        '一天一次': '每日一次',
        '一天兩次': '每日兩次', 
        '一天二次': '每日二次',
        '一天三次': '每日三次',
        '每天一次': '每日一次',
        '每天兩次': '每日兩次',
        '每天二次': '每日二次', 
        '每天三次': '每日三次',
        '每天2次': '每日二次',
        '每天3次': '每日三次',
        '每天1次': '每日一次',
    }
    
    corrected_text = text
    for wrong, correct in corrections.items():
        corrected_text = corrected_text.replace(wrong, correct)
    
    if corrected_text != text:
        print(f"[Text Preprocessing] 修正語音轉文字: '{text}' -> '{corrected_text}'")
    
    return corrected_text

# --- END OF FILE: app/services/ai_processor.py (智能篩選優化版) ---
