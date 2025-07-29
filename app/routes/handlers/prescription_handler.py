# --- 基於原有架構的 app/routes/handlers/prescription_handler.py ---

from flask import current_app
from linebot.models import TextSendMessage, ImageMessage, FlexSendMessage, PostbackEvent
from urllib.parse import parse_qs, unquote
import time
import traceback
import base64
from app import line_bot_api

from app.services.user_service import UserService
from app.services import prescription_service
from app.utils.flex import prescription as flex_prescription, general as flex_general
from app.utils.flex.prescription import create_prescription_model_choice
from app.utils.db import DB

def start_loading_animation(user_id, seconds=10):
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
            print(f"✅ 已為用戶 {user_id} 啟動藥單分析載入動畫")
        else:
            print(f"⚠️ 藥單分析載入動畫啟動失敗: {response.status_code}")
    except Exception as e:
        print(f"❌ 藥單分析載入動畫啟動異常: {e}")

def _reply_message(reply_token, message):
    """統一的回覆訊息處理"""
    try:
        if isinstance(message, list):
            line_bot_api.reply_message(reply_token, message)
        else:
            line_bot_api.reply_message(reply_token, message)
    except Exception as e:
        current_app.logger.error(f"回覆訊息失敗: {e}")

# 新增：處理模型選擇的函數
def handle_prescription_model_select(event, data):
    """處理藥單分析模型選擇"""
    try:
        user_id = event.source.user_id
        
        # 解析選擇的模型
        model_type = data.get('model', [None])[0]
        if not model_type or model_type not in ['smart_filter', 'api_ocr', 'fastapi_ocr']:
            _reply_message(event.reply_token, TextSendMessage(text="無效的模型選擇，請重新開始。"))
            return
        
        # 儲存選擇的模型到用戶狀態（UserService 會自動確保用戶存在）
        user_state = UserService.get_user_complex_state(user_id) or {}
        user_state['selected_model'] = model_type
        user_state['stage'] = 'model_selected'
        result = UserService.set_user_complex_state(user_id, user_state)
        
        if not result:
            current_app.logger.error(f"無法設置用戶狀態: {user_id}")
            _reply_message(event.reply_token, TextSendMessage(text="系統初始化失敗，請稍後再試。"))
            return
        
        # 繼續原有的成員選擇流程
        if model_type == 'smart_filter':
            model_name = "智能分析模式"
        elif model_type == 'api_ocr':
            model_name = "快速識別模式A (Flask)"
        elif model_type == 'fastapi_ocr':
            model_name = "快速識別模式B (FastAPI)"
        else:
            model_name = "未知模式"
        
        # 獲取成員列表並顯示成員選擇
        members = UserService.get_user_members(user_id)
        reply_message = flex_prescription.create_patient_selection_message(members, 'scan')
        _reply_message(event.reply_token, reply_message)
        
        current_app.logger.info(f"用戶 {user_id} 選擇了模型: {model_name} ({model_type})")
        
    except Exception as e:
        current_app.logger.error(f"處理模型選擇錯誤: {e}")
        _reply_message(event.reply_token, TextSendMessage(text="模型選擇時發生錯誤，請稍後再試。"))

