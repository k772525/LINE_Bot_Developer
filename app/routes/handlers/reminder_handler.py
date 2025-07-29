# --- 完整修正後的 app/routes/handlers/reminder_handler.py ---

from flask import current_app
from linebot.models import TextSendMessage, QuickReply, QuickReplyButton, MessageAction
from urllib.parse import parse_qs, unquote, quote

from app.services.user_service import UserService
from app.services import reminder_service
from app.utils.flex import reminder as flex_reminder, general as flex_general, member as flex_member
from app import line_bot_api # 直接從 app 導入

def _reply_message(reply_token, messages):
    if not isinstance(messages, list): messages = [messages]
    line_bot_api.reply_message(reply_token, messages)

def handle(event):
    """用藥提醒處理器的主入口函式"""
    user_id = event.source.user_id
    if event.type == 'postback':
        handle_postback(event, user_id)
    elif event.type == 'message' and hasattr(event.message, 'text'):
        handle_message(event, user_id)

def handle_postback(event, user_id):
    """處理用藥提醒流程中的 Postback 事件"""
    data = parse_qs(unquote(event.postback.data))
    action = data.get('action', [None])[0]
    reply_token = event.reply_token

    if action == 'confirm_delete_reminder':
        reminder_id = data.get('reminder_id', [None])[0]
        _reply_message(reply_token, flex_general.create_simple_confirmation(
            alt_text="確認刪除提醒", title="⚠️ 確定要刪除？", text="您確定要刪除這筆用藥提醒嗎？",
            confirm_label="是，刪除", confirm_data=f"action=execute_delete_reminder&reminder_id={reminder_id}"
        ))

    elif action == 'execute_delete_reminder':
        reminder_id = int(data.get('reminder_id', [0])[0])
        if reminder_service.ReminderService.delete_reminder(reminder_id, user_id) > 0:
            _reply_message(reply_token, TextSendMessage(text="✅ 已成功刪除該筆用藥提醒。"))
        else:
            _reply_message(reply_token, TextSendMessage(text="❌ 操作失敗，找不到提醒或權限不足。"))

    # 處理其他 postback 動作
    elif action == 'add_member_profile':
        UserService.save_user_simple_state(user_id, "awaiting_new_member_name")
        _reply_message(reply_token, TextSendMessage(text="請輸入新提醒對象的名稱（例如：媽媽、爸爸、奶奶等）："))
    
    elif action == 'rename_member_profile':
        member_id = data.get('member_id', [None])[0]
        if member_id:
            UserService.save_user_simple_state(user_id, f"rename_member_profile:{member_id}")
            _reply_message(reply_token, TextSendMessage(text="請輸入新的名稱："))
    
    elif action == 'delete_member_profile_confirm':
        member_id = data.get('member_id', [None])[0]
        if member_id:
            _reply_message(reply_token, flex_general.create_simple_confirmation(
                alt_text="確認刪除對象", title="⚠️ 確定要刪除？", text="刪除提醒對象會同時刪除該對象的所有提醒記錄，此操作無法復原。",
                confirm_label="是，刪除", confirm_data=f"action=execute_delete_member_profile&member_id={member_id}"
            ))
    
    elif action == 'execute_delete_member_profile':
        member_id = int(data.get('member_id', [0])[0])
        if reminder_service.ReminderService.delete_member_profile(member_id, user_id):
            _reply_message(reply_token, TextSendMessage(text="✅ 已成功刪除該提醒對象及其所有提醒。"))
        else:
            _reply_message(reply_token, TextSendMessage(text="❌ 刪除失敗，找不到對象或權限不足。"))
    
    elif action == 'view_reminders_page':
        member_name = data.get('member', [None])[0]
        page = int(data.get('page', [1])[0])
        if member_name:
            show_member_reminders(user_id, member_name, reply_token, page)
    
    elif action == 'delete_reminder':
        # 處理刪除提醒的請求 - 顯示確認對話框
        reminder_id = data.get('reminder_id', [None])[0]
        if reminder_id:
            _reply_message(reply_token, flex_general.create_simple_confirmation(
                alt_text="確認刪除提醒", title="⚠️ 確定要刪除？", text="您確定要刪除這筆用藥提醒嗎？此操作無法復原。",
                confirm_label="是，刪除", confirm_data=f"action=execute_delete_reminder&reminder_id={reminder_id}"
            ))
        else:
            _reply_message(reply_token, TextSendMessage(text="❌ 無法識別要刪除的提醒，請重試。"))
    
    elif action == 'clear_reminders_for_member':
        # 處理清空成員提醒的請求 - 顯示確認對話框
        member_id = data.get('member_id', [None])[0]
        if member_id:
            # 獲取成員資訊以顯示成員名稱
            try:
                from app.utils.db import DB
                member_info = DB.get_member_by_id(int(member_id))
                member_name = member_info['member'] if member_info else '未知成員'
                
                _reply_message(reply_token, flex_general.create_simple_confirmation(
                    alt_text="確認清空提醒", 
                    title="⚠️ 確定要清空所有提醒？", 
                    text=f"您確定要清空「{member_name}」的所有用藥提醒嗎？此操作將刪除該成員的所有提醒記錄，無法復原。",
                    confirm_label="是，清空", 
                    confirm_data=f"action=execute_clear_reminders&member_id={member_id}"
                ))
            except Exception as e:
                current_app.logger.error(f"獲取成員資訊失敗: {e}")
                _reply_message(reply_token, TextSendMessage(text="❌ 無法獲取成員資訊，請重試。"))
        else:
            _reply_message(reply_token, TextSendMessage(text="❌ 無法識別要清空提醒的成員，請重試。"))
    
    elif action == 'execute_clear_reminders':
        # 執行清空成員提醒
        member_id = data.get('member_id', [None])[0]
        if member_id:
            try:
                member_name, deleted_count = reminder_service.ReminderService.clear_reminders_for_member(user_id, int(member_id))
                if deleted_count > 0:
                    _reply_message(reply_token, TextSendMessage(text=f"✅ 已成功清空「{member_name}」的 {deleted_count} 筆用藥提醒。"))
                else:
                    _reply_message(reply_token, TextSendMessage(text=f"「{member_name}」沒有任何提醒需要清空。"))
            except ValueError as e:
                _reply_message(reply_token, TextSendMessage(text=f"❌ {str(e)}"))
            except Exception as e:
                current_app.logger.error(f"清空成員提醒失敗: {e}")
                _reply_message(reply_token, TextSendMessage(text="❌ 清空提醒時發生錯誤，請稍後再試。"))
        else:
            _reply_message(reply_token, TextSendMessage(text="❌ 無法識別要清空提醒的成員，請重試。"))
    
    elif action == 'cancel_task':
        # 處理取消操作
        _reply_message(reply_token, TextSendMessage(text="操作已取消。"))

