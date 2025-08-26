from flask import jsonify 
from backend import app

@app.route("/ocr", methods = ["POST"])
def ocr():
    print("def")
    return jsonify({"ocrResult":"ocr関数通過！"})