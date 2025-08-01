import os
import logging
import io
from uuid import uuid4
from flask import Flask, request, jsonify, send_from_directory, url_for
from pypdf import PdfReader
from PIL import Image

app = Flask(__name__)

# Configuration
UPLOAD_FOLDER = "uploads"
EXTRACTED_FOLDER = "images"
ALLOWED_EXTENSIONS = {"pdf"}
MAX_FILE_SIZE = 2 * 1024 * 1024  # 2 MB limit

# Set Flask max upload size
app.config["MAX_CONTENT_LENGTH"] = MAX_FILE_SIZE

# Ensure directories exist
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(EXTRACTED_FOLDER, exist_ok=True)

def extract_images_from_pdf(pdf_file_path: str, output_path: str):
    """Extract images from a PDF and rename first two images as user-img.png and sign-img.png."""
    try:
        reader = PdfReader(pdf_file_path)
        seen_images = set()
        extracted_files = []
        image_count = 0

        for page in reader.pages:
            for image in page.images:
                image_data = image.data
                image_hash = hash(image_data)

                if image_hash in seen_images:
                    continue

                seen_images.add(image_hash)
                ext = os.path.splitext(image.name)[1].lower()

                if ext == ".jpeg":
                    ext = ".jpg"
                elif ext == ".jp2":
                    try:
                        with Image.open(io.BytesIO(image_data)) as img:
                            if img.mode == "RGBA":
                                img = img.convert("RGB")
                            ext = ".png"
                            image_data = io.BytesIO()
                            img.save(image_data, format="PNG")
                            image_data = image_data.getvalue()
                    except Exception as e:
                        logging.error(f"Failed To Convert Jp2 to PNG")
                        continue

                # Naming logic
                if image_count == 0:
                    image_filename = f"user-img-{str(uuid4())[:10]}{ext}"
                elif image_count == 1:
                    image_filename = f"sign-img-{str(uuid4())[:10]}{ext}"
                else:
                    image_filename = f"{uuid4()}{ext.lower()}"

                image_count += 1

                file_path = os.path.join(output_path, image_filename)
                with open(file_path, "wb") as fp:
                    fp.write(image_data)

                extracted_files.append(image_filename)

        return extracted_files

    except Exception as e:
        logging.error(f"Failed to extract images from {pdf_file_path}: {e}")
        return []

@app.route("/")
def home():
    return jsonify({"ststus": "Images Extract Successfully Activate"})

@app.route("/images", methods=["POST"])
def upload_file():
    """Handle file upload and extract images."""
    if "file" not in request.files:
        return jsonify({"error": "No file Part"}), 400

    file = request.files["file"]

    if file.filename == "":
        return jsonify({"message": "No Selected File"}), 400

    # Check file size
    file.seek(0, os.SEEK_END)  # Move to end of file
    file_size = file.tell()  # Get file size
    file.seek(0)  # Reset file pointer

    if file_size > MAX_FILE_SIZE:
        return jsonify({"message": "File Size Exceeds 2 MB Limit"}), 400

    if file and file.filename.split(".")[-1].lower() in ALLOWED_EXTENSIONS:
        file_path = os.path.join(UPLOAD_FOLDER, f"{uuid4()}.pdf")
        file.save(file_path)

        extracted_images = extract_images_from_pdf(file_path, EXTRACTED_FOLDER)

        # **Delete the PDF after processing**
        try:
            os.remove(file_path)
        except Exception as e:
            logging.error(f"Failed To Delete PDF: {e}")

        if extracted_images:
            # Modify the image response to match the requested structure
            image_urls = {
                "user-image": url_for("download_file", filename=extracted_images[0], _external=True),
                "sign-image": url_for("download_file", filename=extracted_images[1], _external=True)
            }
            return jsonify({"message": "Images extracted successfully", "images": image_urls})

        return jsonify({"message": "No Images Found In The PDF"}), 200

    return jsonify({"message": "Invalid File Type"}), 400

@app.route("/images/<filename>")
def download_file(filename):
    """Serve extracted images."""
    return send_from_directory(EXTRACTED_FOLDER, filename)

from flask import render_template

@app.route("/upload")
def upload_page():
    return render_template("index.html")

if __name__ == "__main__":
    app.run(debug=True)