# 修改：原有的處理函數，添加模型選擇邏輯
def handle(event):
    """處理 prescription 相關事件"""
    try:
        user_id = event.source.user_id
        
        if isinstance(event, PostbackEvent):
            data_str = event.postback.data
            data = parse_qs(unquote(data_str))
            action = data.get('action', [None])[0]
            
            # 新增：處理模型選擇
            if action == 'prescription_model_select':
                handle_prescription_model_select(event, data)
                return
            
            # 修改：開始掃描流程改為顯示模型選擇
            if action == 'initiate_scan_process':
                user_id = event.source.user_id
                
                UserService.clear_user_complex_state(user_id)
                
                # 顯示模型選擇卡片
                flex_message = create_prescription_model_choice()
                _reply_message(event.reply_token, FlexSendMessage(alt_text="請選擇分析模型", contents=flex_message))
                
                current_app.logger.info(f"用戶 {user_id} 開始藥單掃描流程 - 模型選擇階段")
                return
            
            # 處理成員選擇
            if action == 'select_patient_for_scan':
                member_name = data.get('member', [None])[0]
                if member_name:
                    # 保留現有狀態，特別是 selected_model
                    state = UserService.get_user_complex_state(user_id) or {}
                    state["state_info"] = {"state": "AWAITING_IMAGE"}
                    state["last_task"] = state.get("last_task", {})
                    state["last_task"]["member"] = member_name
                    result = UserService.set_user_complex_state(user_id, state)
                    
                    if not result:
                        current_app.logger.error(f"無法設置用戶狀態: {user_id}")
                        _reply_message(event.reply_token, TextSendMessage(text="系統初始化失敗，請稍後再試。"))
                        return
                    
                    # 生成拍照選項
                    from linebot.models import QuickReply, QuickReplyButton, CameraAction, URIAction
                    import time
                    task_id = f"task_{int(time.time())}"
                    
                    # 更新狀態包含 task_id
                    state["last_task"]["task_id"] = task_id
                    UserService.set_user_complex_state(user_id, state)
                    
                    # 修正 LIFF URL 格式 - 確保參數正確傳遞
                    liff_url = f"https://liff.line.me/{current_app.config['LIFF_ID_CAMERA']}?taskId={task_id}"
                    current_app.logger.info(f"生成的 LIFF URL: {liff_url}")
                    
                    quick_reply = QuickReply(items=[
                        QuickReplyButton(action=CameraAction(label="📸 開啟相機拍照")),
                        QuickReplyButton(action=URIAction(label="📤 上傳圖片", uri=liff_url))
                    ])
                    
                    _reply_message(event.reply_token, TextSendMessage(
                        text=f"為「{member_name}」掃描藥單\n\n📋 上傳藥單照片須知：\n• 放平藥單，避免摺疊或皺褶\n• 完整入鏡，確保四個角都在畫面內\n• 避免反光，注意燈光\n\n請選擇拍照方式：",
                        quick_reply=quick_reply
                    ))
                return
            
            # 處理其他 action
            if action == 'start_camera':
                # 重新拍照功能
                state = UserService.get_user_complex_state(user_id)
                member_name = state.get("last_task", {}).get("member", "")
                
                if member_name:
                    import time
                    task_id = f"task_{int(time.time())}"
                    
                    state["state_info"] = {"state": "AWAITING_IMAGE"}
                    state["last_task"]["task_id"] = task_id
                    UserService.set_user_complex_state(user_id, state)
                    
                    from linebot.models import QuickReply, QuickReplyButton, CameraAction, URIAction
                    liff_url = f"https://liff.line.me/{current_app.config['LIFF_ID_CAMERA']}?taskId={task_id}"
                    current_app.logger.info(f"重新拍照 - 生成的 LIFF URL: {liff_url}")
                    
                    quick_reply = QuickReply(items=[
                        QuickReplyButton(action=CameraAction(label="📸 開啟相機拍照")),
                        QuickReplyButton(action=URIAction(label="📤 上傳圖片", uri=liff_url))
                    ])
                    
                    _reply_message(event.reply_token, TextSendMessage(
                        text=f"為「{member_name}」重新掃描藥單\n\n請選擇拍照方式：",
                        quick_reply=quick_reply
                    ))
                else:
                    _reply_message(event.reply_token, TextSendMessage(text="找不到成員資訊，請重新開始。"))
                return
            
            # 處理確認儲存
            if action == 'confirm_save_final':
                try:
                    status, mm_id, is_update = prescription_service.PrescriptionService.save_prescription_from_state(user_id)
                    if status == "SUCCESS":
                        action_text = "更新" if is_update else "新增"
                        
                        from linebot.models import QuickReply, QuickReplyButton, URIAction, MessageAction
                        liff_reminder_url = f"https://liff.line.me/{current_app.config['LIFF_ID_PRESCRIPTION_REMINDER']}?mm_id={mm_id}"
                        
                        quick_reply = QuickReply(items=[
                            QuickReplyButton(action=URIAction(label="🔔 設定用藥提醒", uri=liff_reminder_url)),
                            QuickReplyButton(action=MessageAction(label="⏭️ 跳過，結束流程", text="跳過提醒設定")),
                            QuickReplyButton(action=MessageAction(label="📂 查看藥歷", text="查詢個人藥歷"))
                        ])
                        
                        _reply_message(event.reply_token, TextSendMessage(
                            text=f"✅ 藥歷{action_text}成功！\n\n💡 接下來您可以為這些藥物設定用藥提醒，確保按時服藥：",
                            quick_reply=quick_reply
                        ))
                    else:
                        _reply_message(event.reply_token, TextSendMessage(text="❌ 儲存失敗，請稍後再試。"))
                except Exception as e:
                    current_app.logger.error(f"儲存藥歷時發生錯誤: {e}")
                    _reply_message(event.reply_token, TextSendMessage(text=f"儲存失敗：{str(e)}"))
                return
            
            # 處理查詢藥歷
            if action == 'list_records':
                member_name = data.get('member', [None])[0]
                if member_name:
                    from app.utils.db import DB
                    records = DB.get_records_by_member(user_id, member_name)
                    reply_message = flex_prescription.create_records_carousel(member_name, records)
                    _reply_message(event.reply_token, reply_message)
                else:
                    _reply_message(event.reply_token, TextSendMessage(text="❌ 找不到成員資訊。"))
                return
            
            # 處理查詢流程初始化
            if action == 'initiate_query_process':
                UserService.clear_user_complex_state(user_id)
                members = UserService.get_user_members(user_id)
                reply_message = flex_prescription.create_patient_selection_message(members, 'query')
                _reply_message(event.reply_token, reply_message)
                return
            
            # 處理記錄管理相關操作
            if action in ['view_record_details', 'confirm_delete_record', 'execute_delete_record', 'load_record_as_draft']:
                handle_record_management(event, user_id, action, data)
                return
            
            # 處理取消任務
            if action == 'cancel_task':
                UserService.clear_user_complex_state(user_id)
                _reply_message(event.reply_token, TextSendMessage(text="操作已取消。"))
                return
        
        elif hasattr(event, 'message') and hasattr(event.message, 'text') and event.message.text is not None:
            # 處理文字訊息
            handle_text_message(event, user_id)
            return
        elif hasattr(event, 'message') and hasattr(event.message, 'type') and event.message.type == 'image':
            # 處理圖片訊息
            handle_image_message(event.reply_token, event.message.id, user_id)
            return
            
        current_app.logger.warning(f"未處理的 prescription event: {event}")
        
    except Exception as e:
        current_app.logger.error(f"prescription_handler 處理錯誤: {e}")
        traceback.print_exc()
        _reply_message(event.reply_token, TextSendMessage(text="系統發生錯誤，請稍後再試。"))

