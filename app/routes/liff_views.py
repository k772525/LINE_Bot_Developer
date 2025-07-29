# --- START OF FILE: app/routes/liff_views.py (完整修正版) ---

from flask import Blueprint, request, jsonify, render_template, current_app
import requests
import base64
import traceback

# 從服務層導入邏輯
from ..services.user_service import UserService
from ..services import prescription_service, reminder_service
from ..utils.helpers import convert_minguo_to_gregorian

# 導入數據庫操作類別
from ..utils.db import DB

# 移除 start_loading_animation 函數，現在在 prescription_handler 中處理

# 建立一個名為 'liff' 的藍圖
liff_bp = Blueprint('liff', __name__)

def _verify_line_id_token(id_token: str) -> str | None:
    """驗證 LINE ID Token 並返回 user_id"""
    if not id_token:
        return None
    try:
        import os
        env_value = os.environ.get('LIFF_CHANNEL_ID')
        config_value = current_app.config['LIFF_CHANNEL_ID']
        current_app.logger.info(f"🔍 環境變數 LIFF_CHANNEL_ID: {env_value}")
        current_app.logger.info(f"🔍 Config 中的 LIFF_CHANNEL_ID: {config_value}")
        
        # 從配置中獲取 Channel ID
        client_id = config_value or env_value
        current_app.logger.info(f"🔧 使用配置的 client_id: {client_id}")
        
        response = requests.post(
            'https://api.line.me/oauth2/v2.1/verify',
            data={
                'id_token': id_token,
                'client_id': client_id
            }
        )
        
        current_app.logger.info(f"🔍 LINE API 回應狀態: {response.status_code}")
        if response.status_code != 200:
            current_app.logger.error(f"🔍 LINE API 回應內容: {response.text}")
        
        response.raise_for_status()
        result = response.json()
        current_app.logger.info(f"✅ ID Token 驗證成功 - user_id: {result.get('sub')}")
        return result.get('sub')
    except requests.exceptions.RequestException as e:
        current_app.logger.error(f"ID Token 驗證失敗: {e}")
        if hasattr(e, 'response') and e.response is not None:
            current_app.logger.error(f"錯誤回應內容: {e.response.text}")
        return None

# --- 渲染 LIFF HTML 頁面 (共四個) ---

@liff_bp.route("/liff/camera")
def liff_camera_page():
    return render_template('camera.html', liff_id_camera=current_app.config['LIFF_ID_CAMERA'])

@liff_bp.route("/liff/edit_record")
def liff_edit_page():
    """渲染編輯記錄頁面，並檢查是否有有效的草稿"""
    # 可以在這裡添加一些預檢查邏輯
    return render_template('edit_record.html', liff_id_edit=current_app.config['LIFF_ID_EDIT'])

@liff_bp.route("/liff/prescription_reminder")
def prescription_reminder_page():
    """渲染從藥單批量設定提醒的頁面"""
    mm_id = request.args.get('mm_id')
    liff_id = current_app.config['LIFF_ID_PRESCRIPTION_REMINDER']
    return render_template('prescription_reminder_form.html', mm_id=mm_id, liff_id=liff_id)

@liff_bp.route('/liff/manual_reminder')
def manual_reminder_page():
    """
    渲染手動新增/編輯提醒的頁面。
    根據 URL 查詢參數 mode 的不同，前端 JS 會決定其行為。
    """
    mode = request.args.get('mode', 'add')
    reminder_id = request.args.get('reminder_id')
    member_id = request.args.get('member_id')
    
    # 從配置中獲取 LIFF ID
    liff_id = current_app.config['LIFF_ID_MANUAL_REMINDER']
    current_app.logger.info(f"🔧 手動提醒頁面 - 使用 LIFF ID: {liff_id}")
    
    return render_template(
        'manual_reminder_form.html', 
        mode=mode, 
        reminder_id=reminder_id, 
        member_id=member_id,
        liff_id=liff_id
    )

@liff_bp.route('/liff/health_form')
def health_form_page():
    """渲染健康記錄的頁面"""
    # 從環境變數讀取 LIFF ID
    liff_id = current_app.config['LIFF_ID_HEALTH_FORM']
    
    current_app.logger.info(f"🔧 健康記錄頁面 - 使用 LIFF ID: {liff_id}")
    
    return render_template('health_form.html', liff_id=liff_id)


# --- LIFF 後端 API (維持不變) ---

