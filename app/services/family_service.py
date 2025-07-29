# app/services/family_service.py

import random
import string
from ..utils.db import DB
from .user_service import UserService
from app import line_bot_api
from linebot.models import TextSendMessage

class FamilyService:
    """處理家人綁定相關的所有業務邏輯"""

    @staticmethod
    def generate_binding_code(user_id: str) -> str:
        """產生一個 6 位數的邀請碼並儲存到 state"""
        code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
        # 邀請碼有效期限 10 分鐘
        UserService.save_user_simple_state(user_id, code, minutes=10)
        return code

    @staticmethod
    def start_binding_process(user_id: str, code: str):
        """
        【邏輯強化】處理使用者輸入的綁定碼，進行驗證並準備下一步。
        返回 (狀態, 訊息或資料) 元組。
        """
        inviter_id = DB.get_inviter_by_code(code)

        if not inviter_id:
            return "error", "邀請碼無效或已過期。"
        if inviter_id == user_id:
            return "error", "您不能綁定自己喔！"
        
        # 【優化】檢查是否已綁定，並提供更詳細的錯誤訊息
        if DB.check_binding_exists(user_id, inviter_id):
            binding_info = DB.get_existing_binding_info(user_id, inviter_id)
            if binding_info:
                if binding_info['recorder_id'] == inviter_id:
                    relation_name = binding_info['relation_type']
                    error_msg = f"🔗 您已經與此使用者綁定過了！\n\n目前綁定關係：您在對方的家人列表中是「{relation_name}」\n\n💡 如需重新綁定，請先到「家人綁定與管理」解除現有綁定關係。"
                else:
                    error_msg = f"🔗 您已經與此使用者綁定過了！\n\n目前綁定關係：對方在您的家人列表中是「{binding_info['relation_type']}」\n\n💡 如需重新綁定，請先到「家人綁定與管理」解除現有綁定關係。"
            else:
                error_msg = "🔗 您已經與此使用者綁定過了！\n\n💡 如需重新綁定，請先解除現有綁定關係。"
            return "error", error_msg

        # 【優化】返回待確認狀態，而不是直接進入下一步
        return "confirmation_needed", {"code": code}

    @staticmethod
    def complete_binding(binder_id: str, inviter_id: str, relation_type: str):
        """
        完成綁定流程，將關係寫入資料庫並通知邀請者。
        返回 (狀態, 訊息) 元組。
        """
        # 再次檢查是否已綁定 (防止在流程中被其他人搶先綁定)
        if DB.check_binding_exists(binder_id, inviter_id):
            UserService.delete_user_simple_state(binder_id)
            return "error", "❌ 綁定失敗：您與此使用者已經綁定過了。"

        try:
            binder_profile = line_bot_api.get_profile(binder_id)
            binder_name = binder_profile.display_name
        except Exception:
            binder_name = "新家人"

        # 【邏輯強化】使用新的 DB 函式，同步建立綁定關係和成員
        if not DB.add_family_binding(inviter_id, binder_id, binder_name, relation_type):
            UserService.delete_user_simple_state(binder_id)
            return "error", "❌ 綁定失敗：無法建立家人關係。"
        
        # 确保被绑定者也有用户记录和"本人"成员
        UserService.get_or_create_user(binder_id)

        UserService.delete_user_simple_state(binder_id)

        # 獲取邀請者的姓名
        try:
            inviter_profile = line_bot_api.get_profile(inviter_id)
            inviter_name = inviter_profile.display_name
        except Exception:
            inviter_name = "家人"

        # 使用 PushMessage 通知邀請者
        try:
            inviter_notification = f"🎉 家人綁定成功！\n\n'{binder_name}' 已成功與您綁定為「{relation_type}」！\n\n現在您可以為他們設定用藥提醒或管理藥歷了。"
            line_bot_api.push_message(inviter_id, TextSendMessage(text=inviter_notification))
            
        except Exception as e:
            print(f"發送綁定成功通知給邀請者失敗: {e}")

        # 綁定者的詳細成功消息（用於回覆）
        binder_reply_message = f"🎉 家人綁定成功！\n\n您已成功與 '{inviter_name}' 建立家人關係，您在對方的家人列表中是「{relation_type}」。\n\n對方現在可以為您設定用藥提醒與管理藥歷了。"
        
        return "success", binder_reply_message

    @staticmethod
    def get_family_list(user_id: str):
        """獲取使用者的家人列表（从 invitation_recipients 表获取真正的绑定关系）"""
        return DB.get_family_bindings(user_id)

    @staticmethod
    def unbind_family_member(user_id: str, recipient_id: str, member_name: str):
        """解除與指定家人的綁定關係，並刪除所有相關資料"""
        try:
            # 1. 删除用药提醒
            reminders_deleted = DB.delete_reminders_for_member(user_id, member_name)
            
            # 2. 删除药历记录
            records = DB.get_records_by_member(user_id, member_name)
            records_deleted = 0
            for record in records:
                if record.get('mm_id'):
                    DB.delete_record_by_mm_id(user_id, record.get('mm_id'))
                    records_deleted += 1
            
            # 3. 删除绑定关系
            binding_deleted = DB.delete_family_binding(user_id, recipient_id)
            
            # 4. 删除成员记录
            member_deleted = DB.delete_member_by_name(user_id, member_name)

            # 建立刪除報告
            deleted_items = []
            if reminders_deleted > 0: deleted_items.append(f"{reminders_deleted}筆用藥提醒")
            if records_deleted > 0: deleted_items.append(f"{records_deleted}筆藥歷記錄")
            if binding_deleted > 0: deleted_items.append("家人綁定關係")
            if member_deleted > 0: deleted_items.append("成員資料")
            
            if deleted_items:
                items_text = "、".join(deleted_items)
                return "success", f"✅ 已成功解除與「{member_name}」的綁定關係。\n\n🗑️ 已同步刪除：{items_text}。"
            else:
                return "success", f"✅ 已成功解除與「{member_name}」的綁定關係，沒有其他相關資料需要刪除。"
                
        except Exception as e:
            print(f"解除家人綁定時發生錯誤: {e}")
            return "error", f"❌ 解除綁定失敗：{str(e)}"