# 保持所有原有的函數...
def handle_text_message(event, user_id):
    """處理文字訊息"""
    # 安全地處理可能為 None 的 text
    if not hasattr(event.message, 'text') or event.message.text is None:
        current_app.logger.warning(f"收到空的文字訊息 - 用戶: {user_id}")
        return
    
    # 確保 text 不為 None 才執行 strip()
    message_text = event.message.text
    if message_text is None:
        current_app.logger.warning(f"收到 None 文字訊息 - 用戶: {user_id}")
        return
    
    text = message_text.strip()
    reply_token = event.reply_token
    
    print(f"🔍 [prescription_handler] handle_text_message 被調用")
    print(f"🔍 [prescription_handler] 文字內容: '{text}'")
    print(f"🔍 [prescription_handler] 用戶ID: {user_id}")
    
    # 處理「藥單辨識」按鈕點擊
    if text == "藥單辨識":
        print(f"✅ [prescription_handler] 處理藥單辨識請求")
        UserService.clear_user_complex_state(user_id)
        
        # 顯示模型選擇卡片
        flex_message = create_prescription_model_choice()
        _reply_message(reply_token, FlexSendMessage(alt_text="請選擇分析模型", contents=flex_message))
        
        current_app.logger.info(f"用戶 {user_id} 開始藥單掃描流程 - 模型選擇階段")
        return
    
    # 🧪 FastAPI測試指令
    if text == "測試fastapi":
        print(f"🧪 [prescription_handler] 處理FastAPI測試指令")
        UserService.clear_user_complex_state(user_id)
        
        # 直接設定為FastAPI模式並進入成員選擇
        user_state = UserService.get_user_complex_state(user_id) or {}
        user_state['selected_model'] = 'fastapi_ocr'
        user_state['stage'] = 'model_selected'
        UserService.set_user_complex_state(user_id, user_state)
        
        # 獲取成員列表並顯示成員選擇
        members = UserService.get_user_members(user_id)
        reply_message = flex_prescription.create_patient_selection_message(members, 'scan')
        _reply_message(reply_token, reply_message)
        
        print(f"🧪 [prescription_handler] FastAPI測試模式已啟動 - 用戶: {user_id}")
        _reply_message(reply_token, TextSendMessage(text="🧪 FastAPI測試模式已啟動！\n請選擇成員後上傳藥單照片進行測試。"))
        return
    
    # 處理成員選擇後的文字訊息 - 已移除重複處理邏輯
    # 這部分邏輯已經在 postback 處理中完成，避免重複
    
    # 處理預覽手動修改結果的訊息
    if text == "📝 預覽手動修改結果":
        print(f"🔍 [prescription_handler] 處理預覽手動修改結果 - 用戶: {user_id}")
        try:
            # 獲取用戶狀態
            state = UserService.get_user_complex_state(user_id)
            task_info = state.get("last_task", {})
            results = task_info.get("results")
            
            print(f"📊 [prescription_handler] 用戶狀態 - 有結果: {bool(results)}")
            if results:
                print(f"📋 [prescription_handler] 結果內容預覽: {str(results)[:200]}...")
            
            if results:
                # 準備分析結果訊息
                freq_map_list = DB.get_frequency_map()
                frequency_map = {item['frequency_code']: item for item in freq_map_list}
                liff_edit_id = current_app.config['LIFF_ID_EDIT']
                liff_reminder_id = current_app.config['LIFF_ID_PRESCRIPTION_REMINDER']
                member_name = task_info.get('member', '')
                
                messages = flex_prescription.generate_analysis_report_messages(
                    results, frequency_map, liff_edit_id, liff_reminder_id, member_name, 
                    is_direct_view=False, source="manual_edit"
                )
                
                # 發送預覽結果
                _reply_message(reply_token, messages)
                print(f"✅ [prescription_handler] 手動修改預覽完成並已發送結果給用戶 {user_id}")
                
            else:
                _reply_message(reply_token, TextSendMessage(text="❌ 找不到修改後的資料，請重新操作。"))
                print(f"❌ [prescription_handler] 找不到修改後的資料 - 用戶: {user_id}")
                
        except Exception as e:
            print(f"❌ [prescription_handler] 處理手動修改預覽失敗: {e}")
            traceback.print_exc()
            _reply_message(reply_token, TextSendMessage(text="❌ 預覽過程中發生錯誤，請稍後再試。"))
        
        return
    
    # 處理 LIFF 上傳成功訊息
    if "照片上傳成功" in text and "正在分析中" in text:
        # 啟動載入動畫
        start_loading_animation(user_id, seconds=60)
        
        try:
            # 獲取任務ID
            state = UserService.get_user_complex_state(user_id)
            task_id = state.get("last_task", {}).get("task_id")
            
            if not task_id:
                _reply_message(reply_token, TextSendMessage(text="❌ 找不到任務ID，請重新操作。"))
                return
            
            # 執行同步分析
            prescription_service.PrescriptionService.trigger_analysis(user_id, task_id)
            
            # 獲取分析結果
            updated_state = UserService.get_user_complex_state(user_id)
            results = updated_state.get('last_task', {}).get('results')
            
            if results:
                # 準備分析結果訊息
                freq_map_list = DB.get_frequency_map()
                frequency_map = {item['frequency_code']: item for item in freq_map_list}
                liff_edit_id = current_app.config['LIFF_ID_EDIT']
                liff_reminder_id = current_app.config['LIFF_ID_PRESCRIPTION_REMINDER']
                member_name = state.get('last_task', {}).get('member', '')
                
                messages = flex_prescription.generate_analysis_report_messages(
                    results, frequency_map, liff_edit_id, liff_reminder_id, member_name
                )
                
                _reply_message(reply_token, messages)
            else:
                _reply_message(reply_token, TextSendMessage(text="❌ 分析過程中發生錯誤，請重新上傳照片。"))
                
        except Exception as e:
            current_app.logger.error(f"藥單分析處理失敗: {e}")
            _reply_message(reply_token, TextSendMessage(text="❌ 分析過程中發生錯誤，請重新上傳照片。"))
        return
    
    # 處理跳過提醒設定的訊息
    if text == "跳過提醒設定":
        _reply_message(reply_token, TextSendMessage(text="✅ 藥歷儲存完成！\n\n您可以隨時到「用藥提醒管理」為藥物設定提醒。"))
        return
    
    # 如果沒有匹配到任何處理邏輯，記錄日誌
    print(f"⚠️ [prescription_handler] 未匹配到處理邏輯的文字訊息: '{text}'")

