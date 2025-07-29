# --- 請用此最終版本【完整覆蓋】您的 app/routes/line_webhook.py ---

from flask import Blueprint, request, abort, current_app
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, PostbackEvent, FollowEvent, TextMessage, ImageMessage, AudioMessage, TextSendMessage, FlexSendMessage, QuickReply, QuickReplyButton, MessageAction
import traceback

from app import handler, line_bot_api
from .handlers import prescription_handler
# reminder_handler 將在需要時動態導入以避免作用域問題
try:
    from .handlers import family_handler
except ImportError:
    family_handler = None

try:
    from .handlers import pill_handler
except ImportError:
    pill_handler = None

from app.services.user_service import UserService
from app.services.voice_service import VoiceService
from app.services.ai_processor import parse_text_based_reminder
from app.utils.flex import general as flex_general
from app.utils.flex import health as flex_health
from app.utils.flex import prescription as flex_prescription
from app.utils.flex import settings as flex_settings

webhook_bp = Blueprint('webhook', __name__)

@webhook_bp.route("/callback", methods=['POST'])
def callback():
    signature = request.headers['X-Line-Signature']
    body = request.get_data(as_text=True)
    current_app.logger.info("Request body: " + body)
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)
    except Exception as e:
        current_app.logger.error(f"處理 Webhook 時發生錯誤: {e}")
        traceback.print_exc()
        abort(500)
    return 'OK'


