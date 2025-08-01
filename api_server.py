#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import subprocess
import uuid
import base64
import re
import traceback
from flask import Flask, request, send_file, jsonify

# 初始化Flask应用
app = Flask(__name__)

# 定义上传和转换后文件的临时存储目录
UPLOAD_DIR = '/app/uploads'

# 定义二进制文件在容器内的绝对路径
DECODER_PATH = '/app/silk/decoder'
FFMPEG_PATH = '/usr/local/bin/ffmpeg' # 确保此路径在您的环境中是正确的

# 创建临时目录
os.makedirs(UPLOAD_DIR, exist_ok=True)

def fixBase64Padding(encoded_str):
    pattern = r'A+?=*$'
    encoded_str = re.sub(pattern, '', encoded_str)
    missing_padding = len(encoded_str) % 4
    if missing_padding != 0:
        encoded_str += '=' * (4 - missing_padding)
    return encoded_str

def base64_to_silk(base64_data, output_file):
    try:
        clean_base64 = re.sub(r'\s+', '', base64_data).strip()
        clean_base64 = fixBase64Padding(clean_base64)
        base64_regex = r'^[A-Za-z0-9+/]*={0,2}$'
        if not re.match(base64_regex, clean_base64):
            print('错误：无效的Base64格式')
            return False
        try:
            audio_buffer = base64.b64decode(clean_base64)
        except Exception as e:
            print(f'Base64解码失败: {str(e)}')
            return False
        silk_headers = [b'#!SILK_V3', b'\x02#!SILK_V3']
        is_silk = any(audio_buffer.startswith(header) for header in silk_headers)
        if not is_silk:
            print('警告：数据可能不是标准的SILK格式，但仍会尝试保存')
        with open(output_file, 'wb') as f:
            f.write(audio_buffer)
        print(f'成功保存文件到: {output_file}')
        return True
    except Exception as e:
        print(f'转换失败: {str(e)}')
        return False

@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({"status": "ok"})

@app.route('/convert', methods=['POST'])
def convert_file():
    input_path = None
    converted_file_path = None
    output_filename = "audio"
    try:
        if 'file' in request.files:
            file = request.files['file']
            if file.filename == '':
                return jsonify({"error": "没有选择文件"}), 400
            unique_id = str(uuid.uuid4())
            input_path = os.path.join(UPLOAD_DIR, f"{unique_id}_{file.filename}")
            file.save(input_path)
            output_format = request.form.get('format', 'mp3')
            original_filename_without_ext = os.path.splitext(os.path.basename(file.filename))[0]
            output_filename = f"{original_filename_without_ext}.{output_format}"
            is_wav_to_amr = file.filename.lower().endswith('.wav') and output_format.lower() == 'amr'
            is_mp3_to_amr = file.filename.lower().endswith('.mp3') and output_format.lower() == 'amr'
        elif request.is_json and 'base64_data' in request.json:
            base64_data = request.json['base64_data']
            unique_id = str(uuid.uuid4())
            input_path = os.path.join(UPLOAD_DIR, f"{unique_id}.slk")
            if not base64_to_silk(base64_data, input_path):
                return jsonify({"error": "无法将Base64数据转换为SILK文件"}), 400
            output_format = request.json.get('format', 'mp3')
            output_filename = f"audio.{output_format}"
            is_wav_to_amr = False
            is_mp3_to_amr = False # Base64 输入不执行 amr 转换
        else:
            return jsonify({"error": "请求中未提供文件(file)或Base64数据(base64_data)"}), 400
        converted_file_path = os.path.splitext(input_path)[0] + f".{output_format}"
        if is_wav_to_amr or is_mp3_to_amr:
            subprocess.run([
                FFMPEG_PATH, "-y", "-i", input_path, "-ar", "8000", "-ab", "12.2k", "-ac", "1", converted_file_path
            ], check=True, capture_output=True)
            with open(converted_file_path, "rb") as audio_file:
                amr_data = audio_file.read()
            base64_encoded = base64.b64encode(amr_data).decode("utf-8")
            return jsonify({"amr_base64": base64_encoded})
        else:
            pcm_path = os.path.splitext(input_path)[0] + ".pcm"
            decode_command = [DECODER_PATH, input_path, pcm_path]
            print(f"Executing decode: {' '.join(decode_command)}")
            subprocess.run(decode_command, check=True, capture_output=True)
            if not os.path.exists(pcm_path) or os.path.getsize(pcm_path) == 0:
                raise ValueError(f"Decoder failed to produce a valid PCM file from {input_path}")
            ffmpeg_command = [
                FFMPEG_PATH, '-y', '-f', 's16le', '-ar', '24000',
                '-ac', '1', '-i', pcm_path, converted_file_path
            ]
            subprocess.run(ffmpeg_command, check=True, capture_output=True)
            if not os.path.exists(converted_file_path):
                return jsonify({"error": "转换失败，输出文件未生成"}), 500
            return send_file(
                converted_file_path,
                as_attachment=True,
                download_name=output_filename,
                mimetype=f'audio/{output_format}'
            )
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        traceback.print_exc()
        error_details = {"error": f"服务器内部错误: {str(e)}"}
        if isinstance(e, subprocess.CalledProcessError):
            error_details["details"] = {
                "command": ' '.join(e.cmd),
                "stdout": e.stdout.decode() if e.stdout else 'N/A',
                "stderr": e.stderr.decode() if e.stderr else 'N/A'
            }
        return jsonify(error_details), 500
    finally:
        # 清理临时文件
        if input_path and os.path.exists(input_path):
            os.remove(input_path)
        if converted_file_path and os.path.exists(converted_file_path):
            os.remove(converted_file_path)
        if 'pcm_path' in locals() and 'pcm_path' in vars() and os.path.exists(pcm_path):
            os.remove(pcm_path)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8321, debug=False)
