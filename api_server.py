#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import subprocess
import uuid
import base64
import re
from flask import Flask, request, send_file, jsonify

# 初始化Flask应用
app = Flask(__name__)

# 定义上传和转换后文件的临时存储目录
UPLOAD_DIR = '/app/uploads'
CONVERTED_DIR = '/app/converted'

# 创建临时目录，如果目录已存在则不执行任何操作
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(CONVERTED_DIR, exist_ok=True)

def fixBase64Padding(encoded_str):
    """
    修复损坏的或不规范的Base64字符串的填充。
    有些Base64编码可能缺少末尾的'='填充，此函数会修正它。
    
    Args:
        encoded_str (str): 输入的Base64编码字符串。
        
    Returns:
        str: 修复了填充的Base64字符串。
    """
    # 移除一些特定模式的重复字符，例如错误的结尾'A'和'='
    pattern = r'A+?=*$'
    encoded_str = re.sub(pattern, '', encoded_str)
    
    # 计算字符串长度，确定是否需要填充
    missing_padding = len(encoded_str) % 4
    
    # 如果长度不是4的倍数，则添加'='进行填充
    if missing_padding != 0:
        encoded_str += '=' * (4 - missing_padding)
    return encoded_str

def base64_to_silk(base64_data, output_file):
    """
    将Base64编码的音频数据解码并保存为SILK格式的二进制文件。
    
    Args:
        base64_data (str): Base64编码的音频数据。
        output_file (str): 输出的SILK文件的完整路径。
        
    Returns:
        bool: 如果成功保存则返回True，否则返回False。
    """
    try:
        # 清理Base64数据，移除所有空白字符（如换行符、空格）
        clean_base64 = re.sub(r'\s+', '', base64_data).strip()
        
        # 修正Base64字符串的填充
        clean_base64 = fixBase64Padding(clean_base64)
        
        # 使用正则表达式验证清理后的字符串是否是有效的Base64格式
        base64_regex = r'^[A-Za-z0-9+/]*={0,2}$'
        if not re.match(base64_regex, clean_base64):
            print('错误：无效的Base64格式')
            return False
            
        # 尝试解码Base64字符串为二进制数据
        try:
            audio_buffer = base64.b64decode(clean_base64)
        except Exception as e:
            print(f'Base64解码失败: {str(e)}')
            return False
            
        # 定义已知的SILK文件头标识
        silk_headers = [
            b'#!SILK_V3',      # 标准的SILK v3文件头
            b'\x02#!SILK_V3'   # 某些情况下，文件头前可能有一个额外的字节
        ]
        
        # 检查解码后的二进制数据是否以SILK文件头开始
        is_silk = False
        for header in silk_headers:
            if audio_buffer.startswith(header):
                is_silk = True
                break
        
        # 如果不是SILK格式，打印警告但仍然尝试保存
        if not is_silk:
            print('警告：数据可能不是标准的SILK格式，但仍会尝试保存')
            
        # 将二进制音频数据以二进制写模式('wb')写入到输出文件
        with open(output_file, 'wb') as f:
            f.write(audio_buffer)
            
        print(f'成功保存文件到: {output_file}')
        return True
    except Exception as e:
        # 捕获任何其他在过程中发生的异常
        print(f'转换失败: {str(e)}')
        return False

@app.route('/health', methods=['GET'])
def health_check():
    """
    提供一个健康检查端点，用于监控服务是否正常运行。
    """
    # 返回一个JSON响应，表示服务状态正常
    return jsonify({"status": "ok"})

@app.route('/convert', methods=['POST'])
def convert_file():
    """
    处理文件转换请求的核心路由。
    支持两种输入方式：
    1. 通过 multipart/form-data 上传文件。
    2. 通过 application/json 发送Base64编码的音频数据。
    """
    # 检查请求中是否包含'file'字段，即判断是否为文件上传
    if 'file' in request.files:
        # 获取上传的文件对象
        file = request.files['file']
        
        # 如果用户未选择文件，浏览器会提交一个没有文件名的空部分
        if file.filename == '':
            return jsonify({"error": "没有选择文件"}), 400
            
        # 为本次转换生成一个唯一的ID，以避免文件名冲突
        unique_id = str(uuid.uuid4())
        # 构造输入文件的完整保存路径
        input_path = os.path.join(UPLOAD_DIR, f"{unique_id}_{file.filename}")
        
        # 保存上传的文件到指定路径
        file.save(input_path)
        
        # 从表单数据中获取期望的输出格式，默认为'mp3'
        output_format = request.form.get('format', 'mp3')
        # 从原始文件名中提取文件名（不含扩展名），并构造输出文件名
        original_filename_without_ext = os.path.splitext(os.path.basename(file.filename))[0]
        output_filename = f"{original_filename_without_ext}.{output_format}"
    
    # 检查请求的JSON体中是否包含'base64_data'字段
    elif request.is_json and 'base64_data' in request.json:
        # 获取JSON中的Base64数据
        base64_data = request.json['base64_data']
        # 为本次转换生成唯一ID
        unique_id = str(uuid.uuid4())
        # 构造输入SILK文件的路径
        input_path = os.path.join(UPLOAD_DIR, f"{unique_id}.slk")
        
        # 调用函数将Base64数据转换为SILK文件
        success = base64_to_silk(base64_data, input_path)
        if not success:
            return jsonify({"error": "无法将Base64数据转换为SILK文件"}), 400
            
        # 从JSON数据中获取期望的输出格式，默认为'mp3'
        output_format = request.json.get('format', 'mp3')
        # 为Base64输入构造一个通用的输出文件名
        output_filename = f"audio.{output_format}"
    else:
        # 如果请求中既没有文件也没有Base64数据，返回错误
        return jsonify({"error": "请求中未提供文件(file)或Base64数据(base64_data)"}), 400
    
    # 构造转换后文件的预期路径
    converted_file_path = os.path.splitext(input_path)[0] + f".{output_format}"
    
    try:
        # 调用外部shell脚本(silk.sh)来执行实际的音频格式转换
        subprocess.run([
            "sh",
            "/app/silk.sh",
            input_path,
            output_format
        ], check=True)
        
        # 检查转换后的文件是否真的存在
        if not os.path.exists(converted_file_path):
            # 如果文件不存在，说明转换过程中发生了未捕获的错误
            return jsonify({"error": "转换失败，输出文件未生成"}), 500
            
        # 如果转换成功，使用send_file将文件作为附件发送给客户端
        return send_file(
            converted_file_path,
            as_attachment=True,  # 作为附件下载
            download_name=output_filename,  # 指定下载时的文件名
            mimetype=f'audio/{output_format}'  # 设置正确的MIME类型
        )
    except subprocess.CalledProcessError as e:
        # 如果转换脚本执行失败，返回详细错误信息
        return jsonify({"error": f"转换过程失败: {str(e)}"}), 500
    
    finally:
        # 清理上传的临时文件
        if os.path.exists(input_path):
            os.remove(input_path)
        # 清理转换后发送给用户的临时文件
        if os.path.exists(converted_file_path):
            os.remove(converted_file_path)

# 当该脚本作为主程序直接运行时
if __name__ == '__main__':
    # 启动Flask应用服务器
    # host='0.0.0.0' 使服务器可以从任何网络接口访问（而不仅仅是本地主机）
    # port=8321 指定监听的端口号
    # debug=False 在生产环境中关闭调试模式，以提高性能和安全性
    app.run(host='0.0.0.0', port=8321, debug=False)