@handler.add(MessageEvent, message=(TextMessage, ImageMessage, AudioMessage))
def handle_message_dispatcher(event):
    """處理文字訊息的分發器"""
    user_id = event.source.user_id
    
    # 確保用戶存在
    UserService.get_or_create_user(user_id)
    
    complex_state = UserService.get_user_complex_state(user_id)
    simple_state = UserService.get_user_simple_state(user_id)
    
    # 【核心修正】将图片讯息的处理，也纳入状态判断流程
    if isinstance(event.message, ImageMessage):
        # 优先检查是否为药丸辨识状态
        try:
            from .handlers import pill_handler as ph
            if ph and ph.handle_image_message(event):
                return
        except ImportError:
            pass
        
        # 然后检查是否为药单辨识状态
        if complex_state.get("state_info", {}).get("state") == "AWAITING_IMAGE":
            prescription_handler.handle(event)
        else:
            # 否则，回覆预设讯息
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text="感謝您傳送的圖片，但目前我不知道如何處理它。如果您要辨識藥單，請先點擊「藥單辨識」；如果要辨識藥丸，請點擊「藥品辨識」喔！"))
        return

    # 【新增】處理語音訊息
    if isinstance(event.message, AudioMessage):
        # 檢查是否啟用語音功能
        if not current_app.config.get('SPEECH_TO_TEXT_ENABLED', True):
            line_bot_api.reply_message(event.reply_token, 
                TextSendMessage(text="抱歉，語音輸入功能目前暫不可用"))
            return
        
        # 發送處理中訊息
        line_bot_api.reply_message(event.reply_token, 
            TextSendMessage(text="🎙️ 正在處理您的語音訊息，請稍候..."))
        
        # 下載並處理語音檔案
        audio_content = VoiceService.download_audio_content(event.message.id, line_bot_api)
        if not audio_content:
            line_bot_api.push_message(user_id,
                TextSendMessage(text="❌ 無法下載語音檔案，請重新錄製"))
            return
        
        # 處理語音輸入
        success, result, extra_data = VoiceService.process_voice_input(user_id, audio_content, line_bot_api)
        
        if success:
            # 語音轉文字成功
            current_app.logger.info(f"語音轉文字成功: {result}")
            
            # 檢查是否為語音新增提醒對象指令（最高優先級）
            add_member_data = VoiceService.parse_add_member_command(result)
            if add_member_data['is_add_member_command']:
                member_name = add_member_data['member_name']
                command_type = add_member_data['command_type']
                
                current_app.logger.info(f"語音新增提醒對象指令: 名稱={member_name}, 類型={command_type}")
                
                # 處理新增成員指令
                success, message, extra_info = VoiceService.process_add_member_command(user_id, member_name, command_type)
                line_bot_api.push_message(user_id, TextSendMessage(text=message))
                return
            
            # 先檢查是否為用藥提醒指令（優先於選單指令）
            api_key = current_app.config.get('GEMINI_API_KEY')
            parsed_data = parse_text_based_reminder(result, api_key)

            if parsed_data and parsed_data.get('drug_name'):
                # 如果成功解析出藥物名稱，則視為用藥提醒指令
                current_app.logger.info(f"語音識別為用藥提醒指令: {parsed_data}")
                
                # 檢查是否指定了特定成員
                target_member = _extract_member_from_voice(user_id, result)
                
                if target_member:
                    # 已指定成員，直接創建提醒
                    parsed_data['target_member'] = target_member
                    
                    # 直接使用 ReminderService.create_reminder_from_voice 創建提醒
                    from app.services.reminder_service import ReminderService
                    
                    # 提取語音解析的資料
                    drug_name = parsed_data.get('drug_name', '')
                    dose_quantity = parsed_data.get('dose_quantity', '')
                    frequency_name = parsed_data.get('frequency_name', '')
                    time_slots = parsed_data.get('time_slots', [])  # 這是關鍵！
                    notes = parsed_data.get('notes')
                    
                    current_app.logger.info(f"語音提醒資料: drug_name={drug_name}, time_slots={time_slots}, frequency={frequency_name}, dose={dose_quantity}")
                    
                    # 創建提醒
                    reminder_id = ReminderService.create_reminder_from_voice(
                        user_id=user_id,
                        drug_name=drug_name,
                        timings=time_slots,  # 直接傳遞時間列表
                        frequency=frequency_name,  # 保持原始頻率
                        dosage=dose_quantity,      # 保持原始劑量
                        method=notes or "語音輸入",  # 改為更簡潔的備註
                        target_member=target_member  # 傳入正確的目標成員
                    )
                    
                    if reminder_id:
                        # 創建成功，直接顯示提醒卡片
                        current_app.logger.info(f"語音提醒處理成功，ID: {reminder_id}")
                        
                        # 發送立即的成功訊息（可能是新增或更新）
                        immediate_success_msg = f"✅ 語音用藥提醒設定成功！\n\n👤 對象：{target_member}\n💊 藥物：{drug_name}\n⏰ 時間：{', '.join(time_slots) if time_slots else '預設時間'}\n📅 頻率：{frequency_name}\n\n🔄 正在為您顯示提醒列表..."
                        line_bot_api.push_message(user_id, TextSendMessage(text=immediate_success_msg))
                        
                        # 稍微延遲後顯示卡片，確保資料庫事務完成
                        import time
                        time.sleep(0.5)
                        
                        try:
                            from app.utils.flex import reminder as flex_reminder
                            
                            # 確保用戶資料存在
                            UserService.get_or_create_user(user_id)
                            members = UserService.get_user_members(user_id)
                            target_member_data = next((m for m in members if m['member'] == target_member), None)
                            
                            current_app.logger.info(f"🔍 找到目標成員: {target_member_data}")
                            
                            if target_member_data:
                                # 獲取目標成員的所有提醒（包括剛建立/更新的）
                                reminders = ReminderService.get_reminders_for_member(user_id, target_member)
                                current_app.logger.info(f"🔍 獲取到 {len(reminders) if reminders else 0} 筆提醒")
                                
                                # 確保 LIFF ID 存在
                                liff_id = current_app.config.get('LIFF_ID_MANUAL_REMINDER')
                                current_app.logger.info(f"🔍 LIFF ID: {liff_id}")
                                
                                # 強制創建提醒卡片
                                if liff_id and reminders:
                                    try:
                                        flex_message = flex_reminder.create_reminder_list_carousel(target_member_data, reminders, liff_id)
                                        line_bot_api.push_message(user_id, flex_message)
                                        current_app.logger.info(f"✅ 語音設定提醒成功 - 已顯示「{target_member}」的提醒卡片")
                                        return  # 成功顯示卡片，直接返回
                                    except Exception as carousel_error:
                                        current_app.logger.error(f"❌ 創建提醒卡片失敗: {carousel_error}")
                                        import traceback
                                        current_app.logger.error(f"詳細錯誤: {traceback.format_exc()}")
                                elif not reminders:
                                    current_app.logger.warning(f"⚠️ 無法取得用戶 {user_id} 成員「{target_member}」的提醒列表")
                                else:
                                    current_app.logger.error("❌ 無法取得 LIFF_ID_MANUAL_REMINDER 配置")
                            else:
                                current_app.logger.error(f"❌ 無法找到目標成員「{target_member}」資料")
                                
                        except Exception as e:
                            current_app.logger.error(f"❌ 處理語音提醒結果失敗: {e}")
                            import traceback
                            current_app.logger.error(f"錯誤詳情: {traceback.format_exc()}")
                            
                        # 如果執行到這裡，表示卡片顯示失敗，發送說明訊息
                        fallback_msg = f"💡 您為「{target_member}」設定的「{drug_name}」提醒已完成。\n\n請點選「用藥提醒」→「新增/查詢提醒」→「{target_member}」查看所有提醒。"
                        line_bot_api.push_message(user_id, TextSendMessage(text=fallback_msg))
                    else:
                        current_app.logger.error("❌ 語音提醒設定失敗，reminder_id 為 None")
                        line_bot_api.push_message(user_id, TextSendMessage(text="❌ 設定提醒失敗，請稍後再試或使用選單功能手動新增。"))
                else:
                    # 未指定成員，顯示成員選擇選單
                    _show_member_selection_for_voice_reminder(user_id, parsed_data, line_bot_api)
                return
            
            # 檢查是否為選單指令
            if extra_data.get('is_menu_command', False):
                menu_command = extra_data.get('menu_command')
                postback_data = extra_data.get('postback_data')
                
                current_app.logger.info(f"處理語音選單指令: {menu_command}, postback_data: {postback_data}")
                
                # 處理不同類型的語音選單指令
                if menu_command == 'query_self_reminders':
                    # 查詢本人提醒 - 語音指令處理
                    try:
                        from app.utils.flex import reminder as flex_reminder
                        from app.services.reminder_service import ReminderService
                        
                        current_app.logger.info(f"開始處理語音查詢本人提醒 - 用戶: {user_id}")
                        
                        # 確保用戶存在
                        UserService.get_or_create_user(user_id)
                        
                        # 獲取用戶的所有成員
                        members = UserService.get_user_members(user_id)
                        current_app.logger.info(f"用戶成員列表: {[m['member'] for m in members]}")
                        
                        # 找到本人的成員資料
                        target_member = next((m for m in members if m['member'] == '本人'), None)
                        
                        if target_member:
                            current_app.logger.info(f"找到本人成員: {target_member}")
                            
                            # 獲取本人的提醒列表
                            reminders = ReminderService.get_reminders_for_member(user_id, "本人")
                            current_app.logger.info(f"本人提醒數量: {len(reminders) if reminders else 0}")
                            
                            if reminders and len(reminders) > 0:
                                # 有提醒記錄，顯示卡片
                                liff_id = current_app.config.get('LIFF_ID_MANUAL_REMINDER')
                                if liff_id:
                                    flex_message = flex_reminder.create_reminder_list_carousel(target_member, reminders, liff_id)
                                    line_bot_api.push_message(user_id, flex_message)
                                    current_app.logger.info("語音觸發查詢本人提醒成功 - 顯示提醒卡片")
                                else:
                                    # LIFF ID 未配置，發送文字訊息
                                    reminder_text = f"📋 您目前有 {len(reminders)} 筆用藥提醒：\n\n"
                                    for i, reminder in enumerate(reminders[:5], 1):  # 最多顯示5筆
                                        reminder_text += f"{i}. {reminder.get('drug_name', '未知藥物')} - {reminder.get('frequency_name', '未設定頻率')}\n"
                                    if len(reminders) > 5:
                                        reminder_text += f"\n...還有 {len(reminders) - 5} 筆提醒"
                                    line_bot_api.push_message(user_id, TextSendMessage(text=reminder_text))
                                    current_app.logger.info("語音觸發查詢本人提醒成功 - 顯示文字列表")
                            else:
                                # 沒有提醒記錄
                                line_bot_api.push_message(user_id, TextSendMessage(
                                    text="📋 您目前沒有設定任何用藥提醒。\n\n💡 您可以說「新增提醒」或使用「用藥提醒」選單來建立提醒。"
                                ))
                                current_app.logger.info("語音觸發查詢本人提醒成功 - 無提醒記錄")
                        else:
                            # 找不到本人成員，自動創建
                            current_app.logger.warning(f"找不到用戶 {user_id} 的本人資料，嘗試創建")
                            from app.utils.db import DB
                            DB.add_member(user_id, "本人")
                            line_bot_api.push_message(user_id, TextSendMessage(
                                text="📋 已為您初始化個人資料。\n\n目前沒有用藥提醒，您可以說「新增提醒」來建立第一筆提醒。"
                            ))
                            current_app.logger.info("語音觸發查詢本人提醒 - 已創建本人成員")
                        
                    except Exception as e:
                        current_app.logger.error(f"語音查詢本人提醒失敗: {e}")
                        import traceback
                        current_app.logger.error(f"錯誤詳情: {traceback.format_exc()}")
                        line_bot_api.push_message(user_id, TextSendMessage(text="❌ 查詢提醒時發生錯誤，請稍後再試"))
                    
                    return
                
                elif menu_command == 'query_family_reminders':
                    # 查詢家人提醒 - 顯示成員管理選單
                    try:
                        from app.utils.flex import reminder as flex_reminder
                        from app.services.reminder_service import ReminderService
                        
                        # 獲取成員摘要資訊
                        members_summary = ReminderService.get_members_with_reminder_summary(user_id)
                        liff_id = current_app.config['LIFF_ID_MANUAL_REMINDER']
                        
                        flex_message = flex_reminder.create_member_management_carousel(members_summary, liff_id)
                        line_bot_api.push_message(user_id, flex_message)
                        current_app.logger.info("語音觸發查詢家人提醒成功 - 顯示成員管理")
                        
                    except Exception as e:
                        current_app.logger.error(f"語音查詢家人提醒失敗: {e}")
                        line_bot_api.push_message(user_id, TextSendMessage(text="❌ 查詢家人提醒時發生錯誤，請稍後再試"))
                    
                    return
                
                elif menu_command in ['prescription_scan', 'pill_scan', 'reminder', 'family', 'history', 'health']:
                    # 其他選單指令 - 使用原有的 postback 處理邏輯
                    from urllib.parse import parse_qs
                    
                    class MockEvent:
                        def __init__(self, user_id, postback_data):
                            self.source = type('obj', (object,), {'user_id': user_id})
                            self.reply_token = None
                            self.postback = type('obj', (object,), {'data': postback_data})
                    
                    mock_event = MockEvent(user_id, postback_data)
                    handle_voice_menu_postback(mock_event, menu_command)
                    return
                
                else:
                    current_app.logger.warning(f"未處理的語音選單指令: {menu_command}")
                    return

            # 如果不是選單指令，提供通用幫助
            help_message = f"🎙️ 收到您的語音：「{result}」\n\n我不太確定如何處理這個指令。您可以試試說：\n- 「新增提醒，血壓藥，每天早上8點吃一顆」\n- 「藥單辨識」\n- 「主選單」"
            line_bot_api.push_message(user_id, TextSendMessage(text=help_message))
        else:
            # 語音轉文字失敗
            line_bot_api.push_message(user_id, TextSendMessage(text=f"❌ {result}"))
        return

    if not isinstance(event.message, TextMessage):
        return
        
    # 提取文字訊息內容
    text = event.message.text.strip()

    # 安全的 reminder_handler 調用函數
    def safe_reminder_handler_call():
        # 在函數內部導入，避免作用域問題
        try:
            from .handlers import reminder_handler as rh
            return rh.handle(event)
        except ImportError:
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text="❌ 用藥提醒功能暫時無法使用"))

    # 第一優先級：全局指令
    high_priority_keywords = {
        # 主選單相關
        "選單": lambda: line_bot_api.reply_message(event.reply_token, flex_general.create_main_menu()),
        "主選單": lambda: line_bot_api.reply_message(event.reply_token, flex_general.create_main_menu()),
        "menu": lambda: line_bot_api.reply_message(event.reply_token, flex_general.create_main_menu()),
        
        # 圖文選單按鈕 - 新的簡化名稱
        "藥單辨識": lambda: prescription_handler.handle(event),
        "藥品辨識": lambda: handle_pill_recognition(event),
        "用藥提醒": lambda: safe_reminder_handler_call(),
        "健康紀錄": lambda: line_bot_api.reply_message(
            event.reply_token, 
            flex_health.generate_health_log_menu(f"https://liff.line.me/{current_app.config['LIFF_ID_HEALTH_FORM']}")
        ),
        "設定": lambda: handle_settings_menu(event),
        
        # 舊版本兼容性
        "用藥提醒管理": lambda: safe_reminder_handler_call(),
        "家人綁定與管理": lambda: family_handler.handle(event),
        "藥丸辨識": lambda: handle_pill_recognition(event),
        "此功能正在開發中，敬請期待！": lambda: handle_pill_recognition(event),
        "健康記錄管理": lambda: handle_health_record_menu(event),
        
        # 其他功能
        "登入": lambda: handle_login_request(event),
        "會員登入": lambda: handle_login_request(event),
        "我的藥歷": lambda: handle_query_prescription(event),
        "查詢個人藥歷": lambda: handle_query_prescription(event),
        "新增/查詢提醒": lambda: safe_reminder_handler_call(),
        "管理提醒對象": lambda: safe_reminder_handler_call(),
        "刪除提醒對象": lambda: safe_reminder_handler_call(),
        "管理成員": lambda: safe_reminder_handler_call(),
        "新增提醒對象": lambda: safe_reminder_handler_call(),
    }

    if text in high_priority_keywords:
        UserService.delete_user_simple_state(user_id)
        UserService.clear_user_complex_state(user_id)
        high_priority_keywords[text]()
        return
    
    # 檢查是否為成員選擇（在清除狀態之前）
    user_state = UserService.get_user_simple_state(user_id)
    if user_state == "selecting_member_for_reminder":
        print(f"🔍 [line_webhook] 檢測到成員選擇: {text}")
        safe_reminder_handler_call()
        return

    # 第二優先級：特定流程的文字觸發
    # 檢查藥單相關訊息
    print(f"🔍 Webhook 檢查藥單訊息 - 文字: '{text}'")
    print(f"🔍 包含'照片上傳成功': {'照片上傳成功' in text}")
    print(f"🔍 包含'任務ID:': {'任務ID:' in text}")
    
    if ("照片上傳成功" in text and "任務ID:" in text) or text == '📝 預覽手動修改結果' or text == '測試fastapi':
        print(f"✅ 訊息匹配成功，轉發到 prescription_handler")
        prescription_handler.handle(event)
        return
    
    # 新增：處理 LIFF 上傳的訊息（沒有任務ID的情況）
    if "照片上傳成功" in text and "正在分析中" in text:
        print(f"✅ LIFF 上傳訊息匹配成功，轉發到 prescription_handler")
        prescription_handler.handle(event)
        return
    
    # 新增：處理成員選擇後的文字訊息
    if "為「" in text and "」掃描藥單" in text:
        print(f"✅ 檢測到成員選擇訊息，轉發到 prescription_handler")
        prescription_handler.handle(event)
        return
    # 處理直接發送的「掃描新藥單」文字訊息
    if text == '掃描新藥單' or text == '🤖 掃描新藥單':
        print(f"✅ 檢測到掃描新藥單文字訊息，直接執行掃描流程")
        # 直接執行掃描流程的邏輯 (與 action=start_scan_flow 相同)
        reply_message = flex_prescription.create_management_menu(
            title="📋 藥單辨識管理",
            primary_action_label="📲 掃描新藥單",
            primary_action_data="action=initiate_scan_process"
        )
        line_bot_api.reply_message(event.reply_token, reply_message)
        return
    
    if text.startswith("綁定"):
        family_handler.handle(event)
        return

    # 第三優先級：狀態相關處理
    if simple_state or complex_state.get("state_info", {}).get("state"):
        if text == '取消':
            UserService.delete_user_simple_state(user_id)
            UserService.clear_user_complex_state(user_id)
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text="操作已取消。"))
        # 處理語音提醒成員選擇
        elif complex_state.get("state_info", {}).get("state") == "awaiting_member_selection_for_voice_reminder":
            _handle_voice_reminder_member_selection(event, user_id, text)
        elif state_belongs_to_family(simple_state):
            family_handler.handle(event)
        elif state_belongs_to_reminder(simple_state):
            safe_reminder_handler_call()
        return

    # 第四優先級：如果沒有狀態，檢查是否為成員名稱
    members = [m['member'] for m in UserService.get_user_members(user_id)]
    if text in members:
        safe_reminder_handler_call()
        return

