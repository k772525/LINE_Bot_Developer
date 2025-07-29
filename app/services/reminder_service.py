# app/services/reminder_service.py

import schedule
import time
import traceback
from datetime import datetime
from ..utils.db import DB
from app import line_bot_api
from linebot.models import TextSendMessage

class ReminderService:
    """處理用藥提醒的建立、查詢、刪除與排程發送"""

    @staticmethod
    def create_or_update_reminder(user_id: str, member_id: str = None, form_data: dict = None, reminder_id: int = None):
        """
        建立或更新一筆用藥提醒。
        這個函式將處理來自 LIFF 表單的資料。
        """
        if form_data is None: form_data = {}
            
        reminder_data = {'recorder_id': user_id, **form_data}
        
        if reminder_id:
            existing_reminder = DB.get_reminder_by_id(reminder_id)
            if existing_reminder:
                reminder_data['member'] = existing_reminder['member']
                # 確保藥物名稱不會被清空
                if 'drug_name' not in reminder_data or not reminder_data['drug_name']:
                    reminder_data['drug_name'] = existing_reminder['drug_name']
        elif member_id:
            member_info = DB.get_member_by_id(member_id)
            if member_info:
                reminder_data['member'] = member_info['member']
            else:
                # 如果找不到成員，回傳錯誤
                return None
        
        # 確保 member 欄位存在
        if 'member' not in reminder_data:
            return None
        
        return DB.create_reminder(reminder_data)

    @staticmethod
    def create_reminder_from_voice(user_id: str, drug_name: str, timings: list, frequency: str, dosage: str, method: str):
        """處理來自語音的用藥提醒"""
        # 1. 確保「本人」成員存在
        member = DB.get_self_member(user_id)
        if not member:
            from .user_service import UserService
            UserService.get_or_create_user(user_id)
            member = DB.get_self_member(user_id)
            if not member:
                return None # 如果還是找不到，則放棄

        # 2. 轉換為資料庫格式
        time_slots = {}
        if timings:
            for i, time_str in enumerate(timings):
                if i < 5:  # 最多5個時間槽
                    # 轉換時間格式為 HH:MM:SS
                    converted_time = ReminderService._convert_time_to_db_format(time_str)
                    if converted_time:
                        time_slots[f"time_slot_{i+1}"] = converted_time

        reminder_data = {
            'recorder_id': user_id,
            'member': '本人',
            'drug_name': drug_name,
            'dose_quantity': dosage,
            'notes': f"由語音建立",
            'frequency_name': frequency,
            'frequency_timing_code': method,
            **time_slots
        }

        # 3. 建立提醒
        return DB.create_reminder(reminder_data)

    @staticmethod
    def _convert_time_to_db_format(time_str: str) -> str:
        """
        將各種時間格式轉換為資料庫需要的 HH:MM:SS 格式
        
        Args:
            time_str: 時間字串，如 "早上8點一刻", "08:15", "14:30" 等
            
        Returns:
            格式化的時間字串 "HH:MM:SS"，失敗時返回 None
        """
        import re
        from datetime import datetime, time
        from flask import current_app
        
        if not time_str:
            return None
        
        try:
            # 清理輸入
            time_str = str(time_str).strip()
            
            # 情況1: 已經是 HH:MM 或 HH:MM:SS 格式
            if re.match(r'^\d{1,2}:\d{2}(:\d{2})?$', time_str):
                parts = time_str.split(':')
                hour = int(parts[0])
                minute = int(parts[1])
                second = int(parts[2]) if len(parts) > 2 else 0
                
                # 驗證時間有效性
                if 0 <= hour <= 23 and 0 <= minute <= 59 and 0 <= second <= 59:
                    return f"{hour:02d}:{minute:02d}:{second:02d}"
            
            # 情況2: 中文時間描述
            # 處理「一刻」、「半」、「三刻」等
            time_str = time_str.replace('一刻', '15分').replace('半', '30分').replace('三刻', '45分')
            
            # 提取小時
            hour = None
            minute = 0
            
            # 檢查是否有上午/下午標識
            is_pm = '下午' in time_str or '午後' in time_str
            is_am = '上午' in time_str or '早上' in time_str or '早晨' in time_str or '清晨' in time_str
            
            # 提取數字小時
            hour_match = re.search(r'(\d{1,2})點', time_str)
            if hour_match:
                hour = int(hour_match.group(1))
                
                # 處理12小時制轉24小時制
                if is_pm and hour != 12:  # 下午但不是12點，需要加12
                    hour += 12
                elif is_am and hour == 12:  # 上午12點應該是0點
                    hour = 0
                # 如果是下午12點或上午非12點，保持原值
                
            else:
                # 時段對應 - 這些是24小時制的預設值
                time_periods = {
                    '早上': 8, '早晨': 8, '清晨': 7,
                    '上午': 10, '中午': 12, '正午': 12,
                    '下午': 14, '午後': 15, '傍晚': 17,
                    '晚上': 18, '夜晚': 20, '睡前': 22,
                    '飯前': 7, '餐前': 7, '飯後': 8, '餐後': 8
                }
                
                for period, default_hour in time_periods.items():
                    if period in time_str:
                        hour = default_hour
                        break
            
            # 提取分鐘
            minute_match = re.search(r'(\d{1,2})分', time_str)
            if minute_match:
                minute = int(minute_match.group(1))
            
            # 如果沒有找到小時，使用預設值
            if hour is None:
                hour = 8  # 預設早上8點
            
            # 驗證並格式化
            if 0 <= hour <= 23 and 0 <= minute <= 59:
                return f"{hour:02d}:{minute:02d}:00"
            
            current_app.logger.warning(f"無效的時間值: hour={hour}, minute={minute}")
            return None
            
        except Exception as e:
            current_app.logger.error(f"時間格式轉換錯誤: {time_str} -> {e}")
            return None

    @staticmethod
    def get_reminders_for_member(user_id: str, member_name: str):
        """獲取特定成員的所有提醒"""
        return DB.get_reminders(user_id, member_name)
    
    @staticmethod
    def get_members_with_reminder_summary(user_id: str):
        """獲取用戶的所有成員及其提醒摘要資訊"""
        try:
            from app.services.user_service import UserService
            
            # 獲取用戶的所有成員
            members = UserService.get_user_members(user_id)
            
            # 為每個成員添加提醒摘要資訊
            members_summary = []
            for member in members:
                member_name = member['member']
                
                # 獲取該成員的提醒列表
                reminders = DB.get_reminders(user_id, member_name)
                
                # 計算提醒統計
                total_reminders = len(reminders)
                active_reminders = len([r for r in reminders if r.get('status') != 'inactive'])
                
                # 生成提醒預覽文字
                drug_names = [r.get('drug_name', '未命名藥品') for r in reminders[:2]]
                if len(reminders) > 2:
                    drug_names.append(f"等{len(reminders)}種")
                reminders_preview = "、".join(drug_names) if drug_names else "尚無提醒"
                
                # 創建摘要資訊
                member_summary = {
                    'id': member.get('id'),
                    'member': member_name,
                    'reminders_count': total_reminders,  # 修正欄位名稱以符合 Flex 模板期望
                    'total_reminders': total_reminders,  # 保留舊欄位名稱以保持向後相容
                    'active_reminders': active_reminders,
                    'reminders_preview': reminders_preview,  # 新增預覽文字
                    'recent_reminders': reminders[:3] if reminders else []  # 最近3筆提醒
                }
                
                members_summary.append(member_summary)
            
            return members_summary
            
        except Exception as e:
            current_app.logger.error(f"獲取成員提醒摘要失敗: {e}")
            return []

    @staticmethod
    def get_reminders_summary_for_management(user_id: str):
        """
        【新增】獲取用於管理介面的提醒摘要資訊。
        """
        members = DB.get_members(user_id)
        for member in members:
            reminders = DB.get_reminders(user_id, member['member'])
            member['reminders_count'] = len(reminders)
            drug_names = [r.get('drug_name', '未命名藥品') for r in reminders[:2]]
            if len(reminders) > 2:
                drug_names.append(f"等{len(reminders)}種")
            member['reminders_preview'] = "、".join(drug_names) if drug_names else "尚無提醒"
        return members

    @staticmethod
    def get_reminder_details(reminder_id: int, user_id: str):
        """獲取單筆提醒的詳細資訊，並檢查所有權"""
        if not DB.check_reminder_ownership(reminder_id, user_id):
            return None
        return DB.get_reminder_by_id(reminder_id)

    @staticmethod
    def delete_reminder(reminder_id: int, user_id: str):
        """刪除單筆提醒，並檢查所有權"""
        if not DB.check_reminder_ownership(reminder_id, user_id):
            return 0
        return DB.delete_reminder(reminder_id)

    @staticmethod
    def clear_reminders_for_member(user_id: str, member_id: int):
        """清空特定成員的所有提醒，並返回成員名稱"""
        member = DB.get_member_by_id(member_id)
        if not member or member['recorder_id'] != user_id:
             raise ValueError("找不到該提醒對象或權限不足。")
        
        deleted_count = DB.delete_reminders_for_member(user_id, member['member'])
        return member['member'], deleted_count

    @staticmethod
    def get_prescription_for_liff(mm_id: int):
        """為藥單提醒 LIFF 頁面準備資料"""
        return DB.get_prescription_for_liff(mm_id)

    @staticmethod
    def create_reminders_batch(reminders_data: list, user_id: str):
        """批量建立來自藥單的提醒"""
        for r in reminders_data:
            if r.get('recorder_id') != user_id:
                raise PermissionError("沒有權限建立不屬於自己的提醒")
        return DB.create_reminders_batch(reminders_data)

