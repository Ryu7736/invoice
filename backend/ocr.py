from flask import Blueprint,jsonify

ocr_bp = Blueprint("ocr",__name__)

@ocr_bp.route("/ocr", methods = ["POST"])
def ocr():
    print("def")
    return jsonify({"ocrResult":"ocr関数通過！"})