def _handle_voice_reminder_member_selection(event, user_id: str, text: str):
    """
    處理語音提醒的成員選擇回應
    
    Args:
        event: LINE 事件
        user_id: 用戶ID
        text: 用戶輸入的文字
    """
    try:
        # 獲取儲存的提醒資料
        complex_state = UserService.get_user_complex_state(user_id)
        parsed_data = complex_state.get('state_info', {}).get('parsed_reminder_data')
        
        if not parsed_data:
            line_bot_api.reply_message(event.reply_token, TextSendMessage(
                text="找不到提醒資料，請重新開始語音輸入。"
            ))
            UserService.clear_user_complex_state(user_id)
            return
        
        # 從用戶回應中提取成員名稱
        import re
        member_match = re.search(r'為(.+)設定提醒', text)
        target_member = None
        
        if member_match:
            target_member = member_match.group(1).strip()
        else:
            # 如果沒有匹配到模式，直接檢查是否為成員名稱
            members = UserService.get_user_members(user_id)
            member_names = [m['member'] for m in members]
            if text in member_names:
                target_member = text
        
        if not target_member:
            line_bot_api.reply_message(event.reply_token, TextSendMessage(
                text="請選擇有效的成員，或輸入「取消」結束設定。"
            ))
            return
        
        # 檢查成員是否存在
        members = UserService.get_user_members(user_id)
        if not any(m['member'] == target_member for m in members):
            line_bot_api.reply_message(event.reply_token, TextSendMessage(
                text=f"找不到成員「{target_member}」，請選擇有效的成員。"
            ))
            return
        
        # 清除狀態並創建提醒
        UserService.clear_user_complex_state(user_id)
        
        # 將成員資訊添加到解析資料中
        parsed_data['target_member'] = target_member
        
        # 調用提醒處理器
        from app.routes.handlers import reminder_handler
        reminder_handler.handle_voice_reminder(user_id, parsed_data)
        
        current_app.logger.info(f"語音提醒成員選擇完成: {user_id} -> {target_member}")
        
    except Exception as e:
        current_app.logger.error(f"處理語音提醒成員選擇錯誤: {e}")
        line_bot_api.reply_message(event.reply_token, TextSendMessage(
            text="設定提醒時發生錯誤，請稍後再試。"
        ))
        UserService.clear_user_complex_state(user_id)

def _extract_member_from_voice(user_id: str, voice_text: str) -> str:
    """
    從語音文字中提取成員名稱
    
    Args:
        user_id: 用戶ID
        voice_text: 語音轉文字內容
        
    Returns:
        成員名稱，如果未找到則返回None
    """
    try:
        # 獲取用戶的所有成員
        members = UserService.get_user_members(user_id)
        member_names = [m['member'] for m in members]
        
        # 檢查語音中是否包含成員名稱
        voice_lower = voice_text.lower()
        
        # 直接匹配成員名稱
        for member_name in member_names:
            if member_name in voice_text:
                current_app.logger.info(f"語音中找到成員: {member_name}")
                return member_name
        
        # 檢查特定語言模式
        import re
        
        # 模式 1: "為[...]新增" 或 "幫[...]設定"
        patterns = [
            r'為「?([^」《》中文]+)」?新增',
            r'為「?([^」《》中文]+)」?設定',
            r'幫「?([^」《》中文]+)」?新增',
            r'幫「?([^」《》中文]+)」?設定',
            r'給「?([^」《》中文]+)」?設定',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, voice_text)
            if match:
                potential_member = match.group(1).strip()
                # 檢查是否為已存在的成員
                if potential_member in member_names:
                    current_app.logger.info(f"語音模式匹配到成員: {potential_member}")
                    return potential_member
        
        # 模式 2: 家庭關係詞彙對應
        family_relations = {
            '本人': '本人',
            '自己': '本人',
            '我': '本人',
            '爸爸': '爸爸',
            '父親': '爸爸',
            '婆婆': '婆婆',
            '母親': '婆媆',
            '兒子': '兒子',
            '女兒': '女兒',
            '哥哥': '哥哥',
            '姊姊': '姊姊',
            '弟弟': '弟弟',
            '妹妹': '妹妹'
        }
        
        for relation_word, standard_name in family_relations.items():
            if relation_word in voice_text and standard_name in member_names:
                current_app.logger.info(f"語音關係詞匹配到成員: {relation_word} -> {standard_name}")
                return standard_name
        
        return None
        
    except Exception as e:
        current_app.logger.error(f"提取語音成員名稱錯誤: {e}")
        return None