@liff_bp.route("/api/draft", methods=['GET'])
def get_draft_api():
    auth_header = request.headers.get('Authorization', '')
    id_token = auth_header.split(' ')[1] if auth_header.startswith('Bearer ') else None
    user_id = _verify_line_id_token(id_token)
    if not user_id:
        return jsonify({"status": "error", "message": "無效的 Token"}), 401

    full_state = UserService.get_user_complex_state(user_id)
    task_info = full_state.get("last_task", {})
    
    current_app.logger.info(f"草稿檢查 - 用戶: {user_id}, full_state keys: {list(full_state.keys())}")
    current_app.logger.info(f"草稿檢查 - task_info keys: {list(task_info.keys()) if task_info else 'None'}")

    if 'results' in task_info:
        data_for_frontend = task_info['results'].copy()
        
        # 清理藥物名稱中的引號字元，避免前端 JSON 解析錯誤
        if 'medications' in data_for_frontend:
            for med in data_for_frontend['medications']:
                if med.get('drug_name_zh'):
                    original = med['drug_name_zh']
                    cleaned = (original
                             .replace('"', '')  # 半形雙引號
                             .replace('"', '')  # 全形左雙引號
                             .replace('"', '')  # 全形右雙引號
                             .replace("'", '')  # 半形單引號
                             .replace(''', '')  # 全形左單引號
                             .replace(''', '')  # 全形右單引號
                             .replace('\\', '') # 反斜線
                             .strip())          # 去除首尾空白
                    med['drug_name_zh'] = cleaned
                    if original != cleaned:
                        current_app.logger.info(f"[CLEAN] 草稿藥名清理: '{original}' -> '{cleaned}'")
                        
                if med.get('drug_name_en'):
                    original = med['drug_name_en']
                    cleaned = (original
                             .replace('"', '').replace('"', '').replace('"', '')
                             .replace("'", '').replace(''', '').replace(''', '')
                             .replace('\\', '').strip())
                    med['drug_name_en'] = cleaned
                    if original != cleaned:
                        current_app.logger.info(f"[CLEAN] 草稿英文名清理: '{original}' -> '{cleaned}'")
        
        # 確保包含 member 資訊
        data_for_frontend['member'] = task_info.get('member')
        
        if data_for_frontend.get('visit_date'):
            data_for_frontend['visit_date'] = convert_minguo_to_gregorian(data_for_frontend['visit_date']) or data_for_frontend['visit_date']
        
        if task_info.get("mm_id_to_update"):
            data_for_frontend['mm_id_to_update'] = task_info.get("mm_id_to_update")
        
        current_app.logger.info(f"草稿資料已找到，用戶: {user_id}, 成員: {data_for_frontend.get('member')}")
        return jsonify(data_for_frontend)
    else:
        current_app.logger.warning(f"找不到草稿資料，用戶: {user_id}, task_info: {task_info}")
        
        # 提供更友善的錯誤訊息和建議
        return jsonify({
            "status": "error", 
            "message": "在伺服器上找不到對應的藥歷草稿。", 
            "suggestion": "請先進行藥單掃描分析，或從藥歷記錄中選擇要修改的項目。",
            "debug_info": {
                "user_id": user_id,
                "has_state": bool(full_state),
                "has_task": bool(task_info),
                "task_keys": list(task_info.keys()) if task_info else []
            }
        }), 404

@liff_bp.route("/api/draft/update", methods=['POST'])
def update_draft_api():
    id_token = request.headers.get('Authorization', '').split(' ')[1]
    user_id = _verify_line_id_token(id_token)
    if not user_id:
        return jsonify({"status": "error", "message": "無效的 Token"}), 401

    data = request.get_json()
    if not data or 'draftData' not in data:
        return jsonify({"status": "error", "message": "請求中缺少 'draftData'"}), 400
        
    updated_draft = data['draftData']

    full_state = UserService.get_user_complex_state(user_id)
    task_to_update = full_state.get("last_task", {})
    
    # 處理 member 和 mm_id_to_update 資訊
    member = updated_draft.pop('member', None) 
    if member:
        task_to_update['member'] = member
    
    mm_id = updated_draft.pop('mm_id_to_update', None)
    if mm_id:
        task_to_update['mm_id_to_update'] = mm_id
    
    task_to_update["results"] = updated_draft
    task_to_update["source"] = "manual_edit"
    
    full_state['last_task'] = task_to_update
    UserService.set_user_complex_state(user_id, full_state)
    
    current_app.logger.info(f"草稿已更新，用戶: {user_id}, 成員: {member}")
    
    return jsonify({"success": True, "message": "藥歷草稿已更新，請返回 LINE 查看預覽。"})