def handle_message(event, user_id):
    """處理用藥提醒流程中的 Message 事件"""
    if not hasattr(event.message, 'text') or event.message.text is None:
        current_app.logger.warning(f"收到空的文字訊息 - 用戶: {user_id}")
        return
    
    text = event.message.text.strip()
    reply_token = event.reply_token
    state = UserService.get_user_simple_state(user_id)

    # 處理主要的用藥提醒入口
    if text == "用藥提醒":
        current_app.logger.info(f"用戶 {user_id} 點擊了用藥提醒")
        # 顯示用藥提醒管理選單
        flex_message = flex_reminder.create_reminder_management_menu()
        _reply_message(reply_token, flex_message)
        return
    
    # 處理子選單選項
    elif text == "新增/查詢提醒":
        show_member_selection_for_reminder(user_id, reply_token)
        return
    
    elif text == "管理提醒對象":
        show_member_management(user_id, reply_token)
        return
    
    elif text == "刪除提醒對象":
        show_member_deletion_menu(user_id, reply_token)
        return
    
    elif text == "新增提醒對象":
        UserService.save_user_simple_state(user_id, "awaiting_new_member_name")
        _reply_message(reply_token, TextSendMessage(text="請輸入新提醒對象的名稱（例如：媽媽、爸爸、奶奶等）："))
        return
    
    # 處理狀態相關的輸入
    if state:
        if state == "awaiting_new_member_name":
            create_new_member(user_id, text, reply_token)
            return
        elif state.startswith("rename_member_profile:"):
            member_id = int(state.split(":")[1])
            rename_member(user_id, member_id, text, reply_token)
            return
        elif state == "selecting_member_for_reminder":
            # 用戶選擇了成員名稱
            show_member_reminder_options(user_id, text, reply_token)
            return
    
    # 檢查是否為成員名稱（直接點擊成員查看提醒）
    members = UserService.get_user_members(user_id)
    member_names = [m['member'] for m in members]
    
    if text in member_names:
        show_member_reminders(user_id, text, reply_token)
        return

