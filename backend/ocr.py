from flask import Blueprint,jsonify
from pdf2image import convert_from_bytes
from paddleocr import PaddleOCR
import numpy as np
#以下のルーティングは開発後半で、、まずは/uploadsに統合して管理する。
# ocr_bp = Blueprint("ocr",__name__)

ocr_model = PaddleOCR(lang= "japan", use_angle_cls = True)
# @ocr_bp.route("/ocr", methods = ["POST"])
def ocr(files):
    results = []
    for f in files:
        pdf_bytes = f.read()
        if not pdf_bytes:
            return "f.read()失敗"
        imgs = convert_from_bytes(pdf_bytes, dpi =200, fmt = "png")

        for img in imgs:
            img_array = np.array(img)
            ocr_result = ocr_model.ocr(img_array)
            page_texts = []
            for line in ocr_result[0]:
                text = line[1][0]
                page_texts.append(text)
                print(page_texts)

            results.append(page_texts)
    return results