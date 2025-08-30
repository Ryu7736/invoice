from flask import Flask, request, jsonify
from datetime import datetime
import os
import logging
import sqlite3

# 🔧 ブループリント登録
from backend.main import main_bp

def create_app(config_name='development'):
    """🏭 Flaskアプリケーションファクトリ"""
    
    # 📁 Flaskアプリケーション作成
    app = Flask(__name__,
                template_folder="../frontend/templates",
                static_folder="../frontend/static"
                )
    
    # ⚙️ アプリケーション設定
    configure_app(app, config_name)
    
    # 📋 ブループリント登録
    register_blueprints(app)
    
    # 🛡️ セキュリティ設定
    configure_security(app)
    
    # 📊 ログ設定
    configure_logging(app)
    
    # 🚨 エラーハンドラー設定
    register_error_handlers(app)
    
    # 🔧 リクエスト処理設定
    configure_request_handlers(app)
    
    return app

def configure_app(app, config_name):
    """⚙️ アプリケーション設定"""
    
    # 🔑 基本設定
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
    app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB制限
    
    # 📁 ファイルアップロード設定
    app.config['UPLOAD_FOLDER'] = os.path.join(os.getcwd(), 'uploads')
    app.config['INVOICE_FOLDER'] = os.path.join(os.getcwd(), 'invoices')
    app.config['LOG_FOLDER'] = os.path.join(os.getcwd(), 'logs')
    
    # 📄 許可ファイル形式
    app.config['ALLOWED_EXTENSIONS'] = {'pdf', 'png', 'jpg', 'jpeg', 'gif', 'bmp', 'tiff'}
    
    # 🗂️ データベース設定
    app.config['DATABASE_PATH'] = os.path.join(os.getcwd(), 'invoice_data.db')
    
    # 📊 環境別設定
    if config_name == 'development':
        app.config['DEBUG'] = True
        app.config['TESTING'] = False
    elif config_name == 'testing':
        app.config['DEBUG'] = False
        app.config['TESTING'] = True
        app.config['DATABASE_PATH'] = ':memory:'
    elif config_name == 'production':
        app.config['DEBUG'] = False
        app.config['TESTING'] = False
        app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY')
        if not app.config['SECRET_KEY']:
            raise ValueError("本番環境ではSECRET_KEYの設定が必須です")
    
    print(f"[CONFIG] ⚙️ 設定完了: {config_name}モード")

def register_blueprints(app):
    """📋 ブループリント登録"""
    try:
        # メインブループリント
        app.register_blueprint(main_bp)
        
        print("[BP] 📋 ブループリント登録完了")
        
    except Exception as e:
        print(f"[ERROR] ❌ ブループリント登録エラー: {str(e)}")
        raise

def configure_security(app):
    """🛡️ セキュリティ設定"""
    
    @app.after_request
    def after_request(response):
        """🔒 セキュリティヘッダーを追加"""
        
        # CORS設定（開発環境のみ）
        if app.config['DEBUG']:
            response.headers['Access-Control-Allow-Origin'] = '*'
            response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, OPTIONS'
            response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
        
        # セキュリティヘッダー
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'DENY'
        response.headers['X-XSS-Protection'] = '1; mode=block'
        
        return response
    
    def allowed_file(filename):
        """📄 許可されたファイル形式かチェック"""
        return '.' in filename and \
               filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']
    
    # ユーティリティ関数をアプリケーションコンテキストに追加
    app.allowed_file = allowed_file
    
    print("[SECURITY] 🛡️ セキュリティ設定完了")

def configure_logging(app):
    """📊 ログ設定"""
    
    if not app.config['DEBUG']:
        # 本番環境でのログ設定
        log_file = os.path.join(app.config.get('LOG_FOLDER', 'logs'), 'invoice_app.log')
        
        # ディレクトリ作成
        os.makedirs(os.path.dirname(log_file), exist_ok=True)
        
        # ファイルハンドラーを設定
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(logging.INFO)
        
        # ログフォーマットを設定
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        file_handler.setFormatter(formatter)
        
        # アプリケーションロガーに追加
        app.logger.addHandler(file_handler)
        app.logger.setLevel(logging.INFO)
        
        app.logger.info('🚀 納品書OCRツール起動')
    
    print("[LOG] 📊 ログ設定完了")

def register_error_handlers(app):
    """🚨 エラーハンドラー登録"""
    
    @app.errorhandler(404)
    def not_found_error(error):
        """📄 404エラーハンドラー"""
        return jsonify({
            'error': 'ページが見つかりません',
            'message': 'リクエストされたリソースが存在しません',
            'status_code': 404
        }), 404
    
    @app.errorhandler(500)
    def internal_error(error):
        """🔥 500エラーハンドラー"""
        app.logger.error(f'サーバーエラー: {str(error)}')
        return jsonify({
            'error': 'サーバー内部エラー',
            'message': 'サーバーで問題が発生しました。しばらく時間をおいて再試行してください。',
            'status_code': 500
        }), 500
    
    @app.errorhandler(413)
    def too_large(error):
        """📦 ファイルサイズ超過エラー"""
        return jsonify({
            'error': 'ファイルサイズが大きすぎます',
            'message': f'ファイルサイズは{app.config["MAX_CONTENT_LENGTH"] // (1024*1024)}MB以下にしてください',
            'status_code': 413
        }), 413
    
    print("[ERROR] 🚨 エラーハンドラー登録完了")

def configure_request_handlers(app):
    """🔧 リクエスト処理設定"""
    
    @app.before_request
    def before_request():
        """📥 リクエスト前処理"""
        
        # リクエストログ（デバッグモードのみ）
        if app.config['DEBUG']:
            print(f"[REQUEST] 📥 {request.method} {request.path}")
    
    print("[REQUEST] 🔧 リクエスト処理設定完了")

# 🧪 開発用ヘルパー関数

def create_test_app():
    """🧪 テスト用アプリケーション作成"""
    return create_app('testing')

def create_dev_app():
    """🔧 開発用アプリケーション作成"""
    return create_app('development')

def create_prod_app():
    """🚀 本番用アプリケーション作成"""
    return create_app('production')

# 📊 アプリケーション情報表示

def print_app_info(app):
    """📊 アプリケーション情報を表示"""
    print("\n" + "="*50)
    print("🚛 納品書OCRツール 起動情報")
    print("="*50)
    print(f"🔧 デバッグ: {app.config['DEBUG']}")
    print(f"📁 アップロードフォルダ: {app.config.get('UPLOAD_FOLDER', 'uploads')}")
    print(f"🗂️ データベース: {app.config.get('DATABASE_PATH', 'invoice_data.db')}")
    print("="*50)
    print("✅ アプリケーション起動完了")
    print("="*50 + "\n")

# 🚀 メイン実行部分（デバッグ用）

if __name__ == "__main__":
    # 開発用サーバー起動
    app = create_dev_app()
    print_app_info(app)
    
    # 🔧 開発サーバー起動
    app.run(debug=True)