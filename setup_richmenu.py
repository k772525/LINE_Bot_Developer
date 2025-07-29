#!/usr/bin/env python3
# setup_richmenu.py - 獨立的圖文選單設定腳本

import os
import sys
from dotenv import load_dotenv
from linebot import LineBotApi
from linebot.models import RichMenu, RichMenuSize, RichMenuArea, RichMenuBounds, MessageAction, PostbackAction

# 載入環境變數
load_dotenv()

def find_image_file():
    """尋找項目內的圖片文件"""
    # 可能的圖片文件名
    possible_names = [
        "richmenu.jpg", "richmenu.png", "richmenu.jpeg",
        "menu.jpg", "menu.png", "menu.jpeg",
        "123.jpg", "123.png", "123.jpeg"
    ]
    
    # 可能的路徑
    possible_paths = [".", "images", "assets", "static"]
    
    for path in possible_paths:
        for name in possible_names:
            full_path = os.path.join(path, name)
            if os.path.exists(full_path):
                print(f"✅ 找到圖片文件: {full_path}")
                return full_path
    
    # 如果找不到，提示用戶
    print("❌ 找不到圖片文件")
    print("請將圖文選單圖片放在以下位置之一：")
    for path in possible_paths:
        for name in possible_names[:3]:  # 只顯示主要的文件名
            print(f"   {os.path.join(path, name)}")
    
    # 詢問用戶是否要創建默認圖片
    create_default = input("\n是否創建一個簡單的默認圖片？(y/N): ").strip().lower()
    if create_default == 'y':
        return create_default_image()
    
    return None