def _show_member_selection_for_voice_reminder(user_id: str, parsed_data: dict, line_bot_api):
    """
    顯示成員選擇選單供語音提醒使用
    
    Args:
        user_id: 用戶ID
        parsed_data: 已解析的提醒資料
        line_bot_api: LINE Bot API實例
    """
    try:
        # 獲取用戶的所有成員
        members = UserService.get_user_members(user_id)
        
        if not members:
            # 如果沒有成員，自動創建本人成員並直接設定提醒
            UserService.get_or_create_user(user_id)
            parsed_data['target_member'] = '本人'
            
            # 直接創建提醒
            from app.routes.handlers import reminder_handler
            reminder_handler.handle_voice_reminder(user_id, parsed_data)
            return
        
        # 將解析的提醒資料儲存到用戶狀態中
        UserService.set_user_complex_state(user_id, {
            'state_info': {
                'state': 'awaiting_member_selection_for_voice_reminder',
                'parsed_reminder_data': parsed_data
            }
        })
        
        # 創建快速回覆按鈕
        quick_reply_buttons = []
        for member in members:
            quick_reply_buttons.append(
                QuickReplyButton(
                    action=MessageAction(
                        label=f"{member['member']}", 
                        text=f"為{member['member']}設定提醒"
                    )
                )
            )
        
        # 添加取消按鈕
        quick_reply_buttons.append(
            QuickReplyButton(
                action=MessageAction(label="取消", text="取消")
            )
        )
        
        quick_reply = QuickReply(items=quick_reply_buttons)
        
        # 建立提醒訊息
        drug_name = parsed_data.get('drug_name', '未指定藥物')
        timing_info = ''
        if parsed_data.get('timing'):
            timing_info = f"\n⏰ 時間：{', '.join(parsed_data['timing'])}"
        elif parsed_data.get('frequency'):
            timing_info = f"\n📅 頻率：{parsed_data['frequency']}"
        
        dosage_info = ''
        if parsed_data.get('dosage'):
            dosage_info = f"\n📊 劑量：{parsed_data['dosage']}"
        
        method_info = ''
        if parsed_data.get('method'):
            method_info = f"\n🍽️ 方式：{parsed_data['method']}"
        
        message_text = (
            f"🎤 語音提醒設定\n\n"
            f"💊 藥物：{drug_name}{timing_info}{dosage_info}{method_info}\n\n"
            f"👥 請選擇要為哪位成員設定提醒："
        )
        
        message = TextSendMessage(text=message_text, quick_reply=quick_reply)
        line_bot_api.push_message(user_id, message)
        
        current_app.logger.info(f"語音提醒成員選擇選單已發送: {user_id}")
        
    except Exception as e:
        current_app.logger.error(f"顯示語音提醒成員選擇錯誤: {e}")
        import traceback
        traceback.print_exc()
        line_bot_api.push_message(user_id, TextSendMessage(
            text="設定提醒時發生錯誤，請重試或使用選單功能。"
        ))

def state_belongs_to_family(state):
    return state and (state.startswith("custom_relation:") or state.startswith("edit_nickname:") or state.startswith("relation_select:"))

def state_belongs_to_reminder(state):
    return state and (state.startswith("awaiting_new_member_name") or state.startswith("rename_member_profile:"))

def handle_query_prescription(event):
    """處理查詢個人藥歷的請求"""
    print("🚀 查詢個人藥歷函數被調用了！")
    current_app.logger.info("🚀 查詢個人藥歷函數被調用了！")
    
    try:
        user_id = event.source.user_id
        print(f"🔍 查詢藥歷 - 用戶ID: {user_id}")
        
        UserService.clear_user_complex_state(user_id)
        
        # 顯示藥歷管理選單
        reply_message = flex_prescription.create_management_menu(
            title="📂 藥歷查詢管理",
            primary_action_label="🔍 開始查詢藥歷",
            primary_action_data="action=initiate_query_process"
        )
        line_bot_api.reply_message(event.reply_token, reply_message)
        print("✅ 藥歷管理選單已發送")
        
    except Exception as e:
        print(f"❌ 查詢藥歷處理錯誤: {e}")
        current_app.logger.error(f"查詢藥歷處理錯誤: {e}")
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text="查詢藥歷功能暫時無法使用，請稍後再試。"))

def _handle_text_message_from_voice(event, user_id, text):
    """
    處理從語音轉換來的文字訊息
    
    這個函數重用現有的文字處理邏輯，但避免重複回覆
    """
    try:
        complex_state = UserService.get_user_complex_state(user_id)
        simple_state = UserService.get_user_simple_state(user_id)
        
        # 第一優先級：全局指令
        high_priority_keywords = {
            # 主選單相關
            "選單": lambda: line_bot_api.push_message(user_id, flex_general.create_main_menu()),
            "主選單": lambda: line_bot_api.push_message(user_id, flex_general.create_main_menu()),
            "menu": lambda: line_bot_api.push_message(user_id, flex_general.create_main_menu()),
            
            # 圖文選單按鈕 - 新的簡化名稱
            "藥單辨識": lambda: prescription_handler.handle(event),
            "用藥提醒": lambda: safe_reminder_handler_call(),
            "健康紀錄": lambda: line_bot_api.push_message(
                user_id, 
                flex_health.generate_health_log_menu(f"https://liff.line.me/{current_app.config['LIFF_ID_HEALTH_FORM']}")
            ),
            
            # 家人綁定
            "家人綁定與管理": lambda: family_handler.handle(event) if family_handler else None,
            
            # 健康記錄相關語音指令
            "記錄體重": lambda: _handle_voice_health_record(user_id, "weight"),
            "記錄血壓": lambda: _handle_voice_health_record(user_id, "blood_pressure"), 
            "記錄血糖": lambda: _handle_voice_health_record(user_id, "blood_sugar"),
            "記錄體溫": lambda: _handle_voice_health_record(user_id, "temperature"),
            "記錄血氧": lambda: _handle_voice_health_record(user_id, "blood_oxygen"),
        }

        if text in high_priority_keywords:
            UserService.delete_user_simple_state(user_id)
            UserService.clear_user_complex_state(user_id)
            high_priority_keywords[text]()
            return
        
        # 檢查是否為數值輸入（健康記錄）
        if _try_parse_health_data_from_voice(user_id, text):
            return
            
        # 檢查是否為成員選擇（在清除狀態之前）
        user_state = UserService.get_user_simple_state(user_id)
        if user_state == "selecting_member_for_reminder":
            safe_reminder_handler_call()
            return

        # 檢查是否在等待特定輸入狀態
        if simple_state:
            if simple_state.startswith("awaiting_new_member_name"):
                safe_reminder_handler_call()
                return
            elif simple_state.startswith("custom_relation"):
                if family_handler:
                    family_handler.handle(event)
                return
            elif simple_state.startswith("rename_member_profile"):
                safe_reminder_handler_call()
                return

        # 如果沒有匹配到任何處理器，提供語音輸入幫助
        help_message = ("🎙️ 語音輸入小提示：\n\n"
                       "📋 選單功能語音指令：\n"
                       "• 說「藥單辨識」或「掃描藥單」\n"
                       "• 說「藥品辨識」或「這是什麼藥」\n"
                       "• 說「用藥提醒」或「設定提醒」\n"
                       "• 說「家人綁定」或「新增家人」\n"
                       "• 說「我的藥歷」或「我的藥單」\n"
                       "• 說「健康紀錄」或「記錄健康數據」\n"
                       "• 說「查詢本人」查看個人提醒\n"
                       "• 說「查詢家人」查看家人提醒\n"
                       "• 說「新增本人」設定個人提醒\n\n"
                       "📝 其他功能：\n"
                       "• 說「主選單」查看所有功能\n"
                       "• 說「記錄體重65公斤」記錄健康數據")
        
        line_bot_api.push_message(user_id, TextSendMessage(text=help_message))
        
    except Exception as e:
        current_app.logger.error(f"語音文字處理錯誤: {e}")
        line_bot_api.push_message(user_id, 
            TextSendMessage(text="❌ 處理語音指令時發生錯誤，請重試"))

def _process_voice_text_result(user_id: str, text: str, line_bot_api):
    """處理語音轉文字的結果"""
    try:
        # 簡單的文字指令處理
        text_lower = text.lower().strip()
        
        # 主選單相關指令
        if any(keyword in text for keyword in ["選單", "主選單", "menu"]):
            from app.utils.flex import general as flex_general
            line_bot_api.push_message(user_id, flex_general.create_main_menu())
            return
        
        # 檢查是否為用藥提醒指令
        medication_result = _parse_voice_medication_command(text)
        if medication_result:
            _handle_voice_medication_command(user_id, medication_result, line_bot_api)
            return
        
        # 健康記錄相關指令
        health_keywords = ["體重", "血壓", "血糖", "體溫", "血氧"]
        for keyword in health_keywords:
            if keyword in text:
                _handle_voice_health_record(user_id, keyword, line_bot_api)
                return
        
        # 如果沒有匹配到特定指令，提供幫助訊息
        help_message = f"🎙️ 收到您的語音：「{text}」\n\n如需協助，請說「主選單」查看所有功能。"
        line_bot_api.push_message(user_id, TextSendMessage(text=help_message))
        
    except Exception as e:
        current_app.logger.error(f"處理語音文字結果錯誤: {e}")
        line_bot_api.push_message(user_id, 
            TextSendMessage(text="❌ 處理語音指令時發生錯誤，請重試"))

def _handle_voice_health_record(user_id: str, record_type: str, line_bot_api):
    """處理語音健康記錄指令"""
    from app.services.voice_service import VoiceService
    suggestions = VoiceService.get_voice_input_suggestions("health_record")
    
    message = f"🎙️ 請說出您的{record_type}數值，例如：\n"
    for suggestion in suggestions[:3]:  # 只顯示前3個建議
        message += f"• {suggestion}\n"
    
    line_bot_api.push_message(user_id, TextSendMessage(text=message))
    
    # 設定用戶狀態為等待健康數據輸入
    UserService.save_user_simple_state(user_id, f"awaiting_voice_health_data:{record_type}")

