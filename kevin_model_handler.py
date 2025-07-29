import os
import uuid
import base64
import requests
from google.cloud import storage
from time import time

# --- 環境變數與設定 ---
GCS_BUCKET_NAME = os.environ.get("GCS_BUCKET_NAME")
GCS_PATH_PREFIX = 'predictions/kevin_model/'

# 設定 Google Cloud 認證
GOOGLE_APPLICATION_CREDENTIALS = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
if GOOGLE_APPLICATION_CREDENTIALS:
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = GOOGLE_APPLICATION_CREDENTIALS
# 這是 kevin_api.py 中定義的 API 端點
KEVIN_API_URL = "https://kevin-712800774423.us-central1.run.app/detect"

def _upload_to_gcs(image_bytes, suffix='annotated.jpg'):
    """
    將圖片(bytes)上傳到 Google Cloud Storage 並回傳公開網址。
    這是 kevin_api.py 中的輔助函式。
    如果上傳失敗，返回 None 但不影響主要功能。
    """
    if not GCS_BUCKET_NAME:
        print("    - [Kevin模型] GCS_BUCKET_NAME 環境變數未設定，跳過圖片上傳")
        return None
    
    try:
        storage_client = storage.Client()
        bucket = storage_client.bucket(GCS_BUCKET_NAME)
        filename = f"{GCS_PATH_PREFIX}{uuid.uuid4()}_{suffix}"
        blob = bucket.blob(filename)
        blob.upload_from_string(image_bytes, content_type='image/jpeg')
        public_url = f"https://storage.googleapis.com/{GCS_BUCKET_NAME}/{filename}"
        print(f"    - [Kevin模型] GCS 上傳成功：{public_url}")
        return public_url
    except Exception as e:
        print(f"    - [Kevin模型] GCS 上傳失敗 (這不會影響辨識功能): {e}")
        return None

def detect_pills(pil_image):
    """
    主要辨識函式，接收 PIL 圖片，呼叫 Kevin 的 API，並回傳標準化格式的結果。
    """
    start_time = time()
    print("    - [Kevin模型] 開始處理...")

    # 將 PIL Image 轉換回 bytes
    import io
    img_byte_arr = io.BytesIO()
    pil_image.save(img_byte_arr, format='JPEG')
    image_bytes = img_byte_arr.getvalue()

    try:
        # 步驟 1: 呼叫 kevin_api.py 中定義的 API
        files = {"file": ("image.jpg", image_bytes, "image/jpeg")}
        print(f"    - [Kevin模型] 呼叫 API: {KEVIN_API_URL}")
        api_resp = requests.post(KEVIN_API_URL, files=files, timeout=30)
        api_resp.raise_for_status()
        result = api_resp.json()
        print(f"    - [Kevin模型] API 回應成功")

        # 步驟 2: 解析 API 回應並標準化（適應新格式）
        if not result.get("success") or not result.get("data"):
            raise ValueError("API 回應格式不符或檢測失敗")

        data = result["data"]
        detections = data.get("detections", [])
        annotated_image_url = None

        # 處理標註後的圖片（新格式：data:image/jpeg;base64,xxx）
        annotated_image_base64 = data.get("annotated_image")
        if annotated_image_base64:
            # 新格式包含完整的 data URL，需要提取 base64 部分
            if annotated_image_base64.startswith("data:image/"):
                # 分割 "data:image/jpeg;base64," 和實際的 base64 資料
                if "," in annotated_image_base64:
                    annotated_image_base64 = annotated_image_base64.split(',')[1]
            
            try:
                img_bytes_anno = base64.b64decode(annotated_image_base64)
                annotated_image_url = _upload_to_gcs(img_bytes_anno)
                # 如果 GCS 上傳失敗，仍然繼續處理，只是沒有圖片 URL
                if not annotated_image_url:
                    print("    - [Kevin模型] GCS 上傳失敗，但繼續處理辨識結果")
            except Exception as decode_error:
                print(f"    - [Kevin模型] Base64 解碼失敗: {decode_error}")
                annotated_image_url = None

        elapsed_time = time() - start_time
        
        # 記錄新格式的額外資訊
        total_detections = data.get("total_detections", len(detections))
        image_info = data.get("image_info", {})
        
        print(f"    - [Kevin模型] 檢測完成：找到 {total_detections} 個藥丸")
        if image_info:
            print(f"    - [Kevin模型] 圖片資訊：{image_info.get('original_size', 'Unknown')} {image_info.get('mode', '')}")
        
        # 依照統一格式回傳結果
        return {
            'detections': detections,
            'elapsed_time': elapsed_time,
            'model_name': 'Transformer模型',
            'annotated_image_url': annotated_image_url,
            'detection_mode': 'single', # 標記為單一模型結果
            'success': True,
            # 新增的欄位
            'total_detections': total_detections,
            'image_info': image_info,
            'api_message': result.get("message", "")
        }

    except requests.exceptions.RequestException as e:
        print(f"!!!!!! [API 呼叫錯誤] Kevin模型 API 呼叫失敗: {e} !!!!!!")
        return {"success": False, "error": str(e)}
    except Exception as e:
        print(f"!!!!!! [嚴重錯誤] Kevin模型處理時發生錯誤: {e} !!!!!!")
        return {"success": False, "error": str(e)}