from flask import Blueprint, render_template, jsonify, request, send_file
from backend import ocr
import sqlite3
import os
from datetime import datetime
import tempfile
import traceback
from backend.db import (
    init_database, 
    save_ocr_result, 
    get_invoice_data
)
from backend.excel_generator import generate_invoice

main_bp = Blueprint("main", __name__)

# 🏠 メインページ
@main_bp.route("/")
def index():
    """メインページ（OCRアップロード画面）"""
    return render_template("index.html")

# 📁 OCRファイルアップロード処理
@main_bp.route("/uploads", methods=["POST"])
def uploads():
    """OCR処理のメインエンドポイント"""
    try:
        files = request.files.getlist("files")
        if not files:
            return jsonify({"error": "ファイルが選択されていません"}), 400

        print(f"[DEBUG] 📁 {len(files)}個のファイルを受信")
        
        # OCR処理実行
        ocr_results = ocr.ocr(files)
        
        # OCR結果をログに保存
        for i, file in enumerate(files):
            log_ocr_processing(
                file.filename, 
                len(ocr_results[i]) if i < len(ocr_results) else 0,
                "success"
            )
        
        return jsonify({
            "status": "success",
            "ocr_results": ocr_results,
            "message": f"✅ {len(files)}個のファイルを処理完了"
        })
        
    except Exception as e:
        print(f"[ERROR] ❌ OCR処理エラー: {str(e)}")
        traceback.print_exc()
        
        # エラーログを保存
        if 'files' in locals():
            for file in files:
                log_ocr_processing(file.filename, 0, "error", str(e))
        
        return jsonify({
            "status": "error",
            "error": str(e),
            "message": "OCR処理中にエラーが発生しました"
        }), 500

# 👥 顧客管理ページ
@main_bp.route("/customers")
def customers():
    """顧客管理画面"""
    return render_template("customer.html")

# 📦 商品管理ページ
@main_bp.route("/products")
def products():
    """商品管理画面"""
    return render_template("product.html")

# 🧾 請求書生成ページ
@main_bp.route("/invoices")
def invoices():
    """請求書生成画面"""
    return render_template("invoice_preview.html")

# 📊 処理履歴ページ
@main_bp.route("/logs")
def logs():
    """処理履歴画面"""
    return render_template("logs.html")

# =====================================
# 👥 顧客管理 API
# =====================================

@main_bp.route("/api/customers", methods=["GET"])
def get_customers():
    """顧客一覧を取得"""
    try:
        with sqlite3.connect("invoice_data.db") as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT customer_id, customer_name, billing_cycle, 
                       payment_method, address, phone_number, created_at
                FROM customers 
                ORDER BY customer_name
            """)
            
            customers = []
            for row in cursor.fetchall():
                customers.append({
                    "customer_id": row[0],
                    "customer_name": row[1],
                    "billing_cycle": row[2],
                    "payment_method": row[3],
                    "address": row[4],
                    "phone_number": row[5],
                    "created_at": row[6]
                })
            
        return jsonify(customers)
        
    except Exception as e:
        print(f"[ERROR] 顧客取得エラー: {str(e)}")
        return jsonify({"error": str(e)}), 500

@main_bp.route("/api/customers", methods=["POST"])
def create_customer():
    """新規顧客を登録"""
    try:
        data = request.get_json()
        
        # 必須項目チェック
        if not data.get("customer_name"):
            return jsonify({"error": "顧客名は必須です"}), 400
        
        with sqlite3.connect("invoice_data.db") as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO customers 
                (customer_name, billing_cycle, payment_method, address, phone_number)
                VALUES (?, ?, ?, ?, ?)
            """, (
                data["customer_name"],
                data.get("billing_cycle", "月末"),
                data.get("payment_method", "現金"),
                data.get("address", ""),
                data.get("phone_number", "")
            ))
            
            customer_id = cursor.lastrowid
            conn.commit()
        
        print(f"[DEBUG] ✅ 新規顧客登録: {data['customer_name']} (ID: {customer_id})")
        
        return jsonify({
            "status": "success",
            "customer_id": customer_id,
            "message": f"顧客「{data['customer_name']}」を登録しました"
        })
        
    except Exception as e:
        print(f"[ERROR] 顧客登録エラー: {str(e)}")
        return jsonify({"error": str(e)}), 500