def show_member_selection_for_reminder(user_id, reply_token):
    """顯示成員選擇選單供新增/查詢提醒"""
    try:
        members = UserService.get_user_members(user_id)
        if not members:
            _reply_message(reply_token, TextSendMessage(text="您還沒有任何提醒對象，請先新增一個提醒對象。"))
            return
        
        UserService.save_user_simple_state(user_id, "selecting_member_for_reminder")
        
        # 創建快速回覆按鈕
        quick_reply_buttons = []
        for member in members:
            quick_reply_buttons.append(
                QuickReplyButton(action=MessageAction(label=member['member'], text=member['member']))
            )
        
        quick_reply = QuickReply(items=quick_reply_buttons)
        message = TextSendMessage(text="請選擇要管理提醒的對象：", quick_reply=quick_reply)
        _reply_message(reply_token, message)
        
    except Exception as e:
        current_app.logger.error(f"顯示成員選擇選單錯誤: {e}")
        _reply_message(reply_token, TextSendMessage(text="載入成員列表時發生錯誤，請稍後再試。"))

def show_member_reminder_options(user_id, member_name, reply_token):
    """顯示特定成員的提醒選項"""
    try:
        members = UserService.get_user_members(user_id)
        target_member = next((m for m in members if m['member'] == member_name), None)
        
        if not target_member:
            _reply_message(reply_token, TextSendMessage(text="找不到該成員，請重新選擇。"))
            return
        
        UserService.delete_user_simple_state(user_id)  # 清除選擇狀態
        
        # 顯示該成員的提醒選項選單
        flex_message = flex_reminder.create_reminder_options_menu(target_member)
        _reply_message(reply_token, flex_message)
        
    except Exception as e:
        current_app.logger.error(f"顯示成員提醒選項錯誤: {e}")
        _reply_message(reply_token, TextSendMessage(text="載入提醒選項時發生錯誤，請稍後再試。"))

def show_member_reminders(user_id, member_name, reply_token, page=1):
    """顯示特定成員的提醒列表"""
    try:
        members = UserService.get_user_members(user_id)
        target_member = next((m for m in members if m['member'] == member_name), None)
        
        if not target_member:
            _reply_message(reply_token, TextSendMessage(text="找不到該成員。"))
            return
        
        # 獲取該成員的提醒列表
        reminders = reminder_service.ReminderService.get_reminders_for_member(user_id, member_name)
        liff_id = current_app.config['LIFF_ID_MANUAL_REMINDER']
        
        # 創建提醒列表輪播
        flex_message = flex_reminder.create_reminder_list_carousel(target_member, reminders, liff_id, page)
        _reply_message(reply_token, flex_message)
        
    except Exception as e:
        current_app.logger.error(f"顯示成員提醒列表錯誤: {e}")
        _reply_message(reply_token, TextSendMessage(text="載入提醒列表時發生錯誤，請稍後再試。"))

def show_member_management(user_id, reply_token):
    """顯示成員管理選單"""
    try:
        members_summary = reminder_service.ReminderService.get_members_with_reminder_summary(user_id)
        liff_id = current_app.config['LIFF_ID_MANUAL_REMINDER']
        
        flex_message = flex_reminder.create_member_management_carousel(members_summary, liff_id)
        _reply_message(reply_token, flex_message)
        
    except Exception as e:
        current_app.logger.error(f"顯示成員管理選單錯誤: {e}")
        _reply_message(reply_token, TextSendMessage(text="載入成員管理選單時發生錯誤，請稍後再試。"))

def show_member_deletion_menu(user_id, reply_token):
    """顯示成員刪除選單"""
    try:
        members = UserService.get_user_members(user_id)
        deletable_members = [m for m in members if m['member'] != '本人']  # 不能刪除本人
        
        if not deletable_members:
            _reply_message(reply_token, TextSendMessage(text="沒有可刪除的提醒對象。"))
            return
        
        # 創建快速回覆按鈕
        quick_reply_buttons = []
        for member in deletable_members:
            quick_reply_buttons.append(
                QuickReplyButton(action=MessageAction(label=f"刪除 {member['member']}", text=f"確認刪除 {member['member']}"))
            )
        
        quick_reply = QuickReply(items=quick_reply_buttons)
        message = TextSendMessage(text="請選擇要刪除的提醒對象：", quick_reply=quick_reply)
        _reply_message(reply_token, message)
        
    except Exception as e:
        current_app.logger.error(f"顯示成員刪除選單錯誤: {e}")
        _reply_message(reply_token, TextSendMessage(text="載入刪除選單時發生錯誤，請稍後再試。"))