def handle_image_message(reply_token, message_id, user_id):
    """處理直接上傳的圖片訊息，進行藥單辨識"""
    try:
        print(f"📷 [藥單辨識] 開始處理圖片訊息 - 用戶: {user_id}")
        
        # 檢查用戶狀態
        state = UserService.get_user_complex_state(user_id)
        if not state or state.get("state_info", {}).get("state") != "AWAITING_IMAGE":
            print(f"⚠️ [藥單辨識] 用戶狀態不正確 - 用戶: {user_id}")
            _reply_message(reply_token, TextSendMessage(text="請先選擇成員後再上傳圖片。"))
            return
        
        member_name = state.get("last_task", {}).get("member")
        if not member_name:
            print(f"❌ [藥單辨識] 找不到成員資訊 - 用戶: {user_id}")
            _reply_message(reply_token, TextSendMessage(text="找不到成員資訊，請重新開始。"))
            return
        
        print(f"📋 [藥單辨識] 為成員 '{member_name}' 處理圖片")
        
        # 啟動載入動畫
        start_loading_animation(user_id, seconds=60)
        
        # 下載圖片
        message_content = line_bot_api.get_message_content(message_id)
        image_bytes = message_content.content
        
        print(f"📥 [藥單辨識] 圖片下載完成，大小: {len(image_bytes)} bytes")
        
        # 將圖片轉為base64並儲存到狀態
        image_b64 = base64.b64encode(image_bytes).decode('utf-8')
        
        # 生成任務ID
        import time
        task_id = f"task_{int(time.time())}"
        
        # 更新用戶狀態
        state["last_task"]["image_bytes_list"] = [image_b64]
        state["last_task"]["task_id"] = task_id
        state["state_info"]["state"] = "PROCESSING"
        UserService.set_user_complex_state(user_id, state)
        
        print(f"💾 [藥單辨識] 狀態已更新，任務ID: {task_id}")
        
        # 執行同步分析
        try:
            prescription_service.PrescriptionService.trigger_analysis(user_id, task_id)
            print(f"🔄 [藥單辨識] 分析完成")
            
            # 獲取分析結果
            updated_state = UserService.get_user_complex_state(user_id)
            results = updated_state.get('last_task', {}).get('results')
            
            if results:
                print(f"✅ [藥單辨識] 分析成功，準備發送結果")
                
                # 準備分析結果訊息
                freq_map_list = DB.get_frequency_map()
                frequency_map = {item['frequency_code']: item for item in freq_map_list}
                liff_edit_id = current_app.config['LIFF_ID_EDIT']
                liff_reminder_id = current_app.config['LIFF_ID_PRESCRIPTION_REMINDER']
                
                messages = flex_prescription.generate_analysis_report_messages(
                    results, frequency_map, liff_edit_id, liff_reminder_id, member_name
                )
                
                _reply_message(reply_token, messages)
                print(f"📤 [藥單辨識] 結果已發送給用戶")
                
            else:
                print(f"❌ [藥單辨識] 分析失敗，沒有結果")
                _reply_message(reply_token, TextSendMessage(text="❌ 分析過程中發生錯誤，請重新上傳照片。"))
                
        except Exception as analysis_error:
            print(f"❌ [藥單辨識] 分析過程錯誤: {analysis_error}")
            traceback.print_exc()
            _reply_message(reply_token, TextSendMessage(text="❌ 分析過程中發生錯誤，請重新上傳照片。"))
        
    except Exception as e:
        current_app.logger.error(f"處理圖片訊息時發生錯誤: {e}")
        traceback.print_exc()
        _reply_message(reply_token, TextSendMessage(text="❌ 處理圖片時發生錯誤，請稍後再試。"))

