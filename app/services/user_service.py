# app/services/user_service.py

from ..utils.db import DB
from app import line_bot_api

class UserService:
    """處理使用者、成員和狀態相關的業務邏輯"""

    # --- 複雜狀態管理 (藥單流程) ---
    @staticmethod
    def get_user_complex_state(user_id: str):
        return DB.get_complex_state(user_id)

    @staticmethod
    def set_user_complex_state(user_id: str, state_data: dict):
        """設置用戶複雜狀態，自動確保用戶存在"""
        try:
            # 【核心修復】確保用戶在資料庫中存在
            try:
                user_profile = line_bot_api.get_profile(user_id)
                user_name = user_profile.display_name if user_profile else f"User_{user_id[:8]}"
            except Exception:
                user_name = f"User_{user_id[:8]}"
            
            result = DB.get_or_create_user(user_id, user_name)
            if not result:
                print(f"❌ 無法創建或獲取用戶: {user_id}")
                return False
            
            # 設置狀態
            DB.set_complex_state(user_id, state_data)
            return True
        except Exception as e:
            print(f"❌ 設置用戶狀態失敗: {e}")
            return False

    @staticmethod
    def clear_user_complex_state(user_id: str):
        DB.clear_complex_state(user_id)

    # --- 簡單狀態管理 (通用) ---
    @staticmethod
    def get_user_simple_state(user_id: str):
        return DB.get_simple_state(user_id)

    @staticmethod
    def save_user_simple_state(user_id: str, state: str, minutes: int = 10):
        DB.save_simple_state(user_id, state, minutes_to_expire=minutes)

    @staticmethod
    def delete_user_simple_state(user_id: str):
        DB.delete_simple_state(user_id)
        
    # --- 使用者與成員 ---
    @staticmethod
    def get_or_create_user(user_id: str):
        """如果使用者不存在，則建立使用者並回傳 display name"""
        try:
            profile = line_bot_api.get_profile(user_id)
            user_name = profile.display_name
        except Exception:
            user_name = "使用者" # 預設名稱
        
        DB.get_or_create_user(user_id, user_name)
        return user_name

    @staticmethod
    def get_user_members(user_id: str):
        """獲取指定使用者的所有成員列表"""
        return DB.get_members(user_id)

    @staticmethod
    def add_new_member(user_id: str, member_name: str):
        """為使用者新增一個手動建立的成員"""
        existing_members = DB.get_members(user_id)
        if any(m['member'] == member_name for m in existing_members):
            raise ValueError(f"成員「{member_name}」已存在，請換一個名稱。")
        
        DB.add_member(user_id, member_name)
        return True

    @staticmethod
    def rename_member(user_id: str, old_name: str, new_name: str):
        """
        【邏輯強化】修改成員名稱，並同步更新所有關聯表。
        """
        existing_members = DB.get_members(user_id)
        if any(m['member'] == new_name and m['member'] != old_name for m in existing_members):
            raise ValueError(f"名稱「{new_name}」已存在，請換一個名稱。")

        # 【邏輯強化】呼叫已強化的 DB 層函式
        updated_rows = DB.rename_member(user_id, old_name, new_name)
        if updated_rows == 0:
            raise ValueError("找不到要更新的成員，或更新失敗。")
        
        return True

    @staticmethod
    def get_deletable_members(user_id: str):
        """【新增】獲取可供刪除的自建成員列表"""
        return DB.get_deletable_members(user_id)

    @staticmethod
    def delete_member(user_id: str, member_name: str):
        """
        刪除一個手動建立的成員及其相關提醒和藥歷記錄。
        此函式現在只處理刪除操作，權限檢查由 handler 層決定。
        """
        if member_name == "本人":
            raise ValueError("無法刪除「本人」。")
        
        # 1. 刪除該成員的所有藥歷記錄
        records = DB.get_records_by_member(user_id, member_name)
        for record in records:
            if record.get('mm_id'):
                DB.delete_record_by_mm_id(user_id, record.get('mm_id'))
        
        # 2. 刪除該成員的所有提醒
        DB.delete_reminders_for_member(user_id, member_name)
        
        # 3. 刪除成員本身
        deleted_rows = DB.delete_member_by_name(user_id, member_name)
        if deleted_rows == 0:
            raise ValueError("找不到要刪除的成員，或刪除失敗。")
        
        return True