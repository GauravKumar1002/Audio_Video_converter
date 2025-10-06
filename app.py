from flask import Flask, request, send_file, abort
import os
import subprocess
from werkzeug.utils import secure_filename
from pathlib import Path
import uuid

app = Flask(__name__)
UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# Basic list of supported formats (containers / extension). See docs for full details.
SUPPORTED_INPUT_FORMATS = set(["mp4","mkv","mov","avi","flv","wmv","webm","mpeg","mpg","3gp","m4v","ts","mts","vob","ogv","qt","rm","rmvb","ivf","f4v"])
SUPPORTED_OUTPUT_FORMATS = set(["mp4","mkv","avi","flv","wmv","webm","mpeg","mpg","3gp","mov","m4v","ts","ogg","mp3","wav","aac","flac","opus","amr","wma"])

def allowed(in_ext, out_ext):
    return in_ext.lower() in SUPPORTED_INPUT_FORMATS and out_ext.lower() in SUPPORTED_OUTPUT_FORMATS

@app.route("/convert", methods=["POST"])
def convert():
    """
    Expects multipart/form-data with:
    - file: the uploaded video file
    - target_format: the desired output extension (e.g., mp4, mp3)
    Optional:
    - filename: desired output filename without extension
    """
    if "file" not in request.files:
        return {"error":"no file part"}, 400
    f = request.files["file"]
    if f.filename == "":
        return {"error":"no selected file"}, 400
    target_format = request.form.get("target_format")
    if not target_format:
        return {"error":"target_format is required (e.g., mp4, mp3)"}, 400
    filename = secure_filename(f.filename)
    uid = uuid.uuid4().hex
    in_path = os.path.join(UPLOAD_DIR, uid + "_" + filename)
    f.save(in_path)

    in_ext = Path(filename).suffix.lstrip(".").lower()
    out_ext = target_format.lower()

    if not allowed(in_ext, out_ext):
        return {"error":f"unsupported conversion: {in_ext} -> {out_ext}"}, 400

    # build output filename
    base_out_name = request.form.get("filename", Path(filename).stem)
    out_name = f"{base_out_name}.{out_ext}"
    out_path = os.path.join(UPLOAD_DIR, uid + "_" + out_name)

    # Use ffmpeg (must be installed on the host) for conversion.
    # For audio extraction (video -> audio) we remove video stream with -vn.
    try:
        if out_ext in ("mp3","wav","aac","flac","ogg","opus","amr","wma"):
            # extract audio
            cmd = ["ffmpeg", "-y", "-i", in_path, "-vn", out_path]
        else:
            # container / video conversion
            cmd = ["ffmpeg", "-y", "-i", in_path, out_path]
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=90)
        if proc.returncode != 0:
            # include ffmpeg stderr for debugging
            return {"error":"ffmpeg failed", "details": proc.stderr}, 500
    except Exception as e:
        return {"error":"conversion failed", "details": str(e)}, 500

    return send_file(out_path, as_attachment=True, download_name=out_name)

@app.route("/formats", methods=["GET"])
def formats():
    return {
        "supported_input_formats": sorted(list(SUPPORTED_INPUT_FORMATS)),
        "supported_output_formats": sorted(list(SUPPORTED_OUTPUT_FORMATS))
    }

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001, debug=True)