# --- 背景排程器相關函式 ---

def check_and_send_reminders(app):
    """使用 app_context 並呼叫 send_reminder_logic"""
    with app.app_context():
        try:
            from app import line_bot_api as bot_api
            import pytz
            
            # 使用台北時區時間
            taipei_tz = pytz.timezone('Asia/Taipei')
            current_time_taipei = datetime.now(taipei_tz)
            current_time_str = current_time_taipei.strftime("%H:%M")
            
            # 添加更詳細的日誌
            print(f"[{current_time_str}] 開始檢查提醒（台北時間）...")
            print(f"UTC時間: {datetime.utcnow().strftime('%H:%M')}")
            
            # 檢查 bot_api 是否正確初始化
            if bot_api is None:
                print(f"[{current_time_str}] 錯誤：line_bot_api 未正確初始化")
                return
            
            reminders = DB.get_reminders_for_scheduler(current_time_str)
            print(f"[{current_time_str}] 找到 {len(reminders)} 筆到期提醒")
            
            if reminders:
                app.logger.info(f"[{current_time_str}] 找到 {len(reminders)} 筆到期提醒，準備發送...")
                for i, r in enumerate(reminders, 1):
                    print(f"[{current_time_str}] 處理第 {i} 筆提醒...")
                    send_reminder_logic(r, current_time_str, bot_api)
            else:
                print(f"[{current_time_str}] 沒有到期的提醒")
                
        except Exception as e:
            error_msg = f"排程器執行時發生錯誤： {str(e)}"
            print(error_msg)
            app.logger.error(error_msg)
            traceback.print_exc()