def create_default_image():
    """創建一個簡單的默認圖片"""
    try:
        from PIL import Image, ImageDraw, ImageFont
        
        # 創建 2500x1686 的圖片 (LINE 圖文選單標準尺寸)
        img = Image.new('RGB', (2500, 1686), color='#f0f0f0')
        draw = ImageDraw.Draw(img)
        
        # 繪製網格線和按鈕區域
        # 垂直線
        draw.line([(833, 0), (833, 1686)], fill='#cccccc', width=3)
        draw.line([(1667, 0), (1667, 1686)], fill='#cccccc', width=3)
        # 水平線
        draw.line([(0, 843), (2500, 843)], fill='#cccccc', width=3)
        
        # 添加按鈕文字
        buttons = [
            ("藥單辨識", 416, 421),
            ("藥品辨識", 1250, 421),
            ("用藥提醒", 2083, 421),
            ("家人綁定", 416, 1264),
            ("我的藥歷", 1250, 1264),
            ("健康紀錄", 2083, 1264)
        ]
        
        try:
            # 嘗試使用系統字體
            font = ImageFont.truetype("arial.ttf", 60)
        except:
            # 如果找不到字體，使用默認字體
            font = ImageFont.load_default()
        
        for text, x, y in buttons:
            # 計算文字位置 (居中)
            bbox = draw.textbbox((0, 0), text, font=font)
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]
            
            draw.text((x - text_width//2, y - text_height//2), text, 
                     fill='#333333', font=font)
        
        # 保存圖片
        image_path = "9beee648ee10f2bc.jpg"
        img.save(image_path, "JPEG", quality=95)
        print(f"✅ 已創建默認圖片: {image_path}")
        return image_path
        
    except ImportError:
        print("❌ 無法創建默認圖片 (需要安裝 Pillow: pip install Pillow)")
        return None
    except Exception as e:
        print(f"❌ 創建默認圖片失敗: {e}")
        return None

def upload_image_file(line_bot_api, rich_menu_id, image_path):
    """上傳指定的圖片檔案到圖文選單"""
    try:
        if not os.path.exists(image_path):
            print(f"❌ 找不到圖片檔案: {image_path}")
            return False
        
        # 檢查檔案格式
        if not image_path.lower().endswith(('.png', '.jpg', '.jpeg')):
            print(f"❌ 不支援的圖片格式: {image_path}")
            print("   支援格式: PNG, JPG, JPEG")
            return False
        
        # 讀取圖片檔案
        with open(image_path, 'rb') as f:
            image_data = f.read()
        
        # 檢查檔案大小 (1MB = 1048576 bytes)
        if len(image_data) > 1048576:
            print(f"❌ 圖片檔案太大: {len(image_data)} bytes")
            print("   最大允許: 1MB (1048576 bytes)")
            return False
        
        # 確定 MIME 類型
        if image_path.lower().endswith('.png'):
            content_type = 'image/png'
        else:
            content_type = 'image/jpeg'
        
        # 上傳圖片
        line_bot_api.set_rich_menu_image(rich_menu_id, content_type, image_data)
        print(f"✅ 圖片上傳成功: {image_path}")
        return True
        
    except Exception as e:
        print(f"❌ 上傳圖片失敗: {e}")
        return False

def create_richmenu():
    """創建並設定圖文選單"""
    
    # 初始化 LINE Bot API
    channel_access_token = os.environ.get('LINE_CHANNEL_ACCESS_TOKEN')
    if not channel_access_token:
        print("❌ 錯誤：找不到 LINE_CHANNEL_ACCESS_TOKEN 環境變數")
        print("請確保 .env 文件中有設定 LINE_CHANNEL_ACCESS_TOKEN")
        return False
    
    line_bot_api = LineBotApi(channel_access_token)
    
    try:
        # 1. 先刪除所有現有的圖文選單
        print("🔍 檢查現有的圖文選單...")
        existing_menus = line_bot_api.get_rich_menu_list()
        
        for menu in existing_menus:
            print(f"🗑️ 刪除現有圖文選單: {menu.name} (ID: {menu.rich_menu_id})")
            line_bot_api.delete_rich_menu(menu.rich_menu_id)
        
        # 2. 創建新的圖文選單
        print("🎨 創建新的圖文選單...")
        
        # 您可以在這裡自定義按鈕配置
        rich_menu = RichMenu(
            size=RichMenuSize(width=2500, height=1686),
            selected=True,
            name="家庭健康小幫手主選單",
            chat_bar_text="點擊查看功能選單 📋",
            areas=[
                # 第一排左側：掃描新藥單
                RichMenuArea(
                    bounds=RichMenuBounds(x=0, y=0, width=833, height=843),
                    action=MessageAction(text="藥單辨識")
                ),
                # 第一排中間：藥品辨識
                RichMenuArea(
                    bounds=RichMenuBounds(x=833, y=0, width=834, height=843),
                    action=MessageAction(text="藥品辨識")
                ),
                # 第一排右側：用藥提醒管理
                RichMenuArea(
                    bounds=RichMenuBounds(x=1667, y=0, width=833, height=843),
                    action=MessageAction(text="用藥提醒")
                ),
                # 第二排左側：家人綁定與管理
                RichMenuArea(
                    bounds=RichMenuBounds(x=0, y=843, width=833, height=843),
                    action=MessageAction(text="家人綁定與管理")
                ),
                # 第二排中間：我的藥歷
                RichMenuArea(
                    bounds=RichMenuBounds(x=833, y=843, width=834, height=843),
                    action=MessageAction(text="我的藥歷")
                ),
                # 第二排右側：設定
                RichMenuArea(
                    bounds=RichMenuBounds(x=1667, y=843, width=833, height=843),
                    action=MessageAction(text="健康紀錄")
                )
            ]
        )
        
        # 創建圖文選單
        rich_menu_id = line_bot_api.create_rich_menu(rich_menu)
        print(f"✅ 圖文選單創建成功！ID: {rich_menu_id}")
        
        # 尋找項目內的圖片文件
        image_path = find_image_file()
        if not image_path:
            print("❌ 找不到圖片文件，刪除已創建的圖文選單")
            line_bot_api.delete_rich_menu(rich_menu_id)
            return False
            
        print(f"🖼️ 正在上傳圖片: {image_path}")
        
        if upload_image_file(line_bot_api, rich_menu_id, image_path):
            # 設定為預設圖文選單
            line_bot_api.set_default_rich_menu(rich_menu_id)
            print("✅ 已設定為預設圖文選單")
        else:
            print("❌ 圖片上傳失敗，刪除已創建的圖文選單")
            line_bot_api.delete_rich_menu(rich_menu_id)
            return False
        
        print("\n🎉 圖文選單設定完成！")
        print("📱 現在您的 LINE Bot 用戶應該可以看到新的圖文選單了")
        
        # 顯示按鈕配置
        print("\n📋 圖文選單按鈕配置：")
        print("第一排：")
        print("  左側：藥單辨識")
        print("  中間：藥品辨識") 
        print("  右側：用藥提醒")
        print("第二排：")
        print("  左側：家人綁定與管理")
        print("  中間：我的藥歷")
        print("  右側：健康紀錄")
        
        return True
        
    except Exception as e:
        print(f"❌ 設定圖文選單失敗: {e}")
        return False

def customize_richmenu():
    """自定義圖文選單按鈕"""
    print("🎨 自定義圖文選單設定")
    print("=" * 50)
    
    # 讓用戶自定義按鈕
    buttons = {}
    positions = [
        "第一排左側", "第一排中間", "第一排右側",
        "第二排左側", "第二排中間", "第二排右側"
    ]
    
    print("請為每個位置設定按鈕文字（直接按 Enter 使用預設值）：")
    
    default_texts = [
        "藥品辨識", "用藥提醒", "健康紀錄",
        "家人綁定與管理", "藥單辨識", "設定"
    ]
    
    for i, position in enumerate(positions):
        user_input = input(f"{position} (預設: {default_texts[i]}): ").strip()
        buttons[position] = user_input if user_input else default_texts[i]
    
    print("\n您的自定義配置：")
    for position, text in buttons.items():
        print(f"  {position}: {text}")
    
    confirm = input("\n確認使用此配置嗎？(y/N): ").strip().lower()
    if confirm == 'y':
        return create_custom_richmenu(buttons)
    else:
        print("❌ 已取消設定")
        return False

def create_custom_richmenu(buttons):
    """使用自定義按鈕創建圖文選單"""
    
    channel_access_token = os.environ.get('LINE_CHANNEL_ACCESS_TOKEN')
    if not channel_access_token:
        print("❌ 錯誤：找不到 LINE_CHANNEL_ACCESS_TOKEN 環境變數")
        return False
    
    line_bot_api = LineBotApi(channel_access_token)
    
    try:
        # 刪除現有選單
        existing_menus = line_bot_api.get_rich_menu_list()
        for menu in existing_menus:
            line_bot_api.delete_rich_menu(menu.rich_menu_id)
        
        # 創建自定義圖文選單
        rich_menu = RichMenu(
            size=RichMenuSize(width=2500, height=1686),
            selected=True,
            name="自定義家庭健康小幫手選單",
            chat_bar_text="點擊查看功能選單 📋",
            areas=[
                # 使用用戶自定義的按鈕文字
                RichMenuArea(
                    bounds=RichMenuBounds(x=0, y=0, width=833, height=843),
                    action=MessageAction(text=buttons["第一排左側"])
                ),
                RichMenuArea(
                    bounds=RichMenuBounds(x=833, y=0, width=834, height=843),
                    action=MessageAction(text=buttons["第一排中間"])
                ),
                RichMenuArea(
                    bounds=RichMenuBounds(x=1667, y=0, width=833, height=843),
                    action=MessageAction(text=buttons["第一排右側"])
                ),
                RichMenuArea(
                    bounds=RichMenuBounds(x=0, y=843, width=833, height=843),
                    action=MessageAction(text=buttons["第二排左側"])
                ),
                RichMenuArea(
                    bounds=RichMenuBounds(x=833, y=843, width=834, height=843),
                    action=MessageAction(text=buttons["第二排中間"])
                ),
                RichMenuArea(
                    bounds=RichMenuBounds(x=1667, y=843, width=833, height=843),
                    action=MessageAction(text=buttons["第二排右側"])
                )
            ]
        )
        
        rich_menu_id = line_bot_api.create_rich_menu(rich_menu)
        print(f"✅ 自定義圖文選單創建成功！ID: {rich_menu_id}")
        
        # 尋找項目內的圖片文件
        image_path = find_image_file()
        if not image_path:
            print("❌ 找不到圖片文件，刪除已創建的圖文選單")
            line_bot_api.delete_rich_menu(rich_menu_id)
            return False
            
        print(f"🖼️ 正在上傳圖片: {image_path}")
        
        if upload_image_file(line_bot_api, rich_menu_id, image_path):
            # 設定為預設圖文選單
            line_bot_api.set_default_rich_menu(rich_menu_id)
            print("✅ 已設定為預設圖文選單")
            return True
        else:
            print("❌ 圖片上傳失敗，刪除已創建的圖文選單")
            line_bot_api.delete_rich_menu(rich_menu_id)
            return False
        
    except Exception as e:
        print(f"❌ 設定自定義圖文選單失敗: {e}")
        return False

def main():
    """主函式"""
    print("🤖 LINE Bot 圖文選單設定工具")
    print("=" * 40)
    
    # 檢查環境變數
    if not os.path.exists('.env'):
        print("❌ 找不到 .env 文件")
        print("請確保在專案根目錄有 .env 文件並設定了 LINE_CHANNEL_ACCESS_TOKEN")
        return
    
    print("請選擇操作：")
    print("1. 使用預設配置設定圖文選單")
    print("2. 自定義圖文選單按鈕")
    print("3. 查看現有圖文選單")
    print("4. 刪除所有圖文選單")
    
    choice = input("\n請輸入選項 (1-4): ").strip()
    
    if choice == '1':
        create_richmenu()
    elif choice == '2':
        customize_richmenu()
    elif choice == '3':
        view_existing_menus()
    elif choice == '4':
        delete_all_menus()
    else:
        print("❌ 無效的選項")

def view_existing_menus():
    """查看現有圖文選單"""
    channel_access_token = os.environ.get('LINE_CHANNEL_ACCESS_TOKEN')
    if not channel_access_token:
        print("❌ 錯誤：找不到 LINE_CHANNEL_ACCESS_TOKEN 環境變數")
        return
    
    line_bot_api = LineBotApi(channel_access_token)
    
    try:
        menus = line_bot_api.get_rich_menu_list()
        if not menus:
            print("📭 目前沒有任何圖文選單")
        else:
            print(f"📋 找到 {len(menus)} 個圖文選單：")
            for i, menu in enumerate(menus, 1):
                print(f"  {i}. {menu.name} (ID: {menu.rich_menu_id})")
                print(f"     聊天欄文字: {menu.chat_bar_text}")
                print(f"     是否選中: {menu.selected}")
                print()
    except Exception as e:
        print(f"❌ 查看圖文選單失敗: {e}")

def delete_all_menus():
    """刪除所有圖文選單"""
    channel_access_token = os.environ.get('LINE_CHANNEL_ACCESS_TOKEN')
    if not channel_access_token:
        print("❌ 錯誤：找不到 LINE_CHANNEL_ACCESS_TOKEN 環境變數")
        return
    
    line_bot_api = LineBotApi(channel_access_token)
    
    try:
        menus = line_bot_api.get_rich_menu_list()
        if not menus:
            print("📭 目前沒有任何圖文選單")
            return
        
        confirm = input(f"⚠️ 確定要刪除所有 {len(menus)} 個圖文選單嗎？(y/N): ").strip().lower()
        if confirm == 'y':
            for menu in menus:
                line_bot_api.delete_rich_menu(menu.rich_menu_id)
                print(f"🗑️ 已刪除: {menu.name}")
            print("✅ 所有圖文選單已刪除")
        else:
            print("❌ 已取消刪除操作")
    except Exception as e:
        print(f"❌ 刪除圖文選單失敗: {e}")

if __name__ == "__main__":
    main()