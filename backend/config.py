import os

# 🗂️ ディレクトリ設定
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")
INVOICE_DIR = os.path.join(BASE_DIR, "invoices")
LOG_DIR = os.path.join(BASE_DIR, "logs")

# 📊 データベース設定
DATABASE_PATH = os.path.join(BASE_DIR, "invoice_data.db")

# 🔧 OCR設定
OCR_CONFIG = {
    "language": "japan",
    "confidence_threshold": 0.6,
    "use_preprocessing": True,
    "max_image_size": 2000
}

# 💼 会社情報
COMPANY_INFO = {
    "name": "○○タイヤサービス株式会社",
    "address": "〒000-0000 東京都○○区○○1-1-1",
    "phone": "03-0000-0000",
    "fax": "03-0000-0001",
    "email": "info@tire-service.co.jp"
}

# 📁 必要ディレクトリを作成
for directory in [UPLOAD_DIR, INVOICE_DIR, LOG_DIR]:
    os.makedirs(directory, exist_ok=True)