def _try_parse_health_data_from_voice(user_id: str, text: str) -> bool:
    """
    嘗試從語音文字中解析健康數據
    
    Returns:
        True if parsed and processed successfully, False otherwise
    """
    import re
    
    # 檢查是否在等待健康數據輸入狀態
    user_state = UserService.get_user_simple_state(user_id)
    if not user_state or not user_state.startswith("awaiting_voice_health_data:"):
        return False
    
    record_type = user_state.split(":")[1]
    
    try:
        # 根據不同類型解析數據
        data = {}
        success = False
        
        if record_type == "weight":
            # 解析體重：65公斤、65.5kg等
            weight_match = re.search(r'(\d+(?:\.\d+)?)\s*(?:公斤|kg|kilogram)', text, re.IGNORECASE)
            if weight_match:
                data['weight'] = float(weight_match.group(1))
                success = True
                
        elif record_type == "blood_pressure":
            # 解析血壓：130/80、收縮壓130舒張壓80等
            bp_match = re.search(r'(\d+)[/／]\s*(\d+)', text)
            if bp_match:
                data['systolic_pressure'] = int(bp_match.group(1))
                data['diastolic_pressure'] = int(bp_match.group(2))
                success = True
            else:
                # 嘗試解析中文描述
                systolic_match = re.search(r'收縮壓\s*(\d+)', text)
                diastolic_match = re.search(r'舒張壓\s*(\d+)', text)
                if systolic_match and diastolic_match:
                    data['systolic_pressure'] = int(systolic_match.group(1))
                    data['diastolic_pressure'] = int(diastolic_match.group(1))
                    success = True
                    
        elif record_type == "blood_sugar":
            # 解析血糖：120、血糖120等
            sugar_match = re.search(r'(?:血糖)?\s*(\d+(?:\.\d+)?)', text)
            if sugar_match:
                data['blood_sugar'] = float(sugar_match.group(1))
                success = True
                
        elif record_type == "temperature":
            # 解析體溫：36.5度、36.5°C等
            temp_match = re.search(r'(\d+(?:\.\d+)?)\s*(?:度|°C|度C)', text, re.IGNORECASE)
            if temp_match:
                data['temperature'] = float(temp_match.group(1))
                success = True
                
        elif record_type == "blood_oxygen":
            # 解析血氧：95%、血氧95等
            oxygen_match = re.search(r'(?:血氧)?\s*(\d+(?:\.\d+)?)%?', text)
            if oxygen_match:
                data['blood_oxygen'] = float(oxygen_match.group(1))
                success = True
        
        if success:
            # 清除狀態
            UserService.delete_user_simple_state(user_id)
            
            # 模擬保存健康記錄的API調用
            from datetime import datetime
            record_data = {
                'recorderId': user_id,
                'targetPerson': '本人',  # 語音輸入預設為本人
                'record_time': datetime.now().isoformat(),
                **data
            }
            
            # 這裡應該調用健康記錄的保存API
            # 暫時發送確認訊息
            confirmation = f"✅ 已記錄您的{record_type}數據：\n"
            for key, value in data.items():
                confirmation += f"• {key.replace('_', ' ').title()}: {value}\n"
            
            line_bot_api.push_message(user_id, TextSendMessage(text=confirmation))
            return True
        else:
            # 解析失敗，提供幫助
            help_msg = f"❌ 無法識別{record_type}數據，請重新說一次"
            line_bot_api.push_message(user_id, TextSendMessage(text=help_msg))
            return True  # 雖然失敗，但已處理過這個狀態
            
    except Exception as e:
        current_app.logger.error(f"解析語音健康數據錯誤: {e}")
        line_bot_api.push_message(user_id, 
            TextSendMessage(text="❌ 數據解析錯誤，請重新輸入"))
        return True
    
    return False

def _parse_voice_medication_command(text: str) -> dict:
    """
    Enhanced voice medication command parser with improved natural language understanding
    
    Supports patterns like:
    - "新增用藥血壓藥，每天早上8點吃一顆"
    - "提醒我吃維他命，每天早上一粒"
    - "設定胃藥提醒，飯前30分鐘服用"
    - "我要加血糖藥，每日三次"
    
    Returns:
        Dict with parsed medication info or None if not a medication command
    """
    import re
    
    # Clean and normalize the text
    text = text.strip().replace("，", ",").replace("。", "")
    
    # Enhanced command detection patterns
    add_patterns = [
        # Direct medication addition commands
        r"新增用藥|新增藥物|新增提醒|設定提醒|添加用藥|加入用藥",
        # Natural language patterns
        r"提醒我吃|提醒我服用|幫我設定|我要加|我要設定",
        # Reminder-focused patterns  
        r"設定.*提醒|建立.*提醒|增加.*提醒"
    ]
    
    is_add_command = any(re.search(pattern, text) for pattern in add_patterns)
    
    if not is_add_command:
        return None
    
    result = {
        "action": "add_medication_reminder",
        "member": "本人",  # Default to self for voice commands
        "drug_name": None,
        "frequency": None,
        "timing": None,
        "dosage": None,
        "original_text": text
    }
    
    # Enhanced drug name extraction with multiple strategies
    drug_name = _extract_drug_name_enhanced(text)
    if drug_name:
        result["drug_name"] = drug_name
    
    # Enhanced frequency extraction
    frequency = _extract_frequency_enhanced(text)
    if frequency:
        result["frequency"] = frequency
    
    # Enhanced timing extraction  
    timing = _extract_timing_enhanced(text)
    if timing:
        result["timing"] = timing
    
    # Enhanced dosage extraction
    dosage = _extract_dosage_enhanced(text)
    if dosage:
        result["dosage"] = dosage
    
    return result

def _extract_drug_name_enhanced(text: str) -> str:
    """Enhanced drug name extraction with multiple strategies"""
    import re
    
    # Strategy 1: After command keywords and before timing/frequency words
    command_patterns = [
        r"新增用藥(.+?)(?:[,，]|每|一天|早上|中午|下午|晚上|睡前|飯前|飯後|$)",
        r"新增藥物(.+?)(?:[,，]|每|一天|早上|中午|下午|晚上|睡前|飯前|飯後|$)",
        r"設定(.+?)提醒",
        r"提醒我吃(.+?)(?:[,，]|每|一天|早上|中午|下午|晚上|睡前|飯前|飯後|$)",
        r"我要加(.+?)(?:[,，]|每|一天|早上|中午|下午|晚上|睡前|飯前|飯後|$)",
        r"我要設定(.+?)(?:[,，]|每|一天|早上|中午|下午|晚上|睡前|飯前|飯後|$)"
    ]
    
    for pattern in command_patterns:
        match = re.search(pattern, text)
        if match:
            drug_name = match.group(1).strip()
            # Clean up common noise words
            noise_words = ["的", "藥", "提醒", "時間"]
            for noise in noise_words:
                if drug_name.endswith(noise) and len(drug_name) > 1:
                    drug_name = drug_name[:-len(noise)]
            if drug_name:
                return drug_name
    
    # Strategy 2: Common medication names detection
    common_medications = [
        "血壓藥", "血糖藥", "胃藥", "感冒藥", "止痛藥", "維他命", "鈣片",
        "血脂藥", "心臟藥", "降血壓藥", "降血糖藥", "抗生素", "消炎藥"
    ]
    
    for med in common_medications:
        if med in text:
            return med
    
    return None

def _extract_frequency_enhanced(text: str) -> str:
    """Enhanced frequency extraction with natural language patterns"""
    
    # Comprehensive frequency patterns
    frequency_patterns = {
        # Standard patterns
        "每天": "QD", "每日": "QD",
        "一天一次": "QD", "一日一次": "QD", "每天一次": "QD",
        "一天兩次": "BID", "一日兩次": "BID", "每天兩次": "BID",
        "一天三次": "TID", "一日三次": "TID", "每天三次": "TID",
        "一天四次": "QID", "一日四次": "QID", "每天四次": "QID",
        
        # Alternative expressions
        "每天一顆": "QD", "每天一粒": "QD", "每日一顆": "QD", "每日一粒": "QD",
        "早晚各一次": "BID", "早晚": "BID",
        "三餐飯前": "TID", "三餐飯後": "TID", "飯前": "TID", "飯後": "TID",
        "每天早上": "QD", "每天晚上": "QD",
        
        # Numeric patterns
        "1天1次": "QD", "1日1次": "QD",
        "1天2次": "BID", "1日2次": "BID", 
        "1天3次": "TID", "1日3次": "TID",
        "1天4次": "QID", "1日4次": "QID"
    }
    
    for freq_text, freq_code in frequency_patterns.items():
        if freq_text in text:
            return freq_code
    
    return None

