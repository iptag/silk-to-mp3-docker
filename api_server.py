#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import subprocess
import uuid
import base64
import re
import math
import struct
import traceback
from flask import Flask, request, send_file, jsonify

# 初始化Flask应用
app = Flask(__name__)

# 定义上传和转换后文件的临时存储目录
UPLOAD_DIR = '/app/uploads'

# 定义二进制文件在容器内的绝对路径
DECODER_PATH = '/app/silk/decoder'
ENCODER_PATH = '/app/silk/encoder'
FFMPEG_PATH = '/usr/local/bin/ffmpeg'
FFPROBE_PATH = '/usr/local/bin/ffprobe'

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
    pcm_path = None
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
            converted_file_path = os.path.splitext(input_path)[0] + f".{output_format}"
            pcm_path = os.path.splitext(input_path)[0] + ".pcm"

            if output_format.lower() == 'silk':
                # ==================== 使用我们自己的可靠编码器 ====================
                # ... (ffprobe 部分保持不变) ...
                ffprobe_command = [
                    FFPROBE_PATH, '-v', 'error',
                    '-show_entries', 'format=duration',
                    '-of', 'default=noprint_wrappers=1:nokey=1', input_path
                ]
                result = subprocess.run(ffprobe_command, check=True, capture_output=True, text=True)
                duration_seconds = math.ceil(float(result.stdout.strip()))

                target_sample_rate = "24000"

                # 步骤1: FFmpeg -> PCM file
                ffmpeg_to_pcm_command = [
                    FFMPEG_PATH, '-y', '-i', input_path,
                    '-f', 's16le', '-ar', target_sample_rate, '-ac', '1', pcm_path
                ]
                subprocess.run(ffmpeg_to_pcm_command, check=True, capture_output=True, text=True)

                if not os.path.exists(pcm_path) or os.path.getsize(pcm_path) == 0:
                    raise ValueError(f"FFMPEG failed to produce a valid PCM file from {input_path}")

                # 步骤2: 调用修复后的 custom_encoder
                # 用法: custom_encoder <sample_rate> <input.pcm> <output.silk>
                encoder_command = [
                    ENCODER_PATH,
                    target_sample_rate,
                    pcm_path,
                    converted_file_path
                ]
                print(f"Executing SILK encoder: {' '.join(encoder_command)}")

                # Enhanced error handling for encoder
                try:
                    process = subprocess.run(encoder_command, check=True, capture_output=True, text=True)
                    if process.stderr:
                        print(f"Encoder output: {process.stderr}")
                except subprocess.CalledProcessError as e:
                    print(f"Custom Encoder failed with return code {e.returncode}")
                    print(f"Custom Encoder STDOUT: {e.stdout}")
                    print(f"SILK encoding failed: {e.stderr}")
                    raise ValueError(f"SILK encoding failed: {e.stderr}")
                
                # ... (后续的返回 JSON 部分保持不变) ...
                if not os.path.exists(converted_file_path):
                    return jsonify({"error": "转换失败，SILK文件未生成"}), 500

                with open(converted_file_path, "rb") as audio_file:
                    silk_data = audio_file.read()

                # ==================== VALIDATION: Check for excessive zero bytes ====================
                if len(silk_data) == 0:
                    return jsonify({"error": "转换失败，生成的SILK文件为空"}), 500

                # Check if file starts with proper SILK header
                if not (silk_data.startswith(b'#!SILK_V3') or silk_data.startswith(b'\x02#!SILK_V3')):
                    print(f"Warning: SILK file may not have proper header. First 20 bytes: {silk_data[:20]}")

                # Check for excessive zero bytes (more than 50% zeros indicates a problem)
                zero_count = silk_data.count(b'\x00')
                zero_percentage = (zero_count / len(silk_data)) * 100
                print(f"SILK file stats: size={len(silk_data)} bytes, zero_bytes={zero_count} ({zero_percentage:.1f}%)")

                if zero_percentage > 50:
                    print(f"Warning: SILK file contains {zero_percentage:.1f}% zero bytes, which may indicate encoding issues")
                # ===================================================================================

                base_64_encoded = base64.b64encode(silk_data).decode("utf-8")
                
                return jsonify({"base64": base_64_encoded, "duration": duration_seconds})

            else:
                # 检查输入文件格式
                input_ext = os.path.splitext(file.filename)[1].lower()

                if input_ext == '.silk' or input_ext == '.slk':
                    # SILK -> 其他格式
                    decode_command = [DECODER_PATH, input_path, pcm_path]
                    print(f"Executing decode: {' '.join(decode_command)}")
                    subprocess.run(decode_command, check=True, capture_output=True, text=True)

                    if not os.path.exists(pcm_path) or os.path.getsize(pcm_path) == 0:
                        raise ValueError(f"Decoder failed to produce a valid PCM file from {input_path}")

                    ffmpeg_command = [
                        FFMPEG_PATH, '-y', '-f', 's16le', '-ar', '24000',
                        '-ac', '1', '-i', pcm_path, converted_file_path
                    ]
                    print(f"Executing ffmpeg from pcm: {' '.join(ffmpeg_command)}")
                    subprocess.run(ffmpeg_command, check=True, capture_output=True, text=True)

                else:
                    # 其他格式之间的转换 (包括 ogg <-> mp3)
                    ffmpeg_command = [FFMPEG_PATH, '-y', '-i', input_path]

                    # 根据输出格式添加特定参数
                    if output_format.lower() == 'ogg':
                        ffmpeg_command.extend(['-c:a', 'libvorbis', '-q:a', '5'])
                    elif output_format.lower() == 'mp3':
                        ffmpeg_command.extend(['-c:a', 'libmp3lame', '-b:a', '128k'])

                    ffmpeg_command.append(converted_file_path)

                    print(f"Executing direct conversion: {' '.join(ffmpeg_command)}")
                    subprocess.run(ffmpeg_command, check=True, capture_output=True, text=True)

        elif request.is_json and 'base64_data' in request.json:
            # Base64 -> 其他格式的逻辑保持不变
            base64_data = request.json['base64_data']
            unique_id = str(uuid.uuid4())
            input_path = os.path.join(UPLOAD_DIR, f"{unique_id}.slk")
            if not base64_to_silk(base64_data, input_path):
                return jsonify({"error": "无法将Base64数据转换为SILK文件"}), 400
            
            output_format = request.json.get('format', 'mp3')
            output_filename = f"audio.{output_format}"
            converted_file_path = os.path.splitext(input_path)[0] + f".{output_format}"
            pcm_path = os.path.splitext(input_path)[0] + ".pcm"
            
            decode_command = [DECODER_PATH, input_path, pcm_path]
            print(f"Executing decode: {' '.join(decode_command)}")
            subprocess.run(decode_command, check=True, capture_output=True, text=True)

            if not os.path.exists(pcm_path) or os.path.getsize(pcm_path) == 0:
                raise ValueError(f"Decoder failed to produce a valid PCM file from {input_path}")
            
            ffmpeg_command = [
                FFMPEG_PATH, '-y', '-f', 's16le', '-ar', '24000',
                '-ac', '1', '-i', pcm_path, converted_file_path
            ]
            print(f"Executing ffmpeg from pcm: {' '.join(ffmpeg_command)}")
            subprocess.run(ffmpeg_command, check=True, capture_output=True, text=True)
        
        else:
            return jsonify({"error": "请求中未提供文件(file)或Base64数据(base64_data)"}), 400
        
        if not os.path.exists(converted_file_path):
            return jsonify({"error": "转换失败，输出文件未生成"}), 500
        
        mimetype = f'audio/{output_format}'
        
        return send_file(
            converted_file_path,
            as_attachment=True,
            download_name=output_filename,
            mimetype=mimetype
        )

    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        traceback.print_exc()
        error_details = {"error": f"服务器内部错误: {str(e)}"}
        if isinstance(e, subprocess.CalledProcessError):
            error_details["details"] = {
                "command": ' '.join(e.cmd),
                "stdout": e.stdout if isinstance(e.stdout, str) else e.stdout.decode(errors='ignore'),
                "stderr": e.stderr if isinstance(e.stderr, str) else e.stderr.decode(errors='ignore')
            }
        return jsonify(error_details), 500
        
    finally:
        # 清理所有临时文件
        if input_path and os.path.exists(input_path):
            os.remove(input_path)
        if converted_file_path and os.path.exists(converted_file_path):
            os.remove(converted_file_path)
        if pcm_path and os.path.exists(pcm_path):
            os.remove(pcm_path)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8321, debug=False)
