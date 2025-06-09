#!/usr/bin/env python3
import os
import subprocess
import uuid
import base64
import re
from flask import Flask, request, send_file, jsonify

app = Flask(__name__)

# Create temporary directories for uploads and conversions
os.makedirs('/app/uploads', exist_ok=True)
os.makedirs('/app/converted', exist_ok=True)

def fixBase64Padding(encoded_str):
    # Remove specific patterns of repeated characters
    pattern = r'A+?=*$'
    encoded_str = re.sub(pattern, '', encoded_str)
    # Calculate missing padding
    missing_padding = len(encoded_str) % 4
    if missing_padding != 0:
        # Add padding to make it a multiple of 4
        encoded_str += '=' * (4 - missing_padding)
    return encoded_str

def base64_to_silk(base64_data, output_file):
    try:
        # Clean the base64 data (remove whitespace)
        clean_base64 = re.sub(r'\s+', '', base64_data).strip()
        # Fix base64 padding
        clean_base64 = fixBase64Padding(clean_base64)
        # Check if it's valid base64
        base64_regex = r'^[A-Za-z0-9+/]*={0,2}$'
        if not re.match(base64_regex, clean_base64):
            print('Error: Invalid base64 format')
            return False
        # Decode base64 to binary
        try:
            audio_buffer = base64.b64decode(clean_base64)
        except Exception as e:
            print(f'Base64 decoding failed: {str(e)}')
            return False
        # Check for SILK headers
        silk_headers = [
            b'#!SILK_V3',
            b'\x02#!SILK_V3'
        ]
        is_silk = False
        for header in silk_headers:
            if audio_buffer.startswith(header):
                is_silk = True
                break
        if not is_silk:
            print('Warning: Data may not be in standard SILK format, but will save anyway')
        # Write the binary data to file
        with open(output_file, 'wb') as f:
            f.write(audio_buffer)
        print(f'Successfully saved to: {output_file}')
        return True
    except Exception as e:
        print(f'Conversion failed: {str(e)}')
        return False

@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({"status": "ok"})

@app.route('/convert', methods=['POST'])
def convert_file():
    # Check if the request has a file part or base64 data
    if 'file' in request.files:
        # Original file upload method
        file = request.files['file']
        # If user does not select file, browser also submits an empty part without filename
        if file.filename == '':
            return jsonify({"error": "No selected file"}), 400
        # Generate a unique ID for this conversion to avoid filename conflicts
        unique_id = str(uuid.uuid4())
        input_path = os.path.join('/app/uploads', f"{unique_id}_{file.filename}")
        # Save the uploaded file
        file.save(input_path)
        # Get the output format (default to mp3)
        output_format = request.form.get('format', 'mp3')
        # Construct the output filename
        output_filename = os.path.splitext(os.path.basename(file.filename))[0] + f".{output_format}"
    
    elif 'base64_data' in request.json:
        # New method: Convert base64 data to SILK file
        base64_data = request.json['base64_data']
        # Generate a unique ID for this conversion
        unique_id = str(uuid.uuid4())
        input_path = os.path.join('/app/uploads', f"{unique_id}.slk")
        # Convert base64 to SILK file
        success = base64_to_silk(base64_data, input_path)
        if not success:
            return jsonify({"error": "Failed to convert base64 data to SILK"}), 400
        # Get the output format (default to mp3)
        output_format = request.json.get('format', 'mp3')
        # Construct the output filename
        output_filename = f"audio.{output_format}"
    else:
        return jsonify({"error": "No file or base64_data provided"}), 400
    
    # Run the conversion script
    try:
        subprocess.run([
            "sh", "/app/silk.sh", input_path, output_format
        ], check=True)
        # Path to the converted file
        converted_file_path = os.path.splitext(input_path)[0] + f".{output_format}"
        if not os.path.exists(converted_file_path):
            return jsonify({"error": "Conversion failed"}), 500
        # Return the converted file
        return send_file(
            converted_file_path,
            as_attachment=True,
            download_name=output_filename,
            mimetype=f'audio/{output_format}'
        )
    except subprocess.CalledProcessError as e:
        return jsonify({"error": f"Conversion process failed: {str(e)}"}), 500
    
    finally:
        # Clean up the uploaded file
        if os.path.exists(input_path):
            os.remove(input_path)
        # Clean up the converted file after sending
        converted_file_path = os.path.splitext(input_path)[0] + f".{output_format}"
        if os.path.exists(converted_file_path):
            os.remove(converted_file_path)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8321, debug=False) 