def _extract_timing_enhanced(text: str) -> str:
    """Enhanced timing extraction with flexible time patterns"""
    import re
    
    # Strategy 1: 檢測多個時間點的複合指令（如：早上8點和下午2點）
    multiple_times = _extract_multiple_times(text)
    if multiple_times:
        # 對於多個時間點，回傳第一個時間作為主要時間
        # 並在後續處理中創建多個提醒
        return multiple_times[0]
    
    # Strategy 2: Specific time patterns
    time_patterns = [
        (r"(\d{1,2})點(\d{2})?分?", lambda m: f"{int(m.group(1)):02d}:{m.group(2) or '00'}"),
        (r"(\d{1,2}):\d{2}", lambda m: m.group(0) if int(m.group(0).split(':')[0]) <= 23 else None),
    ]
    
    for pattern, formatter in time_patterns:
        match = re.search(pattern, text)
        if match:
            result = formatter(match)
            if result:
                return result
    
    # Strategy 3: Time period mapping
    timing_patterns = {
        # Basic time periods
        "早上": "08:00", "早晨": "08:00", "清晨": "07:00",
        "上午": "10:00", 
        "中午": "12:00", "正午": "12:00",
        "下午": "14:00", "午後": "15:00",
        "傍晚": "17:00", "晚上": "18:00", "夜晚": "20:00",
        "睡前": "22:00", "就寢前": "22:00",
        
        # Meal-related timing
        "飯前": "07:30", "餐前": "07:30",
        "飯後": "08:30", "餐後": "08:30",
        "早餐前": "07:30", "早餐後": "08:30",
        "午餐前": "11:30", "午餐後": "13:00",
        "晚餐前": "17:30", "晚餐後": "19:00",
        
        # Specific periods
        "起床後": "07:00", "起床時": "07:00",
    }
    
    for timing_text, timing_code in timing_patterns.items():
        if timing_text in text:
            return timing_code
    
    return None

def _extract_multiple_times(text: str) -> list:
    """提取文字中的多個時間點"""
    import re
    
    times = []
    
    # 尋找「和」、「與」、「還有」等連接詞前後的時間
    time_connectors = ["和", "與", "還有", "以及", "及"]
    
    for connector in time_connectors:
        if connector in text:
            # 分割文字
            parts = text.split(connector)
            
            # 從每個部分提取時間
            for part in parts:
                time = _extract_single_time_from_text(part.strip())
                if time and time not in times:
                    times.append(time)
    
    # 如果沒有找到連接詞，嘗試尋找多個獨立的時間表達
    if not times:
        # 尋找所有時間模式
        time_patterns = [
            r"(\d{1,2})點",
            r"早上", r"中午", r"下午", r"晚上", r"睡前"
        ]
        
        found_times = []
        for pattern in time_patterns:
            matches = re.finditer(pattern, text)
            for match in matches:
                time_str = match.group(0)
                time = _convert_time_string_to_24h(time_str)
                if time and time not in found_times:
                    found_times.append(time)
        
        times = found_times
    
    return times

def _extract_single_time_from_text(text: str) -> str:
    """從單個文字片段中提取時間"""
    import re
    
    # 數字時間模式
    time_match = re.search(r"(\d{1,2})點", text)
    if time_match:
        hour = int(time_match.group(1))
        return f"{hour:02d}:00"
    
    # 時段模式
    if "早上" in text or "早晨" in text:
        return "08:00"
    elif "中午" in text:
        return "12:00"
    elif "下午" in text:
        return "14:00"
    elif "晚上" in text:
        return "18:00"
    elif "睡前" in text:
        return "22:00"
    
    return None

def _convert_time_string_to_24h(time_str: str) -> str:
    """將時間字串轉換為24小時格式"""
    import re
    
    # 處理數字時間
    time_match = re.search(r"(\d{1,2})點", time_str)
    if time_match:
        hour = int(time_match.group(1))
        return f"{hour:02d}:00"
    
    # 處理時段
    time_mapping = {
        "早上": "08:00", "早晨": "08:00",
        "中午": "12:00", "正午": "12:00",
        "下午": "14:00", "午後": "15:00",
        "晚上": "18:00", "夜晚": "20:00",
        "睡前": "22:00"
    }
    
    for period, time in time_mapping.items():
        if period in time_str:
            return time
    
    return None

def _extract_dosage_enhanced(text: str) -> str:
    """Enhanced dosage extraction with multiple unit types"""
    import re
    
    # Dosage patterns with various units and expressions
    dosage_patterns = [
        # Standard patterns
        (r"吃(\d+)顆", r"\1顆"),
        (r"服用(\d+)顆", r"\1顆"),
        (r"(\d+)顆", r"\1顆"),
        (r"吃(\d+)粒", r"\1粒"),
        (r"服用(\d+)粒", r"\1粒"),
        (r"(\d+)粒", r"\1粒"),
        
        # Alternative units
        (r"吃(\d+)錠", r"\1錠"),
        (r"服用(\d+)錠", r"\1錠"),
        (r"(\d+)錠", r"\1錠"),
        (r"吃(\d+)片", r"\1片"),
        (r"服用(\d+)片", r"\1片"),
        (r"(\d+)片", r"\1片"),
        
        # Liquid medications
        (r"喝(\d+)毫升", r"\1ml"),
        (r"(\d+)毫升", r"\1ml"),
        (r"(\d+)ml", r"\1ml"),
        
        # Natural language patterns
        (r"一顆", "1顆"),
        (r"兩顆", "2顆"),
        (r"三顆", "3顆"),
        (r"一粒", "1粒"),
        (r"兩粒", "2粒"),
        (r"三粒", "3粒"),
    ]
    
    for pattern, replacement in dosage_patterns:
        if isinstance(pattern, str):
            if pattern in text:
                return replacement
        else:  # regex pattern
            match = re.search(pattern, text)
            if match:
                return re.sub(pattern, replacement, match.group(0))
    
    return None

def _handle_voice_medication_command(user_id: str, medication_data: dict, line_bot_api):
    """處理語音用藥提醒指令"""
    try:
        from app.utils.db import DB
        
        # 確保用戶有本人成員記錄
        self_member = DB.get_self_member(user_id)
        if not self_member:
            # 創建本人成員記錄
            UserService.get_or_create_user(user_id)
            self_member = DB.get_self_member(user_id)
        
        if not self_member:
            line_bot_api.push_message(user_id, TextSendMessage(
                text="❌ 無法創建本人資料，請稍後再試或使用選單功能。"
            ))
            return
        
        # 準備提醒資料 - 轉換為資料庫需要的格式
        timing = medication_data.get('timing', '08:00')
        frequency = medication_data.get('frequency', 'QD')
        dosage = medication_data.get('dosage', '1顆')
        
        # 根據頻率設定時間槽
        time_slots = _convert_frequency_to_time_slots(frequency, timing)
        
        reminder_data = {
            'recorder_id': user_id,
            'member': '本人',
            'drug_name': medication_data.get('drug_name', '未命名藥品'),
            'dose_quantity': dosage,
            'notes': f"由語音建立：{medication_data['original_text']}",
            'frequency_name': frequency,
            'time_slot_1': time_slots.get('time_slot_1'),
            'time_slot_2': time_slots.get('time_slot_2'),
            'time_slot_3': time_slots.get('time_slot_3'),
            'time_slot_4': time_slots.get('time_slot_4'),
            'time_slot_5': time_slots.get('time_slot_5')
        }
        
        # 直接使用 DB.create_reminder 創建提醒
        result = DB.create_reminder(reminder_data)
        
        if result:
            # 成功創建提醒
            confirmation_message = (
                f"✅ 語音提醒設定成功！\n\n"
                f"💊 藥品：{reminder_data['drug_name']}\n"
                f"👤 對象：{reminder_data['member']}\n"
                f"⏰ 時間：{timing}\n"
                f"📊 頻率：{frequency}\n"
                f"💊 劑量：{dosage}\n\n"
                f"🎙️ 原始語音：「{medication_data['original_text']}」"
            )
            line_bot_api.push_message(user_id, TextSendMessage(text=confirmation_message))
            current_app.logger.info(f"語音用藥提醒創建成功 - 用戶: {user_id}, 藥品: {reminder_data['drug_name']}")
        else:
            line_bot_api.push_message(user_id, TextSendMessage(
                text="❌ 創建提醒失敗，請稍後再試或使用選單功能手動設定。"
            ))
            current_app.logger.error(f"語音用藥提醒創建失敗 - 用戶: {user_id}")
            
    except Exception as e:
        current_app.logger.error(f"處理語音用藥指令錯誤: {e}")
        line_bot_api.push_message(user_id, TextSendMessage(
            text="❌ 處理語音用藥指令時發生錯誤，請稍後再試。"
        ))

