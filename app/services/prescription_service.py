# --- 請用此版本【完整覆蓋】您的 app/services/prescription_service.py ---

import base64
import traceback
from ..utils.db import DB
from .user_service import UserService
from . import ai_processor
from ..utils.helpers import convert_minguo_to_gregorian
from flask import current_app
# 移除不再需要的 line_bot_api 和 flex 導入
# from app import line_bot_api
# from ..utils.flex import prescription as flex_prescription

class PrescriptionService:
    """處理藥單分析與藥歷相關的業務邏輯"""

    @staticmethod
    def trigger_analysis(user_id: str, task_id: str):
        """
        觸發藥單深度分析，並將結果存回狀態。
        返回 True 表示成功，或拋出異常。
        """
        full_state = UserService.get_user_complex_state(user_id)
        last_task_info = full_state.get("last_task", {})

        if not last_task_info or last_task_info.get("task_id") != task_id:
            raise ValueError("找不到對應的分析任務，請重新操作。")
        
        image_b64_list = last_task_info.get("image_bytes_list", [])
        if not image_b64_list:
            raise ValueError("分析任務中缺少圖片資料，請重新操作。")
        
        try:
            image_bytes_list = [base64.b64decode(b64_str) for b64_str in image_b64_list]
            
            api_key = current_app.config['GEMINI_API_KEY']
            db_config = {
                'host': current_app.config['DB_HOST'], 'user': current_app.config['DB_USER'],
                'password': current_app.config['DB_PASSWORD'], 'database': current_app.config['DB_NAME'],
                'port': current_app.config['DB_PORT']
            }

            # 檢查用戶是否選擇了特定的模型
            user_state = UserService.get_user_complex_state(user_id) or {}
            selected_model = user_state.get('selected_model', 'smart_filter')
            
            print(f"[Prescription] 分析模型: {selected_model}")
            
            if selected_model == 'api_ocr':
                # 使用組員A的 OCR API (Flask - 異步)
                print(f"[Prescription] 使用快速識別模式 (Flask)")
                # 從狀態中獲取成員名稱
                member_name = last_task_info.get("member", "本人")
                
                if len(image_bytes_list) > 1:
                    print(f"[Prescription] OCR API 多圖處理：將處理 {len(image_bytes_list)} 張圖片")
                    analysis_result, usage_info = PrescriptionService.call_ocr_api_multiple(
                        image_bytes_list, 
                        user_id=user_id, 
                        member_name=member_name
                    )
                else:
                    analysis_result, usage_info = PrescriptionService.call_ocr_api(
                        image_bytes_list[0], 
                        user_id=user_id, 
                        member_name=member_name
                    )
            elif selected_model == 'fastapi_ocr':
                # 使用組員B的 FastAPI OCR (同步)
                print(f"[Prescription] 使用FastAPI快速識別模式")
                # 從狀態中獲取成員名稱
                member_name = last_task_info.get("member", "本人")
                
                if len(image_bytes_list) > 1:
                    print(f"[Prescription] FastAPI OCR 多圖處理：將處理 {len(image_bytes_list)} 張圖片")
                    analysis_result, usage_info = PrescriptionService.call_fastapi_ocr_multiple(
                        image_bytes_list, 
                        user_id=user_id, 
                        member_name=member_name
                    )
                else:
                    analysis_result, usage_info = PrescriptionService.call_fastapi_ocr(
                        image_bytes_list[0], 
                        user_id=user_id, 
                        member_name=member_name
                    )
            else:
                # 使用智能篩選版 AI 分析（預設）
                print(f"[Prescription] 使用智能分析模式")
                analysis_result, usage_info = ai_processor.run_analysis(
                    image_bytes_list, db_config, api_key
                )

            if not analysis_result or not isinstance(analysis_result, dict) or 'medications' not in analysis_result:
                error_detail = usage_info.get("error") if isinstance(usage_info, dict) else "未知AI錯誤"
                raise RuntimeError(f"AI 分析失敗或回傳格式錯誤: {error_detail}")

            last_task_info["results"] = analysis_result
            full_state["last_task"] = last_task_info
            UserService.set_user_complex_state(user_id, full_state)
            
            return True

        except Exception as e:
            print(f"分析任務發生嚴重錯誤: {e}")
            traceback.print_exc()
    
    @staticmethod
    def call_ocr_api_multiple(image_bytes_list, user_id=None, member_name=None):
        """調用組員的 OCR API 進行多圖快速識別"""
        print(f"[OCR API Multi] 開始處理 {len(image_bytes_list)} 張圖片")
        
        all_medications = []
        combined_result = {
            "clinic_name": None,
            "doctor_name": None, 
            "visit_date": None,
            "days_supply": None,
            "medications": []
        }
        
        total_execution_time = 0
        
        for i, image_bytes in enumerate(image_bytes_list):
            print(f"[OCR API Multi] 處理第 {i+1}/{len(image_bytes_list)} 張圖片")
            
            result, usage_info = PrescriptionService.call_ocr_api(
                image_bytes, user_id, member_name
            )
            
            if result and isinstance(result, dict):
                # 合併全域資訊（使用第一張圖片的資訊，或更新為非空值）
                if i == 0 or not combined_result["clinic_name"]:
                    combined_result["clinic_name"] = result.get("clinic_name")
                if i == 0 or not combined_result["doctor_name"]:
                    combined_result["doctor_name"] = result.get("doctor_name")
                if i == 0 or not combined_result["visit_date"]:
                    combined_result["visit_date"] = result.get("visit_date")
                if i == 0 or not combined_result["days_supply"]:
                    combined_result["days_supply"] = result.get("days_supply")
                
                # 合併藥物列表
                medications = result.get("medications", [])
                for med in medications:
                    med["source_image"] = i + 1  # 標記來源圖片
                    all_medications.append(med)
                
                # 累計執行時間
                if usage_info and "execution_time" in usage_info:
                    total_execution_time += usage_info["execution_time"]
            else:
                print(f"[OCR API Multi] 第 {i+1} 張圖片處理失敗")
        
        combined_result["medications"] = all_medications
        combined_result["successful_match_count"] = len([med for med in all_medications if med.get('matched_drug_id')])
        
        # 建立合併的使用統計
        combined_usage_info = {
            "model": "ocr_api_multiple",
            "version": "api_ocr_multi",
            "execution_time": total_execution_time,
            "images_processed": len(image_bytes_list),
            "total_medications": len(all_medications),
            "api_calls_used": len(image_bytes_list),
            "total_tokens": 0,
            "token_savings": "100%",
            "api_status": "success",
            "processing_mode": "sequential_multi_image"
        }
        
        print(f"[OCR API Multi] 完成處理，共識別 {len(all_medications)} 種藥物")
        return combined_result, combined_usage_info

    @staticmethod
    def call_ocr_api(image_bytes, user_id=None, member_name=None):
        """調用組員的 OCR API 進行快速識別"""
        import requests
        import json
        
        try:
            # 組員的 OCR API 端點（正確的路徑）
            api_url = "https://gpu-test-543976352117.us-central1.run.app/api/v1/analyze?photo="
            
            print(f"[OCR API] 開始調用 API: {api_url}")
            print(f"[OCR API] 用戶ID: {user_id}, 成員: {member_name}")
            
            # 準備請求資料（正確的欄位名稱和格式）
            files = {
                'photos': ('prescription.jpg', image_bytes, 'image/jpeg')
            }
            
            data = {
                'line_user_id': user_id or 'unknown',
                'member': member_name or '本人'
            }
            
            print(f"[OCR API] 發送資料: {data}")
            
            # 發送請求
            response = requests.post(
                api_url,
                files=files,
                data=data,
                timeout=60  # 增加到60秒超時
            )
            
            if response.status_code in [200, 202]:
                print(f"[OCR API] 任務提交成功 (狀態碼: {response.status_code})")
                
                if response.status_code == 200:
                    # 同步回應，直接處理結果
                    api_result = response.json()
                    print(f"[OCR API] 同步獲得結果")
                elif response.status_code == 202:
                    # 異步處理，需要輪詢結果
                    print(f"[OCR API] 異步處理，開始輪詢結果...")
                    print(f"[DEBUG] POST回應內容: {response.text}")
                    print(f"[DEBUG] POST回應headers: {dict(response.headers)}")
                    
                    # 等待一段時間再開始輪詢，給組員系統處理時間
                    import time
                    print(f"[DEBUG] 等待10秒讓組員系統處理...")
                    time.sleep(10)
                    
                    api_result = PrescriptionService.poll_ocr_result(user_id)
                    if not api_result:
                        return None, {"error": "輪詢結果超時或失敗"}
                
                # 轉換 API 結果為統一格式
                analysis_result = PrescriptionService.convert_api_result_to_standard_format(api_result)
                
                # 建立使用統計
                usage_info = {
                    "model": "ocr_api",
                    "version": "api_ocr",
                    "execution_time": response.elapsed.total_seconds(),
                    "api_response_time": response.elapsed.total_seconds(),
                    "total_tokens": 0,  # API 不消耗 TOKEN
                    "token_savings": "100%",  # API 不消耗 TOKEN
                    "api_status": "success",
                    "http_status": response.status_code
                }
                
                return analysis_result, usage_info
                
            else:
                print(f"[OCR API] API 調用失敗: {response.status_code}")
                print(f"[OCR API] 回應內容: {response.text}")
                return None, {"error": f"API 調用失敗: {response.status_code}"}
                
        except requests.exceptions.Timeout:
            print(f"[OCR API] API 調用超時")
            return None, {"error": "API 調用超時"}
        except Exception as e:
            print(f"[OCR API] API 調用錯誤: {e}")
            return None, {"error": f"API 調用錯誤: {str(e)}"}
    
    @staticmethod
    def poll_ocr_result(user_id, max_retries=20, polling_interval=10):
        """輪詢組員OCR API獲取異步處理結果"""
        import requests
        import time
        
        # 輪詢端點
        result_url = f"https://gpu-test-543976352117.us-central1.run.app/api/v1/result/{user_id}"
        
        print(f"[OCR API] 開始輪詢結果 - URL: {result_url}")
        print(f"[OCR API] 最大重試次數: {max_retries}, 間隔: {polling_interval}秒")
        print(f"[DEBUG] 輪詢用的user_id: '{user_id}'")
        print(f"[DEBUG] 輪詢用的user_id長度: {len(user_id) if user_id else 0}")
        
        for i in range(max_retries):
            try:
                print(f"[OCR API] 輪詢第 {i+1}/{max_retries} 次...")
                print(f"[DEBUG] 完整輪詢URL: {result_url}")
                
                response = requests.get(result_url, timeout=10)
                
                print(f"[DEBUG] 輪詢回應狀態: {response.status_code}")
                print(f"[DEBUG] 輪詢回應headers: {dict(response.headers)}")
                print(f"[DEBUG] 輪詢回應內容: {response.text}")
                
                if response.status_code == 200:
                    try:
                        result = response.json()
                        print(f"[DEBUG] 結果JSON結構: {list(result.keys()) if isinstance(result, dict) else type(result)}")
                        print(f"[OCR API] 結果預覽: {str(result)[:200]}...")
                        
                        # 檢查JSON中的status字段
                        if result.get("status") == "completed":
                            print(f"[OCR API] 輪詢成功獲得完成結果")
                            return result.get("data")  # 返回data部分
                        elif result.get("status") == "error":
                            print(f"[OCR API] 組員API處理失敗: {result.get('message', '未知錯誤')}")
                            return None
                        elif result.get("status") == "processing":
                            print(f"[OCR API] 任務仍在處理中，繼續等待...")
                        else:
                            print(f"[OCR API] 收到未知狀態: {result.get('status')}")
                            print(f"[DEBUG] 完整回應: {result}")
                        # 如果不是completed，繼續輪詢
                    except Exception as json_error:
                        print(f"[DEBUG] JSON解析錯誤: {json_error}")
                        print(f"[DEBUG] 原始回應: {response.text}")
                    
                elif response.status_code == 404:
                    print(f"[OCR API] 結果尚未準備好 (404)，繼續等待...")
                    
                elif response.status_code == 202:
                    print(f"[OCR API] 任務仍在處理中 (202)，繼續等待...")
                    
                else:
                    print(f"[OCR API] 輪詢收到意外狀態碼: {response.status_code}")
                    print(f"[OCR API] 回應內容: {response.text}")
                
                # 等待下次輪詢
                if i < max_retries - 1:  # 最後一次不需要等待
                    print(f"[OCR API] 等待 {polling_interval} 秒後重試...")
                    time.sleep(polling_interval)
                    
            except requests.exceptions.Timeout:
                print(f"[OCR API] 輪詢第 {i+1} 次超時")
                
            except Exception as e:
                print(f"[OCR API] 輪詢第 {i+1} 次發生錯誤: {e}")
                import traceback
                traceback.print_exc()
        
        print(f"[OCR API] 輪詢超時，已重試 {max_retries} 次")
        return None
    
    @staticmethod
    def call_fastapi_ocr_multiple(image_bytes_list, user_id=None, member_name=None):
        """調用組員B的 FastAPI OCR 進行多圖快速識別"""
        print(f"[FastAPI OCR Multi] 開始處理 {len(image_bytes_list)} 張圖片")
        
        all_medications = []
        combined_result = {
            "clinic_name": None,
            "doctor_name": None, 
            "visit_date": None,
            "days_supply": None,
            "medications": []
        }
        
        total_execution_time = 0
        
        for i, image_bytes in enumerate(image_bytes_list):
            print(f"[FastAPI OCR Multi] 處理第 {i+1}/{len(image_bytes_list)} 張圖片")
            
            result, usage_info = PrescriptionService.call_fastapi_ocr(
                image_bytes, user_id, member_name
            )
            
            if result and isinstance(result, dict):
                # 合併全域資訊（使用第一張圖片的資訊，或更新為非空值）
                if i == 0 or not combined_result["clinic_name"]:
                    combined_result["clinic_name"] = result.get("clinic_name")
                if i == 0 or not combined_result["doctor_name"]:
                    combined_result["doctor_name"] = result.get("doctor_name")
                if i == 0 or not combined_result["visit_date"]:
                    combined_result["visit_date"] = result.get("visit_date")
                if i == 0 or not combined_result["days_supply"]:
                    combined_result["days_supply"] = result.get("days_supply")
                
                # 合併藥物列表
                medications = result.get("medications", [])
                for med in medications:
                    med["source_image"] = i + 1  # 標記來源圖片
                    all_medications.append(med)
                
                # 累計執行時間
                if usage_info and "execution_time" in usage_info:
                    total_execution_time += usage_info["execution_time"]
            else:
                print(f"[FastAPI OCR Multi] 第 {i+1} 張圖片處理失敗")
        
        combined_result["medications"] = all_medications
        combined_result["successful_match_count"] = len([med for med in all_medications if med.get('matched_drug_id')])
        
        # 建立合併的使用統計
        combined_usage_info = {
            "model": "fastapi_ocr_multiple",
            "version": "fastapi_ocr_multi",
            "execution_time": total_execution_time,
            "images_processed": len(image_bytes_list),
            "total_medications": len(all_medications),
            "api_calls_used": len(image_bytes_list),
            "total_tokens": 0,
            "token_savings": "100%",
            "api_status": "success",
            "processing_mode": "sequential_multi_image"
        }
        
        print(f"[FastAPI OCR Multi] 完成處理，共識別 {len(all_medications)} 種藥物")
        return combined_result, combined_usage_info

    @staticmethod
    def call_fastapi_ocr(image_bytes, user_id=None, member_name=None):
        """調用組員B的 FastAPI OCR 進行快速識別（同步處理）"""
        import requests
        import json
        
        try:
            # 組員B的 FastAPI OCR 端點
            api_url = "https://ocr-23010935669.asia-east1.run.app/api/v1/analyze"
            
            print(f"[FastAPI OCR] 開始調用 API: {api_url}")
            print(f"[FastAPI OCR] 用戶ID: {user_id}, 成員: {member_name}")
            
            # 詳細調試用戶ID
            print(f"[DEBUG] FastAPI發送的user_id: {user_id}")
            print(f"[DEBUG] FastAPI user_id長度: {len(user_id) if user_id else 0}")
            print(f"[DEBUG] FastAPI user_id類型: {type(user_id)}")
            print(f"[DEBUG] FastAPI圖片大小: {len(image_bytes)} bytes")
            
            # 準備請求資料（與Flask版本相同的格式）
            files = {
                'photos': ('prescription.jpg', image_bytes, 'image/jpeg')
            }
            
            data = {
                'line_user_id': user_id or 'unknown',
                'member': member_name or '本人'
            }
            
            print(f"[FastAPI OCR] 發送資料: {data}")
            print(f"[DEBUG] FastAPI完整請求資料: files={list(files.keys())}, data={data}")
            
            # 發送請求（FastAPI是同步處理，直接返回結果）
            response = requests.post(
                api_url,
                files=files,
                data=data,
                timeout=60  # FastAPI同步處理，可能需要更長時間
            )
            
            print(f"[FastAPI OCR] 收到回應 (狀態碼: {response.status_code})")
            print(f"[DEBUG] FastAPI回應headers: {dict(response.headers)}")
            print(f"[DEBUG] FastAPI回應內容: {response.text}")
            
            if response.status_code == 200:
                api_result = response.json()
                print(f"[FastAPI OCR] API 調用成功")
                
                # FastAPI直接返回完整結果，檢查status
                if api_result.get("status") == "completed":
                    print(f"[FastAPI OCR] 同步獲得完成結果")
                    
                    # 預處理FastAPI數據，確保數值型欄位為字符串
                    fastapi_data = api_result.get("data", api_result)
                    if "medications" in fastapi_data:
                        for med in fastapi_data["medications"]:
                            # 將數值型欄位轉換為字符串，避免strip()錯誤
                            if "dose_quantity" in med and isinstance(med["dose_quantity"], (int, float)):
                                med["dose_quantity"] = str(med["dose_quantity"])
                    
                    # 轉換 API 結果為統一格式
                    analysis_result = PrescriptionService.convert_api_result_to_standard_format(fastapi_data)
                    
                    # 建立使用統計
                    usage_info = {
                        "model": "fastapi_ocr",
                        "version": "fastapi_ocr",
                        "execution_time": response.elapsed.total_seconds(),
                        "api_response_time": response.elapsed.total_seconds(),
                        "total_tokens": 0,  # API 不消耗 TOKEN
                        "token_savings": "100%",  # API 不消耗 TOKEN
                        "api_status": "success",
                        "http_status": response.status_code,
                        "processing_mode": "synchronous"
                    }
                    
                    return analysis_result, usage_info
                else:
                    print(f"[FastAPI OCR] API 返回非完成狀態: {api_result.get('status')}")
                    return None, {"error": f"FastAPI 返回狀態: {api_result.get('status')}"}
                    
            else:
                print(f"[FastAPI OCR] API 調用失敗: {response.status_code}")
                print(f"[FastAPI OCR] 回應內容: {response.text}")
                return None, {"error": f"FastAPI 調用失敗: {response.status_code}"}
                
        except requests.exceptions.Timeout:
            print(f"[FastAPI OCR] API 調用超時")
            return None, {"error": "FastAPI 調用超時"}
        except Exception as e:
            print(f"[FastAPI OCR] API 調用錯誤: {e}")
            return None, {"error": f"FastAPI 調用錯誤: {str(e)}"}
    
    @staticmethod
    def convert_api_result_to_standard_format(api_result):
        """將 API 結果轉換為標準格式"""
        try:
            # 根據組員 API 的實際回傳格式進行轉換
            # 這裡需要根據實際 API 回傳格式調整
            
            medications = api_result.get('medications', [])
            
            # 確保每個藥物都有必要的欄位
            for med in medications:
                if not med.get('matched_drug_id'):
                    med['matched_drug_id'] = None
                if not med.get('main_use'):
                    med['main_use'] = "API模式暫不提供"
                if not med.get('side_effects'):
                    med['side_effects'] = "API模式暫不提供"
                if not med.get('frequency_count_code'):
                    med['frequency_count_code'] = None
                if not med.get('frequency_timing_code'):
                    med['frequency_timing_code'] = None
            
            # 添加統計資訊
            total_meds = len(medications)
            successful_matches = len([med for med in medications if med.get('matched_drug_id')])
            
            standard_result = {
                "clinic_name": api_result.get('clinic_name'),
                "doctor_name": api_result.get('doctor_name'),
                "visit_date": api_result.get('visit_date'),
                "days_supply": api_result.get('days_supply'),
                "medications": medications,
                "successful_match_count": successful_matches,
                "frequency_stats": {
                    "total": total_meds,
                    "with_frequency": total_meds,  # 假設 API 都有頻率資訊
                    "frequency_rate": 1.0 if total_meds > 0 else 0
                },
                "completeness_type": "api_prescription",
                "is_successful": total_meds > 0,
                "user_message": f"快速識別完成，識別{total_meds}種藥物。"
            }
            
            return standard_result
            
        except Exception as e:
            print(f"[OCR API] 結果轉換錯誤: {e}")
            return {
                "clinic_name": None,
                "doctor_name": None,
                "visit_date": None,
                "days_supply": None,
                "medications": [],
                "successful_match_count": 0,
                "frequency_stats": {
                    "total": 0,
                    "with_frequency": 0,
                    "frequency_rate": 0
                },
                "completeness_type": "api_error",
                "is_successful": False,
                "user_message": "API 結果解析失敗"
            }
            raise

    @staticmethod
    def save_prescription_from_state(user_id: str):
        """
        從使用者狀態中讀取分析結果並存入資料庫。
        """
        full_state = UserService.get_user_complex_state(user_id)
        task_to_save = full_state.get("last_task")

        if not task_to_save or 'results' not in task_to_save:
            raise ValueError("找不到可儲存的結果。")
        
        analysis_data = task_to_save['results']
        
        visit_date_str = analysis_data.get('visit_date')
        visit_date_gregorian = convert_minguo_to_gregorian(visit_date_str)
        if not visit_date_gregorian:
            # 【修正】這裡要確保狀態被正確設定，以便 handle_postback 能夠處理
            state_to_save = UserService.get_user_complex_state(user_id)
            state_to_save['state_info'] = {'state': 'AWAITING_VISIT_DATE'}
            UserService.set_user_complex_state(user_id, state_to_save)
            return "AWAITING_VISIT_DATE", None, None

        analysis_data['visit_date'] = visit_date_gregorian
        
        try:
            mm_id, is_update = DB.save_or_update_prescription(analysis_data, task_to_save, user_id)
            UserService.clear_user_complex_state(user_id)
            return "SUCCESS", mm_id, is_update
        except Exception as e:
            print(f"儲存藥歷時服務層發生錯誤: {e}")
            traceback.print_exc()
            raise

    @staticmethod
    def get_prescription_details(mm_id: int):
        """
        獲取單筆藥歷的完整資訊。
        """
        record = DB.get_prescription_by_mm_id(mm_id)
        if not record:
            return None
        
        all_drugs_info = {d['drug_id']: d for d in DB.get_all_drug_info()}
        
        for med in record.get("medications", []):
            if not isinstance(med, dict): continue
            matched_id = med.get('matched_drug_id')
            drug_info = all_drugs_info.get(matched_id)
            
            if drug_info:
                if not med.get('main_use'): med['main_use'] = drug_info.get('main_use')
                if not med.get('side_effects'): med['side_effects'] = drug_info.get('side_effects')
        
        return record

    @staticmethod
    def load_record_as_draft(user_id: str, mm_id: int):
        """
        將歷史藥歷記錄載入為草稿，供用戶編輯。
        """
        try:
            # 獲取歷史記錄
            record = DB.get_prescription_by_mm_id(mm_id)
            if not record:
                return False
            
            # 檢查權限 - 確保記錄屬於該用戶
            if record.get('recorder_id') != user_id:
                return False
            
            # 準備草稿資料
            medications_for_draft = []
            for med in record.get('medications', []):
                medications_for_draft.append({
                    "matched_drug_id": med.get('matched_drug_id'),
                    "drug_name_zh": med.get('drug_name_zh'),
                    "drug_name_en": med.get('drug_name_en'),
                    "dose_quantity": med.get('dose_quantity'),
                    "frequency_count_code": med.get('frequency_count_code'),
                    "frequency_timing_code": med.get('frequency_timing_code'),
                    "frequency_text": med.get('frequency_text'),
                    "main_use": med.get('main_use'),
                    "side_effects": med.get('side_effects')
                })
            
            # 準備完整的草稿結果
            draft_results = {
                "clinic_name": record.get('clinic_name'),
                "doctor_name": record.get('doctor_name'),
                "visit_date": record.get('visit_date').strftime('%Y-%m-%d') if record.get('visit_date') else None,
                "days_supply": record.get('days_supply'),
                "medications": medications_for_draft,
                "successful_match_count": len(medications_for_draft)
            }
            
            # 建立新的狀態，包含編輯標記
            import time
            initial_state = {
                "last_task": {
                    "task_id": f"edit_{user_id[:8]}_{int(time.time())}",
                    "line_user_id": user_id,
                    "member": record.get('member'),
                    "status": "completed",
                    "mm_id_to_update": mm_id,  # 標記為更新模式
                    "results": draft_results,
                    "source": "load_from_history"
                }
            }
            
            # 儲存狀態
            UserService.set_user_complex_state(user_id, initial_state)
            
            current_app.logger.info(f"歷史記錄已載入為草稿 - 用戶: {user_id}, mm_id: {mm_id}")
            return True
            
        except Exception as e:
            current_app.logger.error(f"載入歷史記錄為草稿時發生錯誤: {e}")
            return False