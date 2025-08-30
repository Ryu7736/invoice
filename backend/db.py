import sqlite3
from datetime import datetime
import os

# データベース初期化
def init_database():
    """データベースとテーブルを初期化"""
    db_path = "invoice_data.db"
    
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        
        # 🏢 顧客マスタテーブル
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS customers (
                customer_id INTEGER PRIMARY KEY AUTOINCREMENT,
                customer_name TEXT NOT NULL,
                billing_cycle TEXT NOT NULL DEFAULT '月末',  -- '20日' or '月末'
                payment_method TEXT DEFAULT '現金',
                address TEXT,
                phone_number TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # 📦 商品マスタテーブル
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS products (
                product_id INTEGER PRIMARY KEY AUTOINCREMENT,
                product_name TEXT NOT NULL,
                base_price REAL NOT NULL,
                category TEXT DEFAULT 'タイヤ',  -- タイヤ、作業、部品等
                unit TEXT DEFAULT '本',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # 🚛 取引データテーブル（OCR抽出＋統合情報）
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS transactions (
                transaction_id INTEGER PRIMARY KEY AUTOINCREMENT,
                customer_id INTEGER,
                product_id INTEGER,
                quantity REAL NOT NULL,
                unit_price REAL NOT NULL,
                total_amount REAL NOT NULL,
                tire_size TEXT,
                tire_type TEXT,
                work_content TEXT,
                transaction_date DATE NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                ocr_confidence REAL DEFAULT 0.0,
                is_verified BOOLEAN DEFAULT FALSE,
                FOREIGN KEY (customer_id) REFERENCES customers (customer_id),
                FOREIGN KEY (product_id) REFERENCES products (product_id)
            )
        """)
        
        # 📄 OCR処理ログテーブル
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS ocr_logs (
                log_id INTEGER PRIMARY KEY AUTOINCREMENT,
                file_name TEXT NOT NULL,
                processing_time REAL,
                texts_detected INTEGER,
                texts_extracted INTEGER,
                processing_status TEXT DEFAULT 'success',
                error_message TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # 🧾 請求書生成ログテーブル
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS invoice_logs (
                invoice_id INTEGER PRIMARY KEY AUTOINCREMENT,
                customer_id INTEGER,
                billing_period_start DATE,
                billing_period_end DATE,
                total_amount REAL,
                invoice_file_path TEXT,
                generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (customer_id) REFERENCES customers (customer_id)
            )
        """)
        
        conn.commit()
        print("✅ データベース初期化完了")

# サンプルデータ投入
def insert_sample_data():
    """テスト用のサンプルデータを投入"""
    with sqlite3.connect("invoice_data.db") as conn:
        cursor = conn.cursor()
        
        # サンプル顧客データ
        sample_customers = [
            ("田中自動車", "月末", "現金", "東京都渋谷区1-1-1", "03-1234-5678"),
            ("佐藤モータース", "20日", "銀行振込", "大阪市中央区2-2-2", "06-9876-5432"),
            ("山田タイヤ商会", "月末", "現金", "名古屋市中区3-3-3", "052-1111-2222")
        ]
        
        cursor.executemany("""
            INSERT OR IGNORE INTO customers 
            (customer_name, billing_cycle, payment_method, address, phone_number)
            VALUES (?, ?, ?, ?, ?)
        """, sample_customers)
        
        # サンプル商品データ
        sample_products = [
            ("ブリヂストン 195/65R15", 15000, "タイヤ", "本"),
            ("ヨコハマ 205/55R16", 18000, "タイヤ", "本"),
            ("タイヤ取付作業", 2000, "作業", "本"),
            ("ホイールバランス調整", 1500, "作業", "本"),
            ("廃タイヤ処理", 500, "処理", "本")
        ]
        
        cursor.executemany("""
            INSERT OR IGNORE INTO products 
            (product_name, base_price, category, unit)
            VALUES (?, ?, ?, ?)
        """, sample_products)
        
        conn.commit()
        print("✅ サンプルデータ投入完了")

# OCR結果をデータベースに保存
def save_ocr_result(customer_name, product_name, quantity, amount, date, tire_size=None, work_content=None):
    """OCR抽出結果をデータベースに保存"""
    with sqlite3.connect("invoice_data.db") as conn:
        cursor = conn.cursor()
        
        # 顧客IDを取得（なければ作成）
        cursor.execute("SELECT customer_id FROM customers WHERE customer_name LIKE ?", (f"%{customer_name}%",))
        customer_result = cursor.fetchone()
        
        if customer_result:
            customer_id = customer_result[0]
        else:
            cursor.execute("""
                INSERT INTO customers (customer_name, billing_cycle)
                VALUES (?, '月末')
            """, (customer_name,))
            customer_id = cursor.lastrowid
        
        # 商品IDを取得（なければ作成）
        cursor.execute("SELECT product_id FROM products WHERE product_name LIKE ?", (f"%{product_name}%",))
        product_result = cursor.fetchone()
        
        if product_result:
            product_id = product_result[0]
        else:
            cursor.execute("""
                INSERT INTO products (product_name, base_price, category)
                VALUES (?, ?, 'その他')
            """, (product_name, amount))
            product_id = cursor.lastrowid
        
        # 取引データを保存
        cursor.execute("""
            INSERT INTO transactions 
            (customer_id, product_id, quantity, unit_price, total_amount, 
             tire_size, work_content, transaction_date)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (customer_id, product_id, quantity, amount, amount * quantity, 
              tire_size, work_content, date))
        
        conn.commit()
        return cursor.lastrowid

# 請求書データ取得
def get_invoice_data(customer_id, start_date, end_date):
    """指定期間の請求書データを取得"""
    with sqlite3.connect("invoice_data.db") as conn:
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT 
                c.customer_name,
                c.address,
                c.phone_number,
                p.product_name,
                t.quantity,
                t.unit_price,
                t.total_amount,
                t.tire_size,
                t.work_content,
                t.transaction_date
            FROM transactions t
            JOIN customers c ON t.customer_id = c.customer_id
            JOIN products p ON t.product_id = p.product_id
            WHERE t.customer_id = ? 
            AND t.transaction_date BETWEEN ? AND ?
            ORDER BY t.transaction_date
        """, (customer_id, start_date, end_date))
        
        return cursor.fetchall()

if __name__ == "__main__":
    init_database()
    insert_sample_data()