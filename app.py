import os
import logging
from uuid import uuid4
from flask import Flask, request, jsonify, send_from_directory, url_for, render_template
from pypdf import PdfReader

app = Flask(__name__)

# কনফিগারেশন
UPLOAD_FOLDER = "uploads"
EXTRACTED_FOLDER = "images"
ALLOWED_EXTENSIONS = {"pdf"}
MAX_FILE_SIZE = 2 * 1024 * 1024  # 2MB limit

app.config["MAX_CONTENT_LENGTH"] = MAX_FILE_SIZE

# ফোল্ডার তৈরি
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(EXTRACTED_FOLDER, exist_ok=True)


def extract_images_from_pdf(pdf_file_path: str, output_path: str):
    """PDF থেকে সব ইমেজ বের করে ফাইল হিসেবে সেভ করবে"""
    try:
        reader = PdfReader(pdf_file_path)
        extracted_files = []

        for page in reader.pages:
            for image in page.images:
                ext = os.path.splitext(image.name)[1].lower()
                if not ext:
                    ext = ".png"

                if ext == ".jpeg":
                    ext = ".jpg"

                image_data = image.data

                file_name = f"{uuid4()}{ext}"
                file_path = os.path.join(output_path, file_name)

                with open(file_path, "wb") as fp:
                    fp.write(image_data)

                extracted_files.append(file_name)

        return extracted_files

    except Exception as e:
        logging.error(f"Failed to extract images from {pdf_file_path}: {e}")
        return []


@app.route("/")
def home():
    return jsonify({"status": "Images Extract API Active"})


@app.route("/images", methods=["POST"])
def upload_file():
    """PDF আপলোড এবং ইমেজ এক্সট্রাক্ট হ্যান্ডেল করবে"""
    if "file" not in request.files:
        return jsonify({"error": "No file Part"}), 400

    file = request.files["file"]

    if file.filename == "":
        return jsonify({"message": "No Selected File"}), 400

    # ফাইল সাইজ চেক
    file.seek(0, os.SEEK_END)
    file_size = file.tell()
    file.seek(0)

    if file_size > MAX_FILE_SIZE:
        return jsonify({"message": "File Size Exceeds 2 MB Limit"}), 400

    # ফাইল টাইপ চেক
    if file and file.filename.split(".")[-1].lower() in ALLOWED_EXTENSIONS:
        file_path = os.path.join(UPLOAD_FOLDER, f"{uuid4()}.pdf")
        file.save(file_path)

        extracted_images = extract_images_from_pdf(file_path, EXTRACTED_FOLDER)

        # প্রসেস শেষে PDF ডিলিট
        try:
            os.remove(file_path)
        except Exception as e:
            logging.error(f"Failed To Delete PDF: {e}")

        if extracted_images:
            image_urls = {}

            # প্রথম ইমেজ => user-image
            image_urls["user-image"] = url_for("download_file", filename=extracted_images[0], _external=True)

            # শেষ ইমেজ => sign-image (যদি একাধিক থাকে)
            if len(extracted_images) > 1:
                image_urls["sign-image"] = url_for("download_file", filename=extracted_images[-1], _external=True)

            return jsonify({"message": "Images extracted successfully", "images": image_urls})

        return jsonify({"message": "No Images Found In The PDF"}), 200

    return jsonify({"message": "Invalid File Type"}), 400


@app.route("/images/<filename>")
def download_file(filename):
    """Extracted ইমেজ ডাউনলোড"""
    return send_from_directory(EXTRACTED_FOLDER, filename)


@app.route("/upload")
def upload_page():
    return render_template("index.html")


if __name__ == "__main__":
    app.run(debug=True)
