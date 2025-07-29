# --- 請用此最終、正確的版本【完整覆蓋】您的 app/routes/handlers/family_handler.py ---

from flask import current_app
from linebot.models import TextSendMessage, QuickReply, QuickReplyButton, MessageAction
from urllib.parse import parse_qs, unquote, quote

from app.services.user_service import UserService
from app.services import family_service
from app.utils.flex import family as flex_family
from app.utils.db import DB

def _reply_message(reply_token, messages):
    from app import line_bot_api
    if not isinstance(messages, list): messages = [messages]
    line_bot_api.reply_message(reply_token, messages)

def handle(event):
    """家人綁定處理器的主入口函式"""
    user_id = event.source.user_id
    if event.type == 'postback':
        handle_postback(event, user_id)
    elif event.type == 'message' and hasattr(event.message, 'text'):
        handle_message(event, user_id)

def handle_postback(event, user_id):
    """處理家人綁定流程中的 Postback 事件"""
    data_str = event.postback.data
    reply_token = event.reply_token
    
    # 優先處理 relation:xxx 格式
    if data_str.startswith('relation:'):
        relation = data_str.split(':', 1)[1]
        state_str = UserService.get_user_simple_state(user_id)
        
        if not state_str or not state_str.startswith("relation_select:"):
            _reply_message(reply_token, TextSendMessage(text="操作已過期或無效，請重新開始。"))
            return

        inviter_id = state_str.split(':', 1)[1]
        if relation == 'other':
            UserService.save_user_simple_state(user_id, f"custom_relation:{inviter_id}")
            _reply_message(reply_token, TextSendMessage(
                text="請輸入您想自訂的稱謂：\n\n❌ 輸入「取消」可結束操作",
                quick_reply=QuickReply(items=[QuickReplyButton(action=MessageAction(label="取消", text="取消"))])
            ))
        else:
            status, message = family_service.FamilyService.complete_binding(user_id, inviter_id, relation)
            _reply_message(reply_token, TextSendMessage(text=message))
        return

    # 處理 action=xxx 格式
    data = parse_qs(unquote(data_str))
    action = data.get('action', [None])[0]

    if action == 'gen_code':
        code = family_service.FamilyService.generate_binding_code(user_id)
        # 修正呼叫方式，只傳遞 code 這一個參數
        _reply_message(reply_token, flex_family.create_invite_code_flex(code))

    elif action == 'confirm_bind':
        code = data.get('code', [None])[0]
        inviter_id = DB.get_inviter_by_code(code)
        if not inviter_id:
            _reply_message(reply_token, TextSendMessage(text="抱歉，此邀請碼已失效，請您的家人重新產生。"))
            return
        
        UserService.save_user_simple_state(user_id, f"relation_select:{inviter_id}")
        _reply_message(reply_token, TextSendMessage(
            text="好的，請選擇您在家人列表中的稱謂：",
            quick_reply=flex_family.create_relation_quick_reply()
        ))

    elif action == 'manage_family':
        family_list = family_service.FamilyService.get_family_list(user_id)
        _reply_message(reply_token, flex_family.create_family_manager_carousel(family_list))

    elif action == 'query_family':
        family_list = family_service.FamilyService.get_family_list(user_id)
        _reply_message(reply_token, flex_family.create_family_manager_carousel(family_list))

    elif action == 'cancel_bind':
        UserService.delete_user_simple_state(user_id)
        _reply_message(reply_token, TextSendMessage(text="操作已取消。"))

    elif action == 'edit_nickname':
        nickname = data.get('nickname', [None])[0]
        if nickname:
            UserService.save_user_simple_state(user_id, f"edit_nickname:{nickname}")
            _reply_message(reply_token, TextSendMessage(
                text=f"請輸入「{nickname}」的新稱謂：\n\n❌ 輸入「取消」可結束操作",
                quick_reply=QuickReply(items=[QuickReplyButton(action=MessageAction(label="取消", text="取消"))])
            ))

    elif action == 'delete_binding':
        nickname = data.get('nickname', [None])[0]
        if nickname:
            family_list = family_service.FamilyService.get_family_list(user_id)
            target_member = next((m for m in family_list if m['relation_type'] == nickname), None)
            
            if target_member:
                recipient_id = target_member['recipient_line_id']
                status, message = family_service.FamilyService.unbind_family_member(user_id, recipient_id, nickname)
                _reply_message(reply_token, TextSendMessage(text=message))
            else:
                _reply_message(reply_token, TextSendMessage(text="❌ 找不到該家人，可能已被刪除。"))

def handle_message(event, user_id):
    """處理家人綁定流程中的 Message 事件"""
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
    state_str = UserService.get_user_simple_state(user_id)

    # 處理狀態相關的輸入
    if state_str:
        if text == '取消':
            UserService.delete_user_simple_state(user_id)
            _reply_message(reply_token, TextSendMessage(text="操作已取消。"))
            return

        if state_str.startswith("custom_relation:"):
            inviter_id = state_str.split(':', 1)[1]
            status, message = family_service.FamilyService.complete_binding(user_id, inviter_id, text)
            _reply_message(reply_token, TextSendMessage(text=message))
            return
            
        elif state_str.startswith("edit_nickname:"):
            old_name = state_str.split(':', 1)[1]
            try:
                UserService.rename_member(user_id, old_name, text)
                UserService.delete_user_simple_state(user_id)
                _reply_message(reply_token, TextSendMessage(text=f"✅ 已成功將「{old_name}」的稱謂修改為「{text}」。"))
            except ValueError as e:
                _reply_message(reply_token, TextSendMessage(text=f"❌ 修改失敗：{e}"))
            return
    
    # 處理頂層指令
    if text == "家人綁定與管理":
        _reply_message(reply_token, flex_family.create_family_binding_menu())
        return
        
    # 處理綁定碼指令
    if text.startswith("綁定"):
        code = text.replace("綁定", "").strip()
        if code:
            status, data = family_service.FamilyService.start_binding_process(user_id, code)
            if status == 'error':
                _reply_message(reply_token, TextSendMessage(text=data))
            elif status == 'confirmation_needed':
                _reply_message(reply_token, [
                    TextSendMessage(text="📌 您即將進行家人綁定，為了保障您的帳戶安全，請確認是否要與對方建立綁定關係。"),
                    flex_family.create_binding_confirmation_flex(data['code'])
                ])
        return