@main_bp.route("/api/customers/<int:customer_id>", methods=["DELETE"])
def delete_customer(customer_id):
    """顧客を削除"""
    try:
        with sqlite3.connect("invoice_data.db") as conn:
            cursor = conn.cursor()
            
            # 関連する取引データの確認
            cursor.execute("SELECT COUNT(*) FROM transactions WHERE customer_id = ?", (customer_id,))
            transaction_count = cursor.fetchone()[0]
            
            if transaction_count > 0:
                return jsonify({
                    "error": f"この顧客には{transaction_count}件の取引データがあります。先に取引データを削除してください。"
                }), 400
            
            # 顧客削除
            cursor.execute("DELETE FROM customers WHERE customer_id = ?", (customer_id,))
            
            if cursor.rowcount == 0:
                return jsonify({"error": "顧客が見つかりません"}), 404
            
            conn.commit()
        
        print(f"[DEBUG] ✅ 顧客削除: ID {customer_id}")
        
        return jsonify({
            "status": "success",
            "message": "顧客を削除しました"
        })
        
    except Exception as e:
        print(f"[ERROR] 顧客削除エラー: {str(e)}")
        return jsonify({"error": str(e)}), 500

# =====================================
# 📦 商品管理 API
# =====================================

@main_bp.route("/api/products", methods=["GET"])
def get_products():
    """商品一覧を取得"""
    try:
        with sqlite3.connect("invoice_data.db") as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT product_id, product_name, base_price, category, unit, created_at
                FROM products 
                ORDER BY category, product_name
            """)
            
            products = []
            for row in cursor.fetchall():
                products.append({
                    "product_id": row[0],
                    "product_name": row[1],
                    "base_price": row[2],
                    "category": row[3],
                    "unit": row[4],
                    "created_at": row[5]
                })
            
        return jsonify(products)
        
    except Exception as e:
        print(f"[ERROR] 商品取得エラー: {str(e)}")
        return jsonify({"error": str(e)}), 500

@main_bp.route("/api/products", methods=["POST"])
def create_product():
    """新規商品を登録"""
    try:
        data = request.get_json()
        
        # 必須項目チェック
        if not data.get("product_name"):
            return jsonify({"error": "商品名は必須です"}), 400
        if not data.get("base_price"):
            return jsonify({"error": "価格は必須です"}), 400
        
        with sqlite3.connect("invoice_data.db") as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO products 
                (product_name, base_price, category, unit)
                VALUES (?, ?, ?, ?)
            """, (
                data["product_name"],
                float(data["base_price"]),
                data.get("category", "その他"),
                data.get("unit", "個")
            ))
            
            product_id = cursor.lastrowid
            conn.commit()
        
        print(f"[DEBUG] ✅ 新規商品登録: {data['product_name']} (ID: {product_id})")
        
        return jsonify({
            "status": "success",
            "product_id": product_id,
            "message": f"商品「{data['product_name']}」を登録しました"
        })
        
    except Exception as e:
        print(f"[ERROR] 商品登録エラー: {str(e)}")
        return jsonify({"error": str(e)}), 500

@main_bp.route("/api/products/<int:product_id>", methods=["DELETE"])
def delete_product(product_id):
    """商品を削除"""
    try:
        with sqlite3.connect("invoice_data.db") as conn:
            cursor = conn.cursor()
            
            # 関連する取引データの確認
            cursor.execute("SELECT COUNT(*) FROM transactions WHERE product_id = ?", (product_id,))
            transaction_count = cursor.fetchone()[0]
            
            if transaction_count > 0:
                return jsonify({
                    "error": f"この商品には{transaction_count}件の取引データがあります。先に取引データを削除してください。"
                }), 400
            
            # 商品削除
            cursor.execute("DELETE FROM products WHERE product_id = ?", (product_id,))
            
            if cursor.rowcount == 0:
                return jsonify({"error": "商品が見つかりません"}), 404
            
            conn.commit()
        
        print(f"[DEBUG] ✅ 商品削除: ID {product_id}")
        
        return jsonify({
            "status": "success",
            "message": "商品を削除しました"
        })
        
    except Exception as e:
        print(f"[ERROR] 商品削除エラー: {str(e)}")
        return jsonify({"error": str(e)}), 500