def create_new_member(user_id, member_name, reply_token):
    """創建新的提醒對象"""
    try:
        UserService.delete_user_simple_state(user_id)
        
        # 檢查名稱是否已存在
        existing_members = UserService.get_user_members(user_id)
        if any(m['member'] == member_name for m in existing_members):
            _reply_message(reply_token, TextSendMessage(text=f"「{member_name}」已經存在，請使用其他名稱。"))
            return
        
        # 創建新成員
        success = reminder_service.ReminderService.create_member_profile(user_id, member_name)
        
        if success:
            _reply_message(reply_token, TextSendMessage(text=f"✅ 已成功新增提醒對象「{member_name}」！"))
        else:
            _reply_message(reply_token, TextSendMessage(text="❌ 新增提醒對象失敗，請稍後再試。"))
            
    except Exception as e:
        current_app.logger.error(f"創建新成員錯誤: {e}")
        _reply_message(reply_token, TextSendMessage(text="新增提醒對象時發生錯誤，請稍後再試。"))

def rename_member(user_id, member_id, new_name, reply_token):
    """重新命名成員"""
    try:
        UserService.delete_user_simple_state(user_id)
        
        # 根據 member_id 獲取現有成員資訊
        existing_members = UserService.get_user_members(user_id)
        target_member = None
        for member in existing_members:
            if str(member.get('id')) == str(member_id):
                target_member = member
                break
        
        if not target_member:
            _reply_message(reply_token, TextSendMessage(text="❌ 找不到要修改的成員。"))
            return
        
        old_name = target_member['member']
        
        # 檢查新名稱是否已存在
        if any(m['member'] == new_name for m in existing_members):
            _reply_message(reply_token, TextSendMessage(text=f"「{new_name}」已經存在，請使用其他名稱。"))
            return
        
        # 使用 UserService.rename_member 重新命名
        UserService.rename_member(user_id, old_name, new_name)
        _reply_message(reply_token, TextSendMessage(text=f"✅ 已成功將「{old_name}」修改為「{new_name}」！"))
            
    except ValueError as ve:
        current_app.logger.error(f"重新命名成員錯誤: {ve}")
        _reply_message(reply_token, TextSendMessage(text=f"❌ {str(ve)}"))
    except Exception as e:
        current_app.logger.error(f"重新命名成員錯誤: {e}")
        _reply_message(reply_token, TextSendMessage(text="修改名稱時發生錯誤，請稍後再試。"))