def _convert_frequency_to_time_slots(frequency: str, default_time: str) -> dict:
    """將頻率和時間轉換為資料庫的時間槽格式"""
    
    # 預設時間槽設定
    time_slots = {
        'time_slot_1': None,
        'time_slot_2': None, 
        'time_slot_3': None,
        'time_slot_4': None,
        'time_slot_5': None
    }
    
    if frequency == 'QD':  # 每天一次
        time_slots['time_slot_1'] = default_time
        
    elif frequency == 'BID':  # 每天兩次
        time_slots['time_slot_1'] = '08:00'
        time_slots['time_slot_2'] = '20:00'
        
    elif frequency == 'TID':  # 每天三次
        time_slots['time_slot_1'] = '08:00'
        time_slots['time_slot_2'] = '14:00'
        time_slots['time_slot_3'] = '20:00'
        
    elif frequency == 'QID':  # 每天四次
        time_slots['time_slot_1'] = '08:00'
        time_slots['time_slot_2'] = '12:00'
        time_slots['time_slot_3'] = '16:00'
        time_slots['time_slot_4'] = '20:00'
        
    else:  # 預設為每天一次
        time_slots['time_slot_1'] = default_time or '08:00'
    
    return time_slots


def handle_pill_recognition(event):
    """處理藥丸辨識的請求"""
    try:
        print(f"🔍 [Pill Recognition] 收到藥品辨識請求")
        # 先檢查全局導入的 pill_handler
        if pill_handler:
            print(f"✅ [Pill Recognition] 使用全局 pill_handler")
            pill_handler.handle(event)
            return
        
        # 如果全局導入失敗，嘗試動態導入
        from .handlers import pill_handler as ph
        if ph:
            print(f"✅ [Pill Recognition] 使用動態導入 pill_handler")
            ph.handle(event)
        else:
            print(f"❌ [Pill Recognition] pill_handler 模組存在但為 None")
            current_app.logger.error("pill_handler 模組存在但為 None")
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text="藥丸辨識功能暫時無法使用，請稍後再試。"))
    except ImportError as e:
        print(f"❌ [Pill Recognition] 無法導入 pill_handler: {e}")
        current_app.logger.error(f"無法導入 pill_handler: {e}")
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text="藥丸辨識功能暫時無法使用，請稍後再試。"))
    except Exception as e:
        print(f"❌ [Pill Recognition] 處理錯誤: {e}")
        current_app.logger.error(f"藥丸辨識處理錯誤: {e}")
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text="藥丸辨識功能發生錯誤，請稍後再試。"))

def handle_settings_menu(event):
    """處理設定選單的請求"""
    try:
        settings_card = flex_settings.create_main_settings_menu()
        flex_message = FlexSendMessage(alt_text="設定選單", contents=settings_card)
        line_bot_api.reply_message(event.reply_token, flex_message)
    except Exception as e:
        current_app.logger.error(f"設定選單處理錯誤: {e}")
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text="設定選單暫時無法使用，請稍後再試。"))

def handle_health_record_menu(event):
    """處理健康記錄選單的請求"""
    print("🚀 健康記錄選單函數被調用了！")
    current_app.logger.info("🚀 健康記錄選單函數被調用了！")
    
    try:
        import os
        env_liff_id = os.environ.get('LIFF_ID_HEALTH_FORM')
        config_liff_id = current_app.config['LIFF_ID_HEALTH_FORM']
        
        print(f"🔍 健康記錄 - 環境變數 LIFF_ID_HEALTH_FORM: {env_liff_id}")
        print(f"🔍 健康記錄 - Config LIFF_ID_HEALTH_FORM: {config_liff_id}")
        current_app.logger.info(f"🔍 健康記錄 - 環境變數 LIFF_ID_HEALTH_FORM: {env_liff_id}")
        current_app.logger.info(f"🔍 健康記錄 - Config LIFF_ID_HEALTH_FORM: {config_liff_id}")
        
        # 使用配置中的 LIFF ID
        liff_url = f"https://liff.line.me/{config_liff_id}"
        
        print(f"🔧 健康記錄 - 強制使用正確的 LIFF URL: {liff_url}")
        current_app.logger.info(f"🔧 健康記錄 - 強制使用正確的 LIFF URL: {liff_url}")
        
        flex_message = flex_health.generate_health_log_menu(liff_url)
        line_bot_api.reply_message(event.reply_token, flex_message)
        print("✅ 健康記錄選單已發送")
    except Exception as e:
        print(f"❌ 健康記錄選單處理錯誤: {e}")
        current_app.logger.error(f"健康記錄選單處理錯誤: {e}")
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text="健康記錄功能暫時無法使用，請稍後再試。"))

def handle_login_request(event):
    """處理登入請求"""
    try:
        from flask import url_for
        login_url = url_for('auth.login', _external=True)
        login_card = flex_settings.create_login_card(login_url)
        flex_message = FlexSendMessage(alt_text="會員登入", contents=login_card)
        line_bot_api.reply_message(event.reply_token, flex_message)
    except Exception as e:
        current_app.logger.error(f"登入請求處理錯誤: {e}")
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text="登入功能暫時無法使用，請稍後再試。"))

@handler.add(FollowEvent)
def handle_follow_event(event):
    """處理用戶第一次加入 Bot 的事件 - 顯示個人資料蒐集聲明"""
    try:
        user_id = event.source.user_id
        current_app.logger.info(f"新用戶加入: {user_id}")
        
        # 建立或獲取用戶資料
        user_name = UserService.get_or_create_user(user_id)
        
        # 簡化的歡迎訊息
        welcome_message = (
            "🎉 歡迎加入健康藥管家！\n\n"
            "📋 個人資料蒐集聲明\n"
            "當您加入並持續使用，即視為同意我們蒐集並使用您的個人資料，以提供相關服務。"
            "（例如：LINE 顯示名稱、使用者 ID、互動紀錄等）。\n\n"
            "本資料僅用於個人功能使用，感謝您的信任與配合！\n\n"
            "請輸入「選單」查看所有功能。"
        )
        
        # 發送歡迎訊息
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=welcome_message))
        current_app.logger.info(f"已向新用戶 {user_name} ({user_id}) 發送歡迎訊息")
        
    except Exception as e:
        current_app.logger.error(f"處理新用戶加入事件錯誤: {e}")
        # 如果發生錯誤，至少發送基本歡迎訊息
        try:
            line_bot_api.reply_message(
                event.reply_token, 
                TextSendMessage(text="🎉 歡迎加入家庭健康小幫手！\n\n請輸入「選單」查看所有功能。")
            )
        except Exception as fallback_error:
            current_app.logger.error(f"發送備用歡迎訊息也失敗: {fallback_error}")

@handler.add(PostbackEvent)
def handle_postback_dispatcher(event):
    from urllib.parse import parse_qs, unquote
    
    data_str = event.postback.data
    
    if data_str.startswith('relation:'):
        family_handler.handle(event)
        return
    
    # 處理圖文選單的直接文字 postback（暫時保留，直到圖文選單更新為 MessageAction）
    if data_str == "我的藥歷":
        handle_query_prescription(event)
        return
    
    try:
        data = parse_qs(unquote(data_str))
        action = data.get('action', [None])[0]
    except (ValueError, IndexError, AttributeError):
        action = None
        
    if not action:
        current_app.logger.warning(f"收到一個無法解析的 Postback data: {data_str}")
        return

    if action == 'start_scan_flow':
        reply_message = flex_prescription.create_management_menu(
            title="📋 藥單辨識管理",
            primary_action_label="📲 掃描新藥單",
            primary_action_data="action=initiate_scan_process"
        )
        line_bot_api.reply_message(event.reply_token, reply_message)
        return
        
    if action == 'start_query_flow':
        reply_message = flex_prescription.create_management_menu(
            title="📂 藥歷查詢管理",
            primary_action_label="🔍 開始查詢藥歷",
            primary_action_data="action=initiate_query_process"
        )
        line_bot_api.reply_message(event.reply_token, reply_message)
        return

    prescription_actions = [
        'initiate_scan_process', 'initiate_query_process', 'prescription_model_select',
        'select_patient_for_scan', 'start_camera', 'manual_edit_liff', 'provide_visit_date', 
        'confirm_save_final', 'list_records', 'view_record_details', 
        'confirm_delete_record', 'execute_delete_record', 'load_record_as_draft', 'cancel_task'
    ]
    family_actions = [
        'gen_code', 'confirm_bind', 'manage_family', 'cancel_bind',
        'edit_nickname', 'delete_binding', 'query_family'
    ]
    reminder_actions = [
        'confirm_delete_reminder', 'execute_delete_reminder', 'clear_reminders_for_member', 'execute_clear_reminders',
        'add_member_profile', 'delete_member_profile_confirm',
        'add_from_prescription', 'rename_member_profile', 'execute_delete_member_profile',
        'delete_reminder', 'view_reminders_page', 'cancel_task'
    ]
    pill_actions = [
        'select_model_mode', 'use_single_model', 'show_model_info', 'back_to_model_menu',
        'get_pill_info'
    ]
    settings_actions = [
        'login_settings', 'show_instructions'
    ]
    health_actions = [
        'health_record'
    ]
    voice_menu_actions = [
        'prescription_scan', 'pill_scan', 'reminder_menu', 'family_menu', 'prescription_history', 'view_existing_reminders', 'query_family_reminders'
    ]
    
    if action in prescription_actions:
        prescription_handler.handle(event)
    elif action in family_actions:
        family_handler.handle(event)
    elif action in reminder_actions:
        try:
            from .handlers import reminder_handler as rh
            rh.handle(event)
        except ImportError:
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text="❌ 用藥提醒功能暫時無法使用"))
    elif action in pill_actions:
        try:
            from .handlers import pill_handler as ph
            if ph:
                ph.handle(event)
            else:
                current_app.logger.warning("pill_handler 不可用")
        except ImportError:
            current_app.logger.error("无法导入 pill_handler")
    elif action in settings_actions:
        handle_settings_postback(event, action)
    elif action in health_actions:
        handle_health_postback(event, action)
    elif action in voice_menu_actions:
        handle_voice_menu_postback(event, action)
    else:
        current_app.logger.warning(f"收到一个未知的 Postback action: {action}")

