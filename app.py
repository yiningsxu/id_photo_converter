from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from flask import Flask, abort, jsonify, render_template, request, send_file
from werkzeug.exceptions import RequestEntityTooLarge

from converter import (
    build_print_sheet,
    detect_photo_size,
    image_to_data_url,
    load_uploaded_image,
    save_pdf,
    save_png,
    validate_params,
)

BASE_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = BASE_DIR / "outputs"
OUTPUT_DIR.mkdir(exist_ok=True)
MAX_UPLOAD_MB = 80

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = MAX_UPLOAD_MB * 1024 * 1024


def _checkbox(name: str) -> bool:
    """HTML checkboxes are absent from form data when unchecked."""
    value = request.form.get(name)
    if value is None:
        return False
    return value.lower() in {"1", "true", "yes", "on"}


def _float_form(name: str, default: float) -> float:
    value = request.form.get(name, str(default))
    return float(value)


@app.get("/")
def index():
    return render_template("index.html")


@app.after_request
def add_local_html_headers(response):
    response.headers.setdefault("Access-Control-Allow-Origin", "*")
    return response


@app.errorhandler(RequestEntityTooLarge)
def handle_large_upload(exc):
    return (
        jsonify({"error": f"上传文件过大。请使用不超过 {MAX_UPLOAD_MB} MB 的图片。"}),
        413,
    )


@app.post("/api/detect-photo-size")
def api_detect_photo_size():
    try:
        uploaded = request.files.get("photo")
        if uploaded is None or uploaded.filename == "":
            raise ValueError("请先上传一张证件照。")

        image = load_uploaded_image(uploaded.stream)
        detected = detect_photo_size(image)
        if detected is None:
            return jsonify(
                {
                    "detected": False,
                    "original_px": f"{image.width} x {image.height}",
                    "message": "未能可靠识别成品尺寸，请手动输入宽度和高度。",
                }
            )

        return jsonify(
            {
                "detected": True,
                "original_px": f"{image.width} x {image.height}",
                "size": detected.public_dict(),
            }
        )
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    except Exception as exc:
        app.logger.exception("photo size detection failed")
        return jsonify({"error": f"识别失败：{exc}"}), 500


@app.post("/api/preview")
def api_preview():
    try:
        uploaded = request.files.get("photo")
        if uploaded is None or uploaded.filename == "":
            raise ValueError("请先上传一张证件照。")

        image = load_uploaded_image(uploaded.stream)
        detected = None
        photo_w_value = request.form.get("photo_w_mm", "35")
        photo_h_value = request.form.get("photo_h_mm", "45")
        if _checkbox("auto_detect_photo_size"):
            detected = detect_photo_size(image)
            if detected is not None:
                photo_w_value = detected.width_mm
                photo_h_value = detected.height_mm

        (
            photo_w_mm,
            photo_h_mm,
            paper_w_mm,
            paper_h_mm,
            dpi,
            margin_mm,
            gap_mm,
        ) = validate_params(
            photo_w_value,
            photo_h_value,
            request.form.get("paper_w_mm", "100"),
            request.form.get("paper_h_mm", "148"),
            request.form.get("dpi", "300"),
            request.form.get("margin_mm", "3"),
            request.form.get("gap_mm", "2"),
        )

        anchor_x = max(0.0, min(1.0, _float_form("anchor_x", 50.0) / 100.0))
        anchor_y = max(0.0, min(1.0, _float_form("anchor_y", 50.0) / 100.0))

        result = build_print_sheet(
            image=image,
            photo_w_mm=photo_w_mm,
            photo_h_mm=photo_h_mm,
            paper_w_mm=paper_w_mm,
            paper_h_mm=paper_h_mm,
            dpi=dpi,
            margin_mm=margin_mm,
            gap_mm=gap_mm,
            anchor_x=anchor_x,
            anchor_y=anchor_y,
            auto_paper_orientation=_checkbox("auto_paper_orientation"),
            allow_photo_rotation=_checkbox("allow_photo_rotation"),
            draw_cut_marks=_checkbox("draw_cut_marks"),
        )

        job_id = uuid4().hex
        png_path = OUTPUT_DIR / f"{job_id}.png"
        pdf_path = OUTPUT_DIR / f"{job_id}.pdf"
        save_png(result.layout_sheet, png_path, result.plan.dpi)
        save_pdf(result.layout_sheet, pdf_path, result.plan)

        response = {
            "job_id": job_id,
            "plan": result.plan.public_dict(),
            "crop_box_px": result.crop_box,
            "original_px": f"{image.width} x {image.height}",
            "cropped_px": f"{result.cropped_photo.width} x {result.cropped_photo.height}",
            "detected_photo_size": detected.public_dict() if detected is not None else None,
            "cropped_preview": image_to_data_url(result.cropped_photo, max_side=700),
            "layout_preview": image_to_data_url(result.layout_sheet, max_side=1200),
            "download_png": f"/download/{job_id}/png",
            "download_pdf": f"/download/{job_id}/pdf",
        }
        return jsonify(response)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    except Exception as exc:
        app.logger.exception("conversion failed")
        return jsonify({"error": f"处理失败：{exc}"}), 500


@app.get("/download/<job_id>/<kind>")
def download(job_id: str, kind: str):
    if not job_id.isalnum() or kind not in {"png", "pdf"}:
        abort(404)
    path = OUTPUT_DIR / f"{job_id}.{kind}"
    if not path.exists():
        abort(404)
    mimetype = "image/png" if kind == "png" else "application/pdf"
    return send_file(
        path,
        mimetype=mimetype,
        as_attachment=True,
        download_name=f"id_photo_sheet_{job_id}.{kind}",
    )


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)