@liff_bp.route("/api/photo/upload_multiple_prescriptions", methods=['POST'])
def upload_multiple_prescriptions():
    try:
        photos = request.files.getlist('photos')
        user_id = request.form.get('lineUserId')
        task_id = request.form.get('taskId')
        
        if not all([user_id, task_id, photos]):
            return jsonify({"status": "error", "message": "請求缺少必要參數"}), 400

        state = UserService.get_user_complex_state(user_id)
        if state.get("last_task", {}).get("task_id") != task_id:
             return jsonify({"status": "error", "message": "任務ID不匹配，請重新操作。"}), 400

        image_b64_list = [base64.b64encode(p.read()).decode('utf-8') for p in photos]
        state["last_task"]["image_bytes_list"] = image_b64_list
        state.pop("state_info", None) 
        UserService.set_user_complex_state(user_id, state)
        
        # 不再需要背景線程，改為在 prescription_handler 中同步處理
        
        # 先回覆上傳成功，然後在背景執行分析
        return jsonify({
            "status": "success", 
            "message": "✅ 照片上傳成功！正在分析中，請稍候...",
            "shouldSendMessage": True,
            "shouldClose": True
        })
    except Exception as e:
        traceback.print_exc()
        current_app.logger.error(f"上傳檔案時發生錯誤: {e}")
        return jsonify({"status": "error", "message": f"伺服器處理時發生嚴重錯誤"}), 500

@liff_bp.route('/api/prescription/<int:mm_id>/medications', methods=['GET'])
def get_medications_for_prescription_api(mm_id):
    data = reminder_service.ReminderService.get_prescription_for_liff(mm_id)
    if data:
        return jsonify(data)
    return jsonify({"success": False, "message": "找不到藥歷資料"}), 404

@liff_bp.route('/api/reminders/batch_create', methods=['POST'])
def create_reminders_from_prescription_api():
    id_token = request.headers.get('Authorization', '').split(' ')[1]
    user_id = _verify_line_id_token(id_token)
    if not user_id:
        return jsonify({"success": False, "message": "無效的 Token"}), 401
    
    reminders = request.json.get('reminders', [])
    if not reminders:
        return jsonify({"success": False, "message": "沒有收到提醒資料"}), 400
    
    if reminder_service.ReminderService.create_reminders_batch(reminders, user_id):
        # 處方提醒儲存成功後，發送該成員的提醒列表 Flex Message
        try:
            from app.utils.db import DB
            from app.utils.flex import reminder as flex_reminder
            from app import line_bot_api
            
            # 從第一個提醒中獲取成員資訊
            if reminders and 'member_id' in reminders[0]:
                member_id = reminders[0]['member_id']
                member_info = DB.get_member_by_id(member_id)
                if member_info:
                    # 獲取該成員的所有提醒
                    member_reminders = reminder_service.ReminderService.get_reminders_for_member(user_id, member_info['member'])
                    
                    # 生成提醒列表 Flex Message
                    liff_id = current_app.config['LIFF_ID_MANUAL_REMINDER']
                    flex_message = flex_reminder.create_reminder_list_carousel(member_info, member_reminders, liff_id)
                    
                    # 發送 Push Message
                    line_bot_api.push_message(user_id, flex_message)
                    current_app.logger.info(f"已向用戶 {user_id} 發送 {member_info['member']} 的處方提醒列表")
        except Exception as e:
            current_app.logger.error(f"發送處方提醒列表 Flex Message 失敗: {e}")
            # 不影響主要功能，繼續返回成功
        
        return jsonify({"success": True, "message": "提醒已成功儲存"})
    return jsonify({"success": False, "message": "儲存提醒失敗"}), 500
    
