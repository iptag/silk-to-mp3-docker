# 多格式音频转换服务 (Audio Converter API)

一个基于Docker的高性能音频转换服务，专门优化了SILK格式处理，支持多种音频格式之间的智能转换，并提供音频时长信息。

## 🎵 核心功能

- ✅ **SILK v3 专业支持**：使用优化的编码器，完全兼容微信语音格式
- ✅ **多格式转换**：支持WAV、MP3、OGA、SILK之间的相互转换
- ✅ **智能转换路径**：自动选择最优转换方式（直接转换 vs PCM中转）
- ✅ **双输入模式**：支持文件上传和Base64编码数据输入
- ✅ **音频时长获取**：所有转换都提供精确的音频时长信息
- ✅ **高质量输出**：针对不同格式优化的编码参数
- ✅ **自动清理**：转换完成后自动清理临时文件
- ✅ **容器化部署**：多阶段Docker构建，优化镜像体积

## 📋 支持的格式

### 输入格式
- **WAV**: 无损音频格式
- **MP3**: MPEG-1 Audio Layer III
- **OGA**: Oga Vorbis格式
- **SILK**: 微信语音格式 (.silk, .slk)

### 输出格式
- **MP3**: 128kbps, LAME编码器
- **OGA**: 质量等级8, Vorbis编码器
- **SILK**: 24kHz, 24kbps, 单声道
- **WAV**: 24kHz, 16-bit, 单声道

## 🔄 转换路径

### 直接转换（高效）
- MP3 ↔ OGA
- WAV → MP3
- WAV → OGA

### 通过PCM中转
- SILK → MP3/OGA
- WAV/MP3/OGA → SILK

## 🚀 快速开始

### 构建镜像

```bash
# 构建镜像
docker build -t audio-converter .
```

### 运行容器

```bash
# 启动API服务
docker run -d \
  --name audio-converter \
  -p 8321:8321 \
  audio-converter
```

## 📡 API使用方法

### 文件上传转换

#### 基础格式转换（返回文件 + 时长响应头）
```bash
# WAV转MP3（时长信息在响应头X-Audio-Duration中）
curl -F "file=@audio.wav" -F "format=mp3" http://localhost:8321/convert --output converted.mp3 -v

# WAV转OGA
curl -F "file=@audio.wav" -F "format=oga" http://localhost:8321/convert --output converted.oga -v

# MP3转OGA
curl -F "file=@audio.mp3" -F "format=oga" http://localhost:8321/convert --output converted.oga -v

# OGA转MP3
curl -F "file=@audio.oga" -F "format=mp3" http://localhost:8321/convert --output converted.mp3 -v
```

#### SILK格式转换（返回JSON）
```bash
# SILK转MP3（返回文件 + 时长响应头）
curl -F "file=@voice.silk" -F "format=mp3" http://localhost:8321/convert --output converted.mp3 -v

# WAV转SILK（返回JSON包含Base64和时长）
curl -F "file=@audio.wav" -F "format=silk" http://localhost:8321/convert
```

#### WAV转SILK返回的JSON格式
```json
{
  "base64": "AiMhU0lMS19WMwwApyt096...",
  "duration": 18
}
```

### Base64数据转换（SILK解码）

```bash
# Base64 SILK数据转MP3（返回文件 + 时长响应头）
curl -X POST \
     -H "Content-Type: application/json" \
     -d '{"base64_data": "AiMhU0lMS19WMwwApyt096...", "format": "mp3"}' \
     http://localhost:8321/convert \
     --output converted.mp3 -v
```

### 响应格式

#### 文件响应（非SILK格式）
- **响应体**: 音频文件二进制数据
- **响应头**: `X-Audio-Duration: 18` （时长，单位：秒，向上取整）
- **Content-Type**: `audio/mp3`, `audio/ogg`, 等

#### JSON响应（SILK格式）
```json
{
  "base64": "AiMhU0lMS19WMwwApyt096...",
  "duration": 18
}
```

#### 错误响应
```json
{
  "error": "错误描述"
}
```

## 🛠️ 技术架构

### 核心组件
- **FFmpeg**: 音频格式转换和处理
- **FFprobe**: 音频时长获取
- **SILK SDK**: 微信SILK格式编解码
- **Custom Encoder**: 优化的SILK编码器
- **Flask**: Web API框架
- **Docker**: 容器化部署

### 项目结构
```
silk-to-mp3-docker/
├── Dockerfile              # 多阶段Docker构建
├── api_server.py           # Flask API服务器
├── custom_encoder.cpp      # 优化的SILK编码器
├── silk_decoder/           # SILK解码器
│   ├── Makefile
│   ├── interface/
│   └── src/
├── silk_encoder/           # SILK编码器
│   ├── Makefile
│   ├── interface/
│   └── src/
└── README.md
```

### 编码参数
- **MP3**: 128kbps, LAME编码器
- **OGA**: 质量等级8, Vorbis编码器
- **SILK**: 24kHz, 24kbps, 单声道
- **PCM**: 24kHz, 16-bit, 单声道（中间格式）

## 🧪 测试

### 健康检查
```bash
curl http://localhost:8321/health
```

### 手动测试
```bash
# 测试WAV转OGA（查看响应头中的时长）
curl -F "file=@test.wav" -F "format=oga" http://localhost:8321/convert -v --output test.oga

# 测试WAV转SILK（JSON响应）
curl -F "file=@test.wav" -F "format=silk" http://localhost:8321/convert

# 测试Base64 SILK转MP3
curl -X POST \
     -H "Content-Type: application/json" \
     -d '{"base64_data": "your_silk_base64_data", "format": "mp3"}' \
     http://localhost:8321/convert \
     --output converted.mp3 -v
```

## 💡 客户端集成示例

### Node.js客户端
```javascript
const axios = require('axios');
const fs = require('fs');
const FormData = require('form-data');

async function convertAudio(audioPath, format) {
    const formData = new FormData();
    formData.append('file', fs.createReadStream(audioPath));
    formData.append('format', format);

    const response = await axios.post('http://localhost:8321/convert', formData, {
        headers: { ...formData.getHeaders() },
        responseType: 'stream'
    });

    // 从响应头获取时长
    const duration = parseInt(response.headers['x-audio-duration'] || '0');
    console.log(`音频时长: ${duration}秒`);

    return response.data;
}
```

## ⚠️ 注意事项

- **时长信息**: 所有时长都是向上取整的整数（秒）
- **SILK格式**: 专为语音优化，采样率固定为24kHz，单声道
- **文件清理**: 转换完成后自动清理临时文件
- **响应格式**: SILK转换返回JSON，其他格式返回文件+时长响应头
- **编码质量**: 建议使用高质量源文件以获得最佳转换效果

## 📄 许可证

MIT License