def handle_record_management(event, user_id, action, data):
    """處理藥歷記錄管理相關操作"""
    reply_token = event.reply_token
    
    if action == 'view_record_details':
        mm_id = int(data.get('mm_id', [0])[0])
        record = prescription_service.PrescriptionService.get_prescription_details(mm_id)
        if record:
            # 使用現有的分析報告生成函數來顯示藥歷詳情
            freq_map_list = DB.get_frequency_map()
            frequency_map = {item['frequency_code']: item for item in freq_map_list}
            liff_edit_id = current_app.config['LIFF_ID_EDIT']
            liff_reminder_id = current_app.config['LIFF_ID_PRESCRIPTION_REMINDER']
            member_name = record.get('member', '')
            
            messages = flex_prescription.generate_analysis_report_messages(
                record, frequency_map, liff_edit_id, liff_reminder_id, member_name, 
                is_direct_view=True, source=""
            )
            _reply_message(reply_token, messages)
        else:
            _reply_message(reply_token, TextSendMessage(text="❌ 找不到該筆記錄。"))
    
    elif action == 'confirm_delete_record':
        mm_id = data.get('mm_id', [None])[0]
        from app.utils.flex.general import create_simple_confirmation
        _reply_message(reply_token, create_simple_confirmation(
            alt_text="確認刪除記錄", title="⚠️ 確定要刪除？", text="您確定要刪除這筆藥歷記錄嗎？此操作無法復原！",
            confirm_label="是，刪除", confirm_data=f"action=execute_delete_record&mm_id={mm_id}"
        ))
    
    elif action == 'execute_delete_record':
        mm_id = int(data.get('mm_id', [0])[0])
        if DB.delete_record_by_mm_id(user_id, mm_id):
            _reply_message(reply_token, TextSendMessage(text="✅ 記錄已成功刪除。"))
        else:
            _reply_message(reply_token, TextSendMessage(text="❌ 刪除失敗，找不到記錄或權限不足。"))
    
    elif action == 'load_record_as_draft':
        mm_id = int(data.get('mm_id', [0])[0])
        try:
            # 載入歷史記錄為草稿
            success = prescription_service.PrescriptionService.load_record_as_draft(user_id, mm_id)
            if success:
                # 載入成功後開啟編輯頁面
                liff_url = f"https://liff.line.me/{current_app.config['LIFF_ID_EDIT']}"
                from app.utils.flex.general import create_liff_button
                _reply_message(reply_token, create_liff_button("✏️ 開始編輯", liff_url, "歷史記錄已載入為草稿"))
            else:
                _reply_message(reply_token, TextSendMessage(text="❌ 載入記錄失敗，找不到記錄或權限不足。"))
        except Exception as e:
            current_app.logger.error(f"載入記錄為草稿時發生錯誤: {e}")
            _reply_message(reply_token, TextSendMessage(text="❌ 載入記錄時發生錯誤，請稍後再試。"))