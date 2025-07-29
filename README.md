# 🏥 智能藥品管理 LINE Bot

<div align="center">

![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)
![Flask](https://img.shields.io/badge/Flask-2.3+-green.svg)
![LINE Bot](https://img.shields.io/badge/LINE-Bot%20API-00C300.svg)
![Google Cloud](https://img.shields.io/badge/Google%20Cloud-Run-4285F4.svg)
![License](https://img.shields.io/badge/License-MIT-yellow.svg)

**一個功能完整的 LINE Bot 智能藥品管理系統**

[功能特色](#-功能特色) • [快速開始](#-快速開始) • [部署指南](#-部署) • [API 文檔](#-api-文檔) • [貢獻指南](#-貢獻)

</div>

## ✨ 主要功能

- 📋 **藥單辨識**: 使用 AI 技術自動辨識藥單照片
- ⏰ **用藥提醒**: 智能提醒系統，支援多種提醒模式
- 👨‍👩‍👧‍👦 **家人綁定**: 家庭成員互相關心，共同管理健康
- 🗂️ **藥歷管理**: 完整的用藥記錄管理系統
- 📊 **健康記錄**: 記錄和追蹤健康狀況
- 🎙️ **語音快捷鍵**: 語音指令快速操作，支援語音新增提醒對象
- 🤖 **AI 助手**: 基於 Google Gemini 的智能對話

## 🏗️ 技術架構

- **後端框架**: Flask 3.1.1
- **資料庫**: MySQL
- **AI 服務**: Google Gemini API
- **語音識別**: Google Cloud Speech-to-Text API
- **訊息平台**: LINE Bot SDK
- **前端**: LIFF (LINE Front-end Framework)
- **部署**: Google Cloud Run
- **容器化**: Docker

## 🚀 快速開始

### 環境需求

- Python 3.11+
- MySQL 8.0+
- Docker (可選)

## 🔧 配置說明

### 必要環境變數

```bash
# LINE Bot API 設定
LINE_CHANNEL_ACCESS_TOKEN=your_access_token
LINE_CHANNEL_SECRET=your_channel_secret
YOUR_BOT_ID=@your_bot_id

# LIFF 應用程式設定
LIFF_CHANNEL_ID=your_liff_channel_id
LIFF_ID_CAMERA=your_camera_liff_id
LIFF_ID_EDIT=your_edit_liff_id
LIFF_ID_PRESCRIPTION_REMINDER=your_prescription_reminder_liff_id
LIFF_ID_MANUAL_REMINDER=your_manual_reminder_liff_id
LIFF_ID_HEALTH_FORM=your_health_form_liff_id

# LINE Login 設定
LINE_LOGIN_CHANNEL_ID=your_login_channel_id
LINE_LOGIN_CHANNEL_SECRET=your_login_channel_secret

# Google Gemini API 設定
GEMINI_API_KEY=your_gemini_api_key

# Google Cloud Speech-to-Text 設定 (語音識別)
GOOGLE_APPLICATION_CREDENTIALS=path/to/service-account-key.json
SPEECH_TO_TEXT_ENABLED=true

# MySQL 資料庫設定
DB_HOST=your_db_host
DB_USER=your_db_user
DB_PASS=your_db_password
DB_NAME=your_db_name
DB_PORT=3306

# Flask 設定
SECRET_KEY=your_secret_key
```

## 🎙️ 語音快捷鍵功能

### 語音新增提醒對象

用戶可以透過語音快速新增提醒對象，支援以下語音指令格式：

#### 支援的語音指令

| 指令類型 | 範例語音指令 | 說明 |
|---------|-------------|------|
| **新增提醒對象** | 「新增提醒對象媽媽」<br>「我要新增提醒對象爸爸」<br>「幫我新增提醒對象奶奶」 | 新增指定名稱的提醒對象 |
| **新增家人** | 「新增家人弟弟」<br>「我要新增家人姊姊」<br>「幫我新增家人阿姨」 | 以家人身份新增提醒對象 |
| **建立提醒對象** | 「建立提醒對象外婆」<br>「我要建立提醒對象小明」 | 建立新的提醒對象 |
| **其他變體** | 「新增成員小華」<br>「新增家庭成員叔叔」 | 其他自然語言變體 |

#### 功能特色

- 🎯 **智能解析**: 支援多種自然語言表達方式
- ✅ **錯誤處理**: 自動檢查重複名稱、無效輸入
- 💬 **友善回應**: 根據指令類型返回相應的成功訊息
- ⚡ **優先處理**: 最高優先級處理，避免與其他功能衝突
- 🔍 **完整測試**: 通過多項測試案例驗證解析邏輯

#### 使用方式

1. 在 LINE Bot 對話中，長按麥克風按鈕錄製語音
2. 清楚說出指令，例如：「新增提醒對象媽媽」
3. 系統會自動識別語音並新增提醒對象
4. 收到成功確認訊息後即可為該成員設定用藥提醒

#### 技術實作

- **語音識別**: Google Cloud Speech-to-Text API
- **語音優化**: Google Gemini AI 優化識別結果
- **指令解析**: 正則表達式匹配多種語音指令格式
- **智能過濾**: 自動過濾無效名稱和重複成員

## 📁 專案結構

```
.
├── app/                    # 主應用程式目錄
│   ├── routes/            # 路由處理
│   │   ├── handlers/      # 業務邏輯處理器
│   │   ├── auth.py        # 認證相關
│   │   ├── liff_views.py  # LIFF 視圖
│   │   └── line_webhook.py # LINE Webhook
│   ├── services/          # 業務服務層
│   │   ├── voice_service.py    # 語音識別和處理服務
│   │   ├── ai_processor.py     # AI 處理服務
│   │   ├── reminder_service.py # 提醒服務
│   │   └── user_service.py     # 用戶服務
│   ├── templates/         # HTML 模板
│   └── utils/             # 工具函數
├── .github/               # GitHub Actions 配置
│   ├── workflows/         # CI/CD 工作流程
│   └── ISSUE_TEMPLATE/    # Issue 模板
├── Dockerfile             # Docker 配置
├── requirements.txt       # Python 依賴
├── config.py             # 應用程式配置
└── run.py                # 應用程式入口點
```

## 🔄 CI/CD 流程

本專案使用 GitHub Actions 實現自動化 CI/CD：

### 主要工作流程

1. **CI/CD Pipeline** (`.github/workflows/ci-cd.yml`)
   - 程式碼品質檢查
   - 自動化測試
   - Docker 映像建構和推送
   - 自動部署到 staging/production

2. **GCP 部署** (`.github/workflows/deploy-gcp.yml`)
   - 部署到 Google Cloud Run
   - 環境變數管理
   - 健康檢查

3. **安全掃描** (`.github/workflows/security-scan.yml`)
   - 依賴漏洞掃描
   - 程式碼安全分析
   - Docker 映像安全檢查

### 部署環境

- **Staging**: `develop` 分支自動部署
- **Production**: `main` 分支自動部署

## 🔒 安全性

- 使用 GitHub Secrets 管理敏感資訊
- 定期進行安全掃描
- 依賴項目自動更新 (Dependabot)
- 容器映像漏洞檢測



## 🙏 致謝

- [LINE Developers](https://developers.line.biz/)
- [Google Gemini](https://ai.google.dev/)
- [Google Cloud Speech-to-Text](https://cloud.google.com/speech-to-text)
- [Flask](https://flask.palletsprojects.com/)
- 所有貢獻者

---

**注意**: 請確保在生產環境中妥善保護您的 API 金鑰和敏感資訊。"# LINE_Bot_Developer" 
