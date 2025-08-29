from flask import Blueprint, render_template, jsonify, request
from backend import ocr

main_bp = Blueprint("main",__name__)

@main_bp.route("/")
def index():
    return render_template(
        "index.html"
    )

@main_bp.route("/uploads", methods = ["POST"])
def uploads():
    files = request.files.getlist("files")
    if not files:
        return jsonify({"error":"no files"})

    ocr_results = ocr.ocr(files)
    return jsonify({"ocr_results":ocr_results})