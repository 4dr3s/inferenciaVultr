from dotenv import load_dotenv
import os
from flask import Flask, request, render_template, jsonify, send_file
import requests
import b2sdk.v2
import io

load_dotenv()

app = Flask(__name__)

def accound_credentials():
    info = b2sdk.v2.InMemoryAccountInfo()
    api = b2sdk.v2.B2Api(info)
    appKeyId = os.getenv("ACCOUNT_ID")
    appKey = os.getenv("APPLICATION_KEY")
    api.authorize_account("production", appKeyId, appKey)
    return api

@app.route('/')
def index():
    return render_template('upload.html')

@app.route("/generate_and_upload_audio", methods=["POST"])
def generate_and_upload_audio():
    input_text = request.form.get('input_text')

    if not input_text:
        return render_template('upload.html', error="Por favor ingresa un texto para convertir a audio.")

    BASE_URL = 'https://api.vultrinference.com/v1/audio/speech'
    payload = {
        "model": "bark-small",
        "input": input_text,
        "voice": "es_speaker_1"
    }

    headers = {
        'Authorization': f'Bearer {os.getenv("API_KEY")}',
        'Content-Type': 'application/json'
    }

    response = requests.post(BASE_URL, json=payload, headers=headers)

    if response.status_code == 200:
        audio_data = io.BytesIO(response.content)
        
        api = accound_credentials()
        bucket = api.get_bucket_by_name(os.getenv("BUCKET_NAME"))
        
        file_name = 'output_audio.mp3'
        bucket.upload_bytes(audio_data.read(), file_name, file_name)

        return f"¡Audio generado y guardado exitosamente en Backblaze B2 como '{file_name}'!"

    else:
        return render_template('upload.html', error=f"Error al generar el audio: {response.status_code}. {response.json()}")

@app.route("/list_files")
def list_files():
    api = accound_credentials()
    bucket = api.get_bucket_by_name(os.getenv("BUCKET_NAME"))
    files = list(bucket.ls())

    file_info = []
    for file, _ in files:
        file_info.append({
            'name': file.file_name,
            'size': file.size
        })

    return render_template('list_files.html', files=file_info)

@app.route("/download/<file_name>")
def download_file(file_name):
    try:
        api = accound_credentials()
        bucket = api.get_bucket_by_name(os.getenv("BUCKET_NAME"))
        
        downloaded_file = bucket.download_file_by_name(file_name)
        file_data = downloaded_file.read()
        
        return send_file(io.BytesIO(file_data), as_attachment=True, download_name=file_name)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(debug=True)