@liff_bp.route('/api/reminders', methods=['POST'])
def create_manual_reminder_api():
    data = request.json
    user_id = _verify_line_id_token(data.get('idToken'))
    member_id = data.get('memberId')

    if not all([user_id, member_id]):
        return jsonify({'success': False, 'message': '驗證失敗或缺少必要資訊'}), 401
    
    # 這裡的 reminder_service 函式可能需要根據您的 DB 層進行調整
    new_id = reminder_service.ReminderService.create_or_update_reminder(user_id, member_id, data.get('formData', {}))
    if new_id:
        # 新增成功後，發送該成員的提醒列表 Flex Message
        try:
            from app.utils.db import DB
            from app.utils.flex import reminder as flex_reminder
            from app import line_bot_api
            
            # 獲取成員資訊
            member_info = DB.get_member_by_id(member_id)
            if member_info:
                # 獲取該成員的所有提醒
                reminders = reminder_service.ReminderService.get_reminders_for_member(user_id, member_info['member'])
                
                # 生成提醒列表 Flex Message
                liff_id = current_app.config['LIFF_ID_MANUAL_REMINDER']
                flex_message = flex_reminder.create_reminder_list_carousel(member_info, reminders, liff_id)
                
                # 發送 Push Message
                line_bot_api.push_message(user_id, flex_message)
                current_app.logger.info(f"已向用戶 {user_id} 發送 {member_info['member']} 的新增提醒列表")
        except Exception as e:
            current_app.logger.error(f"發送新增提醒列表 Flex Message 失敗: {e}")
            # 不影響主要功能，繼續返回成功
        
        return jsonify({'success': True, 'reminder_id': new_id})
    else:
        return jsonify({'success': False, 'message': '建立提醒失敗：找不到指定的成員或資料不完整'}), 400

@liff_bp.route('/api/reminders/<int:reminder_id>', methods=['GET', 'PUT'])
def manual_reminder_api(reminder_id):
    id_token = request.headers.get('Authorization', '').split(' ')[1]
    user_id = _verify_line_id_token(id_token)
    if not user_id:
        return jsonify({'success': False, 'message': '驗證失敗'}), 401
    
    if request.method == 'GET':
        reminder = reminder_service.ReminderService.get_reminder_details(reminder_id, user_id)
        if not reminder:
            return jsonify({'success': False, 'message': '找不到提醒或權限不足'}), 404
        
        # 轉換 timedelta 對象為字符串格式，避免 JSON 序列化錯誤
        for i in range(1, 6):
            time_slot_key = f'time_slot_{i}'
            if time_slot_key in reminder and reminder[time_slot_key]:
                time_slot = reminder[time_slot_key]
                # 如果是 timedelta 對象，轉換為 HH:MM 格式
                if hasattr(time_slot, 'total_seconds'):
                    total_seconds = int(time_slot.total_seconds())
                    hours = total_seconds // 3600
                    minutes = (total_seconds % 3600) // 60
                    reminder[time_slot_key] = f"{hours:02d}:{minutes:02d}"
                # 如果不是字符串，轉換為字符串
                elif not isinstance(time_slot, str):
                    reminder[time_slot_key] = str(time_slot)
        
        return jsonify(reminder)
        
    if request.method == 'PUT':
        form_data = request.json.get('formData', {})
        # 這裡的 reminder_service 函式可能需要根據您的 DB 層進行調整
        success = reminder_service.ReminderService.create_or_update_reminder(user_id, None, form_data, reminder_id)
        if success:
            # 編輯成功後，發送該成員的提醒列表 Flex Message
            try:
                from app.utils.db import DB
                from app.utils.flex import reminder as flex_reminder
                from app import line_bot_api
                
                # 獲取更新後的提醒資訊
                reminder_info = reminder_service.ReminderService.get_reminder_details(reminder_id, user_id)
                if reminder_info:
                    # 從 reminder_info 中獲取成員名稱
                    member_name = reminder_info.get('member')
                    if member_name:
                        # 通過成員名稱獲取成員資訊
                        members = DB.get_members(user_id)
                        member_info = next((m for m in members if m['member'] == member_name), None)
                        
                        if member_info:
                            # 獲取該成員的所有提醒
                            reminders = reminder_service.ReminderService.get_reminders_for_member(user_id, member_name)
                            
                            # 生成提醒列表 Flex Message
                            liff_id = current_app.config['LIFF_ID_MANUAL_REMINDER']
                            flex_message = flex_reminder.create_reminder_list_carousel(member_info, reminders, liff_id)
                            
                            # 發送 Push Message
                            line_bot_api.push_message(user_id, flex_message)
                            current_app.logger.info(f"已向用戶 {user_id} 發送 {member_name} 的更新提醒列表")
                        else:
                            current_app.logger.warning(f"找不到成員資訊: {member_name}")
                    else:
                        current_app.logger.warning(f"提醒資訊中找不到 member: {list(reminder_info.keys())}")
            except Exception as e:
                current_app.logger.error(f"發送更新提醒列表 Flex Message 失敗: {e}")
                # 不影響主要功能，繼續返回成功
            
            return jsonify({'success': True})
        return jsonify({'success': False, 'message': '更新失敗或權限不足'}), 500

