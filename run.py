"""🚀 アプリケーション起動スクリプト"""

import sys
import os

# パスを追加
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from backend import create_dev_app, print_app_info

if __name__ == "__main__":
    try:
        print("🚀 納品書OCRツール起動中...")
        
        # アプリケーション作成
        app = create_dev_app()
        
        # 情報表示
        print_app_info(app)
        
        # サーバー起動
        app.run(
            host='127.0.0.1',
            port=5000,
            debug=True,
            threaded=True
        )
        
    except Exception as e:
        print(f"❌ 起動エラー: {str(e)}")
        import traceback
        traceback.print_exc()