def handle_voice_reminder(user_id: str, parsed_data: dict):
    """
    處理從語音解析出的結構化提醒資料。
    """
    try:
        current_app.logger.info(f"[Voice Reminder] 開始處理語音提醒: {parsed_data}")
        
        # 1. 準備提醒資料
        # 使用 get 方法並提供預設值，增加程式碼的穩健性
        drug_name = parsed_data.get('drug_name', '未指定藥物')
        # 支援多種時間欄位格式
        timings = parsed_data.get('time_slots') or parsed_data.get('timing') or []
        frequency = parsed_data.get('frequency_name') or parsed_data.get('frequency') or '每日一次'
        dosage = parsed_data.get('dose_quantity') or parsed_data.get('dosage') or '1顆'
        method = parsed_data.get('method')  # method 可以為 None
        target_member = parsed_data.get('target_member') or parsed_data.get('member', '本人')

        # 2. 獲取或創建目標成員
        from app.services.user_service import UserService
        from app.utils.db import DB
        
        # 獲取用戶的所有成員
        members = UserService.get_user_members(user_id)
        target_member_data = None
        
        # 尋找目標成員
        for member in members:
            if member['member'] == target_member:
                target_member_data = member
                break
        
        if not target_member_data:
            # 如果找不到目標成員，嘗試創建本人成員
            if target_member == '本人':
                UserService.get_or_create_user(user_id)
                target_member_data = DB.get_self_member(user_id)
            
            if not target_member_data:
                line_bot_api.push_message(user_id, TextSendMessage(
                    text=f"找不到成員「{target_member}」，請先新增該成員或使用選單功能。"
                ))
                return

        # 3. 轉換為資料庫格式
        # 處理時間槽
        current_app.logger.info(f"[Voice Reminder] 處理時間槽，timings: {timings}")
        time_slots = {}
        if timings:
            for i, time_str in enumerate(timings):
                if i < 5:  # 最多5個時間槽
                    current_app.logger.info(f"[Voice Reminder] 轉換時間 {i+1}: {time_str}")
                    # 轉換時間格式為 HH:MM:SS
                    converted_time = reminder_service.ReminderService._convert_time_to_db_format(time_str)
                    if converted_time:
                        time_slots[f"time_slot_{i+1}"] = converted_time
                        current_app.logger.info(f"[Voice Reminder] 成功轉換: time_slot_{i+1} = {converted_time}")
                    else:
                        current_app.logger.warning(f"[Voice Reminder] 時間轉換失敗: {time_str}")
        else:
            # 如果沒有指定時間，根據頻率設定預設時間
            current_app.logger.info(f"[Voice Reminder] 沒有指定時間，使用頻率預設時間: {frequency}")
            default_times = _get_default_times_from_frequency(frequency)
            for i, default_time in enumerate(default_times):
                if i < 5:
                    time_slots[f"time_slot_{i+1}"] = default_time
        
        current_app.logger.info(f"[Voice Reminder] 最終時間槽配置: {time_slots}")

        # 處理頻率編碼
        frequency_code = _convert_frequency_to_code(frequency)
        
        reminder_data = {
            'recorder_id': user_id,
            'member': target_member,
            'drug_name': drug_name,
            'dose_quantity': dosage,
            'notes': f"由語音建立: {parsed_data.get('original_text', '語音輸入')}",
            'frequency_name': frequency,
            'frequency_timing_code': method,
            'frequency_count_code': frequency_code,
            **time_slots
        }

        # 4. 建立提醒
        result = DB.create_reminder(reminder_data)
        
        if result:
            # 成功創建提醒
            timing_str = ', '.join(timings) if timings else '預設時間'
            success_message = (
                f"✅ 語音提醒設定成功！\n\n"
                f"💊 藥物：{drug_name}\n"
                f"👥 對象：{target_member}\n"
                f"⏰ 時間：{timing_str}\n"
                f"📅 頻率：{frequency}\n"
                f"📊 劑量：{dosage}"
            )
            if method:
                success_message += f"\n🍽️ 方式：{method}"
            
            line_bot_api.push_message(user_id, TextSendMessage(text=success_message))
            current_app.logger.info(f"[Voice Reminder] 成功建立語音提醒，藥物: {drug_name}, 成員: {target_member}")
        else:
            # 建立失敗
            line_bot_api.push_message(user_id, TextSendMessage(
                text="❌ 建立提醒失敗，請稍後再試或使用選單功能手動新增。"
            ))
            current_app.logger.error(f"[Voice Reminder] 建立語音提醒失敗 - 用戶: {user_id}")
            
    except Exception as e:
        current_app.logger.error(f"[Voice Reminder] 處理語音提醒時發生嚴重錯誤: {e}")
        import traceback
        traceback.print_exc()
        line_bot_api.push_message(user_id, TextSendMessage(
            text="❌ 處理您的語音指令時發生內部錯誤，我們將會盡快修復。"
        ))

def _get_default_times_from_frequency(frequency: str) -> list:
    """根據頻率設定預設時間"""
    if not frequency:  # 處理 None 或空字串
        return ['08:00:00']  # 預設為每日一次
        
    frequency_lower = frequency.lower()
    
    if '一次' in frequency or 'qd' in frequency_lower:
        return ['08:00:00']
    elif '两次' in frequency or '二次' in frequency or 'bid' in frequency_lower:
        return ['08:00:00', '20:00:00']
    elif '三次' in frequency or 'tid' in frequency_lower:
        return ['08:00:00', '14:00:00', '20:00:00']
    elif '四次' in frequency or 'qid' in frequency_lower:
        return ['08:00:00', '12:00:00', '16:00:00', '20:00:00']
    else:
        return ['08:00:00']  # 預設為每日一次

def _convert_frequency_to_code(frequency: str) -> str:
    """轉換頻率為編碼"""
    if not frequency:  # 處理 None 或空字串
        return 'QD'  # 預設為每日一次
        
    frequency_lower = frequency.lower()
    
    if '一次' in frequency or 'qd' in frequency_lower:
        return 'QD'
    elif '两次' in frequency or '二次' in frequency or 'bid' in frequency_lower:
        return 'BID'
    elif '三次' in frequency or 'tid' in frequency_lower:
        return 'TID'
    elif '四次' in frequency or 'qid' in frequency_lower:
        return 'QID'
    elif '需要時' in frequency or 'prn' in frequency_lower:
        return 'PRN'
    elif '睡前' in frequency or 'hs' in frequency_lower:
        return 'HS'
    else:
        return 'QD'  # 預設為每日一次（修正：原本是TID）

# (檔案中原有的其他函式維持不變)
# ...