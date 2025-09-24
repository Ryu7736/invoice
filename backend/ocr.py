from flask import Blueprint,jsonify
from pdf2image import convert_from_bytes
import easyocr
import numpy as np
#以下のルーティングは開発後半で、、まずは/uploadsに統合して管理する。
# ocr_bp = Blueprint("ocr",__name__)

ocr_model = easyocr.Reader(["ja","en"])

# @ocr_bp.route("/ocr", methods = ["POST"])
def ocr(files):
    results = []
    for f in files:
        if not f.filename:
            results.append("空ファイルをスキップしました。")
            continue
        pdf_bytes = f.read()
        if not pdf_bytes:
            results.append("ファイルの読み取りに失敗")
            continue

        imgs = convert_from_bytes(pdf_bytes, dpi =200, fmt = "png")

        for img in imgs:
            img_array = np.array(img)
            ocr_result = ocr_model.readtext(img_array)
            page_text = []
            for detection in ocr_result:
                bbox, text, confidence = detection
                page_text.append(text)
            results.append(page_text)

    return results