# =====================================
# 🧾 請求書生成 API
# =====================================

@main_bp.route("/api/invoice-preview", methods=["POST"])
def invoice_preview():
    """請求書プレビューデータを取得"""
    try:
        data = request.get_json()
        customer_id = data.get("customer_id")
        start_date = data.get("start_date")
        end_date = data.get("end_date")
        billing_date = data.get("billing_date", datetime.now().strftime("%Y-%m-%d"))
        
        if not all([customer_id, start_date, end_date]):
            return jsonify({"error": "必須パラメータが不足しています"}), 400
        
        # 請求書データを取得
        invoice_data = get_invoice_data(customer_id, start_date, end_date)
        
        if not invoice_data:
            return jsonify({
                "error": "指定期間に取引データがありません",
                "customer_id": customer_id,
                "period": f"{start_date} ～ {end_date}"
            }), 404
        
        # レスポンス用データを構築
        response_data = {
            "customer_name": invoice_data[0][0],
            "customer_address": invoice_data[0][1],
            "customer_phone": invoice_data[0][2],
            "start_date": start_date,
            "end_date": end_date,
            "billing_date": billing_date,
            "items": []
        }
        
        # 取引項目を整理
        for row in invoice_data:
            response_data["items"].append({
                "product_name": row[3],
                "quantity": row[4],
                "unit_price": row[5],
                "total_amount": row[6],
                "size_content": row[7] or row[8],  # タイヤサイズまたは作業内容
                "transaction_date": row[9],
                "note": ""
            })
        
        print(f"[DEBUG] 📊 請求書プレビュー生成: 顧客ID {customer_id}, {len(response_data['items'])}件")
        
        return jsonify(response_data)
        
    except Exception as e:
        print(f"[ERROR] 請求書プレビューエラー: {str(e)}")
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@main_bp.route("/api/generate-invoice", methods=["POST"])
def generate_invoice_file():
    """Excel請求書ファイルを生成・ダウンロード"""
    try:
        data = request.get_json()
        customer_id = data.get("customer_id")
        start_date = data.get("start_date")
        end_date = data.get("end_date")
        
        if not all([customer_id, start_date, end_date]):
            return jsonify({"error": "必須パラメータが不足しています"}), 400
        
        # 一時ディレクトリに請求書を生成
        temp_dir = tempfile.mkdtemp()
        
        try:
            filepath, message = generate_invoice(customer_id, start_date, end_date, temp_dir)
            
            if not filepath:
                return jsonify({"error": message}), 400
            
            print(f"[DEBUG] 📥 Excel請求書生成: {filepath}")
            
            # ファイルをダウンロード用に送信
            return send_file(
                filepath,
                as_attachment=True,
                download_name=os.path.basename(filepath),
                mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            )
            
        finally:
            # 一時ファイルをクリーンアップ（少し遅らせて）
            # 実際の本番環境では、バックグラウンドタスクで処理することを推奨
            pass
        
    except Exception as e:
        print(f"[ERROR] Excel生成エラー: {str(e)}")
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

# =====================================
# 📊 ログ・履歴管理 API
# =====================================