# --- 健康記錄 API ---

@liff_bp.route('/api/health_logs/<string:recorder_id>', methods=['GET'])
def get_health_logs_api(recorder_id):
    """獲取指定用戶相關的所有健康記錄（包含家人建立的）"""
    try:
        logs = DB.get_all_logs_by_recorder(recorder_id)
        # 手動序列化以確保使用 CustomJSONEncoder
        from flask import Response
        from app import CustomJSONEncoder
        import json
        response_json = json.dumps(logs, cls=CustomJSONEncoder)
        return Response(response_json, mimetype='application/json')
    except Exception as e:
        current_app.logger.error(f"獲取健康記錄失敗: {e}")
        return jsonify({"error": "獲取健康記錄失敗"}), 500

@liff_bp.route('/api/health_logs/<string:recorder_id>/member/<string:member_id>', methods=['GET'])
def get_member_health_logs_api(recorder_id, member_id):
    """獲取特定成員的健康記錄（包含邀請者建立的 + 該成員自建的）"""
    try:
        logs = DB.get_logs_for_specific_member(recorder_id, member_id)
        return jsonify(logs)
    except Exception as e:
        current_app.logger.error(f"獲取成員健康記錄失敗: {e}")
        return jsonify({"error": "獲取成員健康記錄失敗"}), 500

@liff_bp.route('/api/health_log', methods=['POST'])
def create_health_log_api():
    """新增健康記錄"""
    try:
        data = request.get_json()
        current_app.logger.info(f"收到健康記錄資料: {data}")
        
        if not data:
            current_app.logger.error("缺少請求資料")
            return jsonify({"error": "缺少請求資料"}), 400
        
        # 驗證必要欄位
        if not data.get('recorderId') or not data.get('targetPerson'):
            current_app.logger.error(f"缺少必要欄位 - recorderId: {data.get('recorderId')}, targetPerson: {data.get('targetPerson')}")
            return jsonify({"error": "缺少必要欄位"}), 400
        
        current_app.logger.info(f"準備新增健康記錄 - 用戶: {data.get('recorderId')}, 對象: {data.get('targetPerson')}")
        success = DB.add_health_log(data)
        
        if success:
            current_app.logger.info("健康記錄新增成功")
            return jsonify({"success": True, "message": "健康記錄新增成功"})
        else:
            current_app.logger.error("資料庫新增失敗")
            return jsonify({"error": "新增健康記錄失敗"}), 500
            
    except Exception as e:
        current_app.logger.error(f"新增健康記錄失敗: {e}")
        import traceback
        current_app.logger.error(f"錯誤詳情: {traceback.format_exc()}")
        return jsonify({"error": f"新增健康記錄失敗: {str(e)}"}), 500

@liff_bp.route('/api/health_log/<int:log_id>', methods=['DELETE'])
def delete_health_log_api(log_id):
    """刪除健康記錄"""
    try:
        data = request.get_json()
        if not data or not data.get('recorderId'):
            return jsonify({"error": "缺少記錄者ID"}), 400
        
        recorder_id = data.get('recorderId')
        success = DB.delete_health_log(log_id, recorder_id)
        
        if success:
            return jsonify({"success": True, "message": "健康記錄刪除成功"})
        else:
            return jsonify({"error": "刪除失敗或無權限"}), 403
            
    except Exception as e:
        current_app.logger.error(f"刪除健康記錄失敗: {e}")
        return jsonify({"error": "刪除健康記錄失敗"}), 500

@liff_bp.route('/api/family_list/<user_id>', methods=['GET'])
def get_family_list_api(user_id):
    """獲取用戶的家人綁定列表"""
    try:
        from app.services.family_service import FamilyService
        
        # 獲取家人列表
        family_list = FamilyService.get_family_list(user_id)
        
        current_app.logger.info(f"用戶 {user_id} 的家人列表: {family_list}")
        
        return jsonify(family_list)
        
    except Exception as e:
        current_app.logger.error(f"獲取家人列表失敗: {e}")
        return jsonify({"error": "獲取家人列表失敗"}), 500

# 移除背景分析函數，現在改為在 prescription_handler 中同步處理

# --- END OF FILE: app/routes/liff_views.py ---