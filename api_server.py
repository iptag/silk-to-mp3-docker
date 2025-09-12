#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import subprocess
import uuid
import base64
import re
import math
import traceback
from flask import Flask, request, send_file, jsonify

# 初始化Flask应用
app = Flask(__name__)

# 定义上传和转换后文件的临时存储目录
UPLOAD_DIR = '/app/uploads'

# 定义二进制文件在容器内的绝对路径
DECODER_PATH = '/app/silk_decoder/decoder'  # 使用工作正常的 silk_decoder 解码器
ENCODER_PATH = '/app/silk_encoder/encoder'  # 基于官方示例的 custom_encoder
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

def get_audio_duration(file_path):
    """获取音频文件时长（秒），向上取整"""
    try:
        ffprobe_command = [
            FFPROBE_PATH, '-v', 'error',
            '-show_entries', 'format=duration',
            '-of', 'default=noprint_wrappers=1:nokey=1', file_path
        ]
        result = subprocess.run(ffprobe_command, check=True, capture_output=True)
        duration_seconds = math.ceil(float(result.stdout.decode('utf-8', errors='replace').strip()))
        print(f"获取音频时长: {duration_seconds}秒")
        return duration_seconds
    except Exception as e:
        print(f"获取音频时长失败: {str(e)}")
        return 0  # 返回默认值

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
                # 获取音频时长
                duration_seconds = get_audio_duration(input_path)

                target_sample_rate = "24000"

                # 步骤1: FFmpeg -> PCM file (确保格式完全正确)
                ffmpeg_to_pcm_command = [
                    FFMPEG_PATH, '-y', '-i', input_path,
                    '-f', 's16le',  # 16-bit signed little-endian
                    '-ar', target_sample_rate,  # 采样率
                    '-ac', '1',     # 单声道
                    '-acodec', 'pcm_s16le',  # 明确指定编码器
                    pcm_path
                ]
                subprocess.run(ffmpeg_to_pcm_command, check=True, capture_output=True)
                print(f"FFmpeg PCM conversion completed. PCM file size: {os.path.getsize(pcm_path) if os.path.exists(pcm_path) else 0} bytes")

                if not os.path.exists(pcm_path) or os.path.getsize(pcm_path) == 0:
                    raise ValueError(f"FFMPEG failed to produce a valid PCM file from {input_path}")

                # 验证PCM文件格式
                pcm_size = os.path.getsize(pcm_path)
                expected_samples = int(duration_seconds * int(target_sample_rate))
                expected_size = expected_samples * 2  # 16-bit samples = 2 bytes per sample
                print(f"PCM file validation: size={pcm_size} bytes, expected~{expected_size} bytes, duration={duration_seconds}s")

                # 检查PCM文件内容（前32字节的十六进制dump）
                try:
                    with open(pcm_path, 'rb') as pcm_file:
                        first_bytes = pcm_file.read(32)
                        hex_dump = ' '.join(f'{b:02x}' for b in first_bytes)
                        print(f"PCM file first 32 bytes: {hex_dump}")

                        # 检查是否全为零（可能表示转换失败）
                        if all(b == 0 for b in first_bytes):
                            print("WARNING: PCM file starts with all zeros - possible conversion issue")
                except Exception as e:
                    print(f"Failed to read PCM file for analysis: {e}")

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
                    process = subprocess.run(encoder_command, check=True, capture_output=True)
                    if process.stderr:
                        stderr_text = process.stderr.decode('utf-8', errors='replace')
                        print(f"Encoder output: {stderr_text}")
                    if process.stdout:
                        stdout_text = process.stdout.decode('utf-8', errors='replace')
                        print(f"Encoder stdout: {stdout_text}")
                except subprocess.CalledProcessError as e:
                    print(f"Custom Encoder failed with return code {e.returncode}")
                    stdout_text = e.stdout.decode('utf-8', errors='replace') if e.stdout else "No stdout"
                    stderr_text = e.stderr.decode('utf-8', errors='replace') if e.stderr else "No stderr"
                    print(f"Custom Encoder STDOUT: {stdout_text}")
                    print(f"SILK encoding failed: {stderr_text}")
                    raise ValueError(f"SILK encoding failed: {stderr_text}")

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
                    subprocess.run(decode_command, check=True, capture_output=True)

                    if not os.path.exists(pcm_path) or os.path.getsize(pcm_path) == 0:
                        raise ValueError(f"Decoder failed to produce a valid PCM file from {input_path}")

                    ffmpeg_command = [
                        FFMPEG_PATH, '-y', '-f', 's16le', '-ar', '24000',
                        '-ac', '1', '-i', pcm_path, converted_file_path
                    ]
                    print(f"Executing ffmpeg from pcm: {' '.join(ffmpeg_command)}")
                    subprocess.run(ffmpeg_command, check=True, capture_output=True)

                else:
                    # 其他格式之间的转换 (包括 oga <-> mp3, oga是telegram用到的语音消息格式)
                    ffmpeg_command = [FFMPEG_PATH, '-y', '-i', input_path]

                    # 根据输出格式添加特定参数
                    if output_format.lower() == 'oga':
                        ffmpeg_command.extend(['-c:a', 'libvorbis', '-q:a', '8'])
                    elif output_format.lower() == 'mp3':
                        ffmpeg_command.extend(['-c:a', 'libmp3lame', '-b:a', '128k'])

                    ffmpeg_command.append(converted_file_path)

                    print(f"Executing direct conversion: {' '.join(ffmpeg_command)}")
                    subprocess.run(ffmpeg_command, check=True, capture_output=True)

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
            subprocess.run(decode_command, check=True, capture_output=True)

            if not os.path.exists(pcm_path) or os.path.getsize(pcm_path) == 0:
                raise ValueError(f"Decoder failed to produce a valid PCM file from {input_path}")

            ffmpeg_command = [
                FFMPEG_PATH, '-y', '-f', 's16le', '-ar', '24000',
                '-ac', '1', '-i', pcm_path, converted_file_path
            ]
            print(f"Executing ffmpeg from pcm: {' '.join(ffmpeg_command)}")
            subprocess.run(ffmpeg_command, check=True, capture_output=True)

        else:
            return jsonify({"error": "请求中未提供文件(file)或Base64数据(base64_data)"}), 400

        if not os.path.exists(converted_file_path):
            return jsonify({"error": "转换失败，输出文件未生成"}), 500

        # 获取音频时长并添加到响应头
        duration_seconds = get_audio_duration(converted_file_path)

        mimetype = f'audio/{output_format}'

        response = send_file(
            converted_file_path,
            as_attachment=True,
            download_name=output_filename,
            mimetype=mimetype
        )

        # 在响应头中添加时长信息
        response.headers['X-Audio-Duration'] = str(duration_seconds)

        return response

    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        traceback.print_exc()
        error_details = {"error": f"服务器内部错误: {str(e)}"}
        if isinstance(e, subprocess.CalledProcessError):
            stdout_text = ""
            stderr_text = ""

            if e.stdout:
                stdout_text = e.stdout.decode('utf-8', errors='replace') if isinstance(e.stdout, bytes) else str(e.stdout)
            if e.stderr:
                stderr_text = e.stderr.decode('utf-8', errors='replace') if isinstance(e.stderr, bytes) else str(e.stderr)

            error_details["details"] = {
                "command": ' '.join(e.cmd),
                "stdout": stdout_text,
                "stderr": stderr_text
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
