from flask import Flask
#bp登録
from backend.main import main_bp
#from backend.ocr import ocr_bp

def create_app():
    app = Flask(__name__,
                template_folder="../frontend/templates",
                static_folder="../frontend/static"
                )
    app.register_blueprint(main_bp)
    #app.register_blueprint(ocr_bp)
    return app