def handle_settings_postback(event, action):
    """處理設定相關的 postback 事件"""
    try:
        if action == 'login_settings':
            from flask import url_for
            login_url = url_for('auth.login', _external=True)
            login_card = flex_settings.create_login_card(login_url)
            flex_message = FlexSendMessage(alt_text="會員登入", contents=login_card)
            line_bot_api.reply_message(event.reply_token, flex_message)
            
        elif action == 'show_instructions':
            instructions_card = flex_settings.create_instructions_card()
            flex_message = FlexSendMessage(alt_text="使用說明", contents=instructions_card)
            line_bot_api.reply_message(event.reply_token, flex_message)
            
    except Exception as e:
        current_app.logger.error(f"設定 postback 處理錯誤: {e}")
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text="設定功能發生錯誤，請稍後再試。"))

def handle_health_postback(event, action):
    """處理健康記錄相關的 postback 事件"""
    try:
        if action == 'health_record':
            # 檢查是否有 reply_token，如果沒有則使用 push_message
            user_id = event.source.user_id
            
            if event.reply_token:
                # 有 reply_token，使用原本的函數
                handle_health_record_menu(event)
            else:
                # 沒有 reply_token，直接發送健康記錄選單
                from app.utils.flex import health as flex_health
                from flask import current_app
                
                liff_url = f"https://liff.line.me/{current_app.config['LIFF_ID_HEALTH_FORM']}"
                flex_message = flex_health.generate_health_log_menu(liff_url)
                line_bot_api.push_message(user_id, flex_message)
                
            current_app.logger.info("語音觸發健康記錄選單成功")
            
    except Exception as e:
        current_app.logger.error(f"健康記錄 postback 處理錯誤: {e}")
        user_id = event.source.user_id
        line_bot_api.push_message(user_id, TextSendMessage(text="健康記錄功能發生錯誤，請稍後再試。"))

def handle_voice_menu_postback(event, action):
    """處理語音選單相關的 postback 事件"""
    try:
        user_id = event.source.user_id
        
        if action == 'prescription_scan':
            # 藥單辨識
            from .handlers import prescription_handler
            if event.reply_token:
                prescription_handler.handle(event)
            else:
                # 使用原本的藥單辨識選單
                from app.utils.flex import prescription as flex_prescription
                flex_message = flex_prescription.create_prescription_model_choice()
                line_bot_api.push_message(user_id, FlexSendMessage(alt_text="藥單辨識選單", contents=flex_message))
            current_app.logger.info("語音觸發藥單辨識成功")
            
        elif action == 'pill_scan':
            # 藥品辨識
            try:
                from .handlers import pill_handler as ph
                if ph and event.reply_token:
                    ph.handle(event)
                else:
                    # 發送藥品辨識選單
                    from app.utils.flex import pill as flex_pill
                    flex_message = flex_pill.generate_pill_identification_menu()
                    line_bot_api.push_message(user_id, flex_message)
            except ImportError:
                line_bot_api.push_message(user_id, TextSendMessage(text="藥品辨識功能暫時無法使用"))
            current_app.logger.info("語音觸發藥品辨識成功")
            
        elif action == 'reminder_menu':
            # 用藥提醒
            if event.reply_token:
                try:
                    from .handlers import reminder_handler as rh
                    rh.handle(event)
                except ImportError:
                    line_bot_api.reply_message(event.reply_token, TextSendMessage(text="❌ 用藥提醒功能暫時無法使用"))
            else:
                # 發送提醒選單
                from app.utils.flex import reminder as flex_reminder
                flex_message = flex_reminder.create_reminder_management_menu()
                line_bot_api.push_message(user_id, flex_message)
            current_app.logger.info("語音觸發用藥提醒成功")
            
        elif action == 'family_menu':
            # 家人綁定
            from .handlers import family_handler
            if event.reply_token:
                family_handler.handle(event)
            else:
                # 發送家人管理選單
                from app.utils.flex import family as flex_family
                flex_message = flex_family.create_family_binding_menu()
                line_bot_api.push_message(user_id, flex_message)
            current_app.logger.info("語音觸發家人綁定成功")
            
        elif action == 'prescription_history':
            # 藥歷查詢
            from .handlers import prescription_handler
            if event.reply_token:
                prescription_handler.handle(event)
            else:
                # 使用原本的藥歷查詢管理選單
                from app.utils.flex import prescription as flex_prescription
                flex_message = flex_prescription.create_management_menu(
                    title="📂 藥歷查詢管理",
                    primary_action_label="🔍 開始查詢藥歷",
                    primary_action_data="action=initiate_query_process"
                )
                line_bot_api.push_message(user_id, flex_message)
            current_app.logger.info("語音觸發藥歷查詢成功")
            
        elif action == 'view_existing_reminders':
            # 查詢指定成員的提醒 - 使用卡片顯示
            try:
                from app.utils.flex import reminder as flex_reminder
                from app.services.reminder_service import ReminderService
                from flask import current_app
                from urllib.parse import parse_qs, unquote
                
                # 解析 member 參數
                data = parse_qs(unquote(event.postback.data))
                member_name = data.get('member', ['本人'])[0]  # 默認為本人
                
                # 獲取用戶的所有成員
                members = UserService.get_user_members(user_id)
                # 找到指定的成員資料
                target_member = next((m for m in members if m['member'] == member_name), None)
                
                if target_member:
                    # 獲取指定成員的提醒列表
                    reminders = ReminderService.get_reminders_for_member(user_id, member_name)
                    liff_id = current_app.config['LIFF_ID_MANUAL_REMINDER']
                    flex_message = flex_reminder.create_reminder_list_carousel(target_member, reminders, liff_id)
                    
                    line_bot_api.push_message(user_id, flex_message)
                    current_app.logger.info("語音觸發查詢本人提醒成功 - 顯示卡片")
                else:
                    # 如果找不到本人，發送錯誤訊息
                    line_bot_api.push_message(user_id, TextSendMessage(text="❌ 找不到本人的資料，請先設定提醒對象"))
                    current_app.logger.warning(f"找不到用戶 {user_id} 的本人資料")
                
            except Exception as carousel_error:
                current_app.logger.error(f"創建提醒卡片失敗: {carousel_error}")
                # 如果卡片創建失敗，發送簡單文字訊息
                line_bot_api.push_message(user_id, TextSendMessage(
                    text="🔍 查詢本人提醒功能\n\n正在為您查詢用藥提醒資訊...\n\n請稍後使用「用藥提醒」選單查看完整的提醒列表。"
                ))
                current_app.logger.info("語音觸發查詢本人提醒成功 - 備用文字")
                
        elif action == 'query_family_reminders':
            # 查詢家人提醒 - 顯示本人的提醒列表卡片
            from app.services import reminder_service
            from app.utils.flex import reminder as flex_reminder
            from flask import current_app
            
            # 獲取用戶的所有成員（包括本人）
            members = UserService.get_user_members(user_id)
            # 找到本人的成員資料
            target_member = next((m for m in members if m['member'] == '本人'), None)
            
            if target_member:
                # 獲取本人的提醒列表
                reminders = reminder_service.ReminderService.get_reminders_for_member(user_id, "本人")
                liff_id = current_app.config['LIFF_ID_MANUAL_REMINDER']
                flex_message = flex_reminder.create_reminder_list_carousel(target_member, reminders, liff_id)
                
                # 使用 push_message 發送訊息
                line_bot_api.push_message(user_id, flex_message)
                current_app.logger.info(f"語音觸發查詢提醒成功 - 顯示「{member_name}」的提醒列表")
            else:
                # 如果找不到指定成員，發送錯誤訊息
                line_bot_api.push_message(user_id, TextSendMessage(text=f"❌ 找不到「{member_name}」的資料，請先設定提醒對象"))
                current_app.logger.warning(f"找不到用戶 {user_id} 的「{member_name}」資料")
            
    except Exception as e:
        current_app.logger.error(f"語音選單 postback 處理錯誤 (action={action}): {e}")
        
        user_id = event.source.user_id
        try:
            line_bot_api.push_message(user_id, TextSendMessage(text="功能發生錯誤，請稍後再試。"))
        except Exception as push_error:
            current_app.logger.error(f"發送錯誤訊息失敗: {push_error}")