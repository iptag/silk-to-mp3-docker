# 多格式音频转换服务 (Audio Converter API)

一个基于Docker的高性能音频转换服务，专门优化了SILK格式处理，支持多种音频格式之间的智能转换。

## 🎵 核心功能

- ✅ **SILK v3 专业支持**：使用优化的编码器，完全兼容微信语音格式
- ✅ **多格式转换**：支持WAV、MP3、OGA、SILK之间的相互转换
- ✅ **智能转换路径**：自动选择最优转换方式（直接转换 vs PCM中转）
- ✅ **双输入模式**：支持文件上传和Base64编码数据输入
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
- **OGA**: 质量等级5, Vorbis编码器
- **SILK**: 24kHz, 24kbps, 单声道

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

#### 基础格式转换
```bash
# WAV转MP3
curl -F "file=@audio.wav" -F "format=mp3" http://localhost:8321/convert --output converted.mp3

# WAV转OGA
curl -F "file=@audio.wav" -F "format=oga" http://localhost:8321/convert --output converted.oga

# MP3转OGA
curl -F "file=@audio.mp3" -F "format=oga" http://localhost:8321/convert --output converted.oga

# OGA转MP3
curl -F "file=@audio.oga" -F "format=mp3" http://localhost:8321/convert --output converted.mp3
```

#### SILK格式转换
```bash
# SILK转MP3
curl -F "file=@voice.silk" -F "format=mp3" http://localhost:8321/convert --output converted.mp3

# WAV转SILK (返回Base64)
curl -F "file=@audio.wav" -F "format=silk" http://localhost:8321/convert
```

#### WAV转SILK后返回的json数据格式为
```json
{
  "base64": "xxxxxx",
  "duration": 18
}
```

### Base64数据转换

```bash
curl -X POST \
     -H "Content-Type: application/json" \
     -d '{"base64_data": "AiMhU0lMS19WMwwApyt096...", "format": "mp3"}' \
     http://localhost:8321/convert
```

### 响应格式

#### 成功响应
```json
{
  "filename": "audio.mp3",
  "base64_data": "base64_encoded_audio_data",
  "duration_seconds": 18
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
- **SILK SDK**: 微信SILK格式编解码
- **Flask**: Web API框架
- **Docker**: 容器化部署

### 项目结构
```
silk-to-mp3-docker/
├── Dockerfile              # 多阶段Docker构建
├── api_server.py           # Flask API服务器
├── custom_encoder.cpp      # 优化的SILK编码器
├── silk/                   # SILK SDK
│   ├── Makefile
│   ├── interface/
│   └── src/
├── README.md
└── CHANGELOG.md
```

### 编码参数
- **MP3**: 128kbps, LAME编码器
- **OGA**: 质量等级5, Vorbis编码器
- **SILK**: 24kHz, 24kbps, 单声道

## 🧪 测试

运行测试脚本：
```bash
# Linux/Mac
./test_oga_conversion.sh

# 或手动测试
curl -F "file=@test.wav" -F "format=oga" http://localhost:8321/convert
```

## ⚠️ 注意事项

- SILK格式专为语音优化，采样率固定为24kHz
- 所有音频在转换为SILK时会自动转为单声道
- 临时文件在转换完成后自动清理
- 建议使用高质量源文件以获得最佳转换效果

## 📄 许可证

MIT License