def send_reminder_logic(reminder_data: dict, current_time_str: str, bot_api=None):
    """
    發送提醒的核心邏輯。
    採用更嚴謹的判斷，確保只通知設定者與被設定者。
    """
    api = bot_api or line_bot_api
    if api is None:
        print(f"    - 錯誤：line_bot_api 未正確初始化")
        return
    
    # 調試資訊
    print(f"    - 調試：reminder_data keys: {list(reminder_data.keys())}")
    print(f"    - 調試：recorder_id: '{reminder_data.get('recorder_id')}'")
    print(f"    - 調試：bound_recipient_line_id: '{reminder_data.get('bound_recipient_line_id')}')")
    
    recorder_id = reminder_data.get('recorder_id')
    member_name = reminder_data.get('member')
    drug_name = reminder_data.get('drug_name', '未命名藥品')
    recipient_line_id = reminder_data.get('bound_recipient_line_id')

    party_msg_text = f"⏰ 用藥提醒！\n\nHi {member_name}，該吃藥囉！\n藥品：{drug_name}\n時間：{current_time_str}"
    creator_msg_text = f"🔔 您為「{member_name}」設定的提醒已發送。\n藥品：{drug_name}\n時間：{current_time_str}"
    
    # 情況一: 有綁定關係的家人提醒 (且不是幫自己設)
    if recipient_line_id and recipient_line_id != recorder_id:
        print(f"  -> 雙向通知: 設定者[{recorder_id[:6]}..] -> 家人[{recipient_line_id[:6]}..] ({member_name})")
        try:
            api.push_message(recipient_line_id, TextSendMessage(text=party_msg_text))
            print(f"    - ✅ 成功發送 [家人提醒] 給 {recipient_line_id}")
        except Exception as e:
            print(f"    - ❌ 發送 [家人提醒] 給 {recipient_line_id} 失敗: {e}")
        try:
            api.push_message(recorder_id, TextSendMessage(text=creator_msg_text))
            print(f"    - ✅ 成功發送 [備忘提醒] 給 {recorder_id}")
        except Exception as e:
            print(f"    - ❌ 發送 [備忘提醒] 給 {recorder_id} 失敗: {e}")
    # 情況二: 幫自己設定的提醒，或幫一個未綁定的本地 Profile 設定
    else:
        print(f"  -> 單向通知: 設定者[{recorder_id[:6]}..] -> 自己 ({member_name})")
        try:
            api.push_message(recorder_id, TextSendMessage(text=party_msg_text))
            print(f"    - ✅ 成功發送 [個人提醒] 給 {recorder_id}")
        except Exception as e:
            print(f"    - ❌ 發送 [個人提醒] 給 {recorder_id} 失敗: {e}")
            # 詳細錯誤資訊
            if hasattr(e, 'status_code'):
                print(f"      狀態碼: {e.status_code}")
                if e.status_code == 400:
                    print(f"      ⚠️  可能原因: 用戶已封鎖機器人或刪除好友關係")
                elif e.status_code == 401:
                    print(f"      ⚠️  可能原因: LINE Channel Access Token 無效")
                elif e.status_code == 403:
                    print(f"      ⚠️  可能原因: 沒有權限發送訊息給此用戶")
            if hasattr(e, 'error_response'):
                print(f"      錯誤回應: {e.error_response}")
            # 檢查 user_id 格式
            if not recorder_id or not recorder_id.startswith('U'):
                print(f"      ⚠️  可能的問題: user_id 格式不正確 '{recorder_id}'")

def run_scheduler(app):
    """啟動背景排程的函式"""
    print("背景排程器已啟動，每分鐘檢查一次。")
    print(f"當前時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # 添加更詳細的日誌
    schedule.every().minute.at(":00").do(check_and_send_reminders, app=app)
    
    # 立即執行一次檢查（用於測試）
    print("執行初始提醒檢查...")
    check_and_send_reminders(app)
    
    while True:
        schedule.run_pending()
        time.sleep(1)