@main_bp.route("/api/logs/ocr", methods=["GET"])
def get_ocr_logs():
    """OCR処理ログを取得"""
    try:
        with sqlite3.connect("invoice_data.db") as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT log_id, file_name, processing_time, texts_detected, 
                       texts_extracted, processing_status, error_message, created_at
                FROM ocr_logs 
                ORDER BY created_at DESC
                LIMIT 100
            """)
            
            logs = []
            for row in cursor.fetchall():
                logs.append({
                    "log_id": row[0],
                    "file_name": row[1],
                    "processing_time": row[2],
                    "texts_detected": row[3],
                    "texts_extracted": row[4],
                    "processing_status": row[5],
                    "error_message": row[6],
                    "created_at": row[7]
                })
            
        return jsonify(logs)
        
    except Exception as e:
        print(f"[ERROR] ログ取得エラー: {str(e)}")
        return jsonify({"error": str(e)}), 500

@main_bp.route("/api/logs/invoices", methods=["GET"])
def get_invoice_logs():
    """請求書生成ログを取得"""
    try:
        with sqlite3.connect("invoice_data.db") as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT i.invoice_id, c.customer_name, i.billing_period_start, 
                       i.billing_period_end, i.total_amount, i.invoice_file_path, 
                       i.generated_at
                FROM invoice_logs i
                LEFT JOIN customers c ON i.customer_id = c.customer_id
                ORDER BY i.generated_at DESC
                LIMIT 50
            """)
            
            logs = []
            for row in cursor.fetchall():
                logs.append({
                    "invoice_id": row[0],
                    "customer_name": row[1],
                    "billing_period_start": row[2],
                    "billing_period_end": row[3],
                    "total_amount": row[4],
                    "invoice_file_path": row[5],
                    "generated_at": row[6]
                })
            
        return jsonify(logs)
        
    except Exception as e:
        print(f"[ERROR] 請求書ログ取得エラー: {str(e)}")
        return jsonify({"error": str(e)}), 500

# =====================================
# 🛠️ ユーティリティ関数
# =====================================

def log_ocr_processing(filename, texts_extracted, status, error_message=None):
    """OCR処理ログを保存"""
    try:
        with sqlite3.connect("invoice_data.db") as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO ocr_logs 
                (file_name, texts_extracted, processing_status, error_message)
                VALUES (?, ?, ?, ?)
            """, (filename, texts_extracted, status, error_message))
            conn.commit()
    except Exception as e:
        print(f"[ERROR] ログ保存エラー: {str(e)}")

def log_invoice_generation(customer_id, start_date, end_date, total_amount, filepath):
    """請求書生成ログを保存"""
    try:
        with sqlite3.connect("invoice_data.db") as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO invoice_logs 
                (customer_id, billing_period_start, billing_period_end, total_amount, invoice_file_path)
                VALUES (?, ?, ?, ?, ?)
            """, (customer_id, start_date, end_date, total_amount, filepath))
            conn.commit()
    except Exception as e:
        print(f"[ERROR] 請求書ログ保存エラー: {str(e)}")

# =====================================
# 🔧 開発用API（テスト・デバッグ用）
# =====================================

@main_bp.route("/api/dev/reset-db", methods=["POST"])
def reset_database():
    """データベースをリセット（開発用）"""
    try:
        # 本番環境では無効化すること
        if os.environ.get("FLASK_ENV") != "development":
            return jsonify({"error": "本番環境では実行できません"}), 403
        
        init_database()
        
        return jsonify({
            "status": "success",
            "message": "データベースをリセットしました"
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@main_bp.route("/api/dev/sample-data", methods=["POST"])
def insert_sample_data():
    """サンプルデータを投入（開発用）"""
    try:
        from backend.db import insert_sample_data
        insert_sample_data()
        
        return jsonify({
            "status": "success",
            "message": "サンプルデータを投入しました"
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# =====================================
# 🏗️ 初期化処理（Flask 2.2+ 対応）
# =====================================

def initialize_app_data():
    """アプリケーション初期化（Flask 2.2+対応）"""
    try:
        print("[DEBUG] 🏗️ アプリケーション初期化開始")
        
        # データベース初期化
        init_database()
        
        # 必要なディレクトリを作成
        directories = ["uploads", "invoices", "logs"]
        for dir_name in directories:
            os.makedirs(dir_name, exist_ok=True)
        
        print("[DEBUG] ✅ アプリケーション初期化完了")
        
    except Exception as e:
        print(f"[ERROR] ❌ 初期化エラー: {str(e)}")

# 初期化処理をブループリント登録時に実行
initialize_app_data()