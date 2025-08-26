from backend import app
from flask import render_template, jsonify

@app.route("/")
def index():
    return render_template(
        "index.html"
    )

@app.route("/uploads", methods = ["POST"])
def uploads():
    return jsonify({"message": "/uploads通過！"})