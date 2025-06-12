# 音频格式转换 API 服务

这个Docker容器提供了一个强大的音频格式转换API服务，主要功能包括：

- **SILK v3 音频解码**：将微信语音等SILK v3格式音频转换为常见音频格式
- **多格式音频转换**：支持MP3、AMR、WAV等多种音频格式之间的转换
- **多种输入方式**：支持文件上传和Base64编码数据输入
- **特殊格式处理**：WAV到AMR转换支持返回Base64编码数据

源代码参考[kn007/silk-v3-decoder](https://github.com/kn007/silk-v3-decoder)，在原作者功能基础上增加了完整的REST API接口、多格式支持和Docker容器化部署。

## 功能特性

- ✅ **SILK v3 解码**：支持微信语音等SILK格式音频文件
- ✅ **多格式转换**：支持MP3、AMR、WAV等常见音频格式
- ✅ **双输入模式**：文件上传 + Base64编码数据
- ✅ **智能处理**：自动检测SILK文件头，支持非标准格式
- ✅ **特殊转换**：WAV→AMR转换返回Base64编码数据
- ✅ **自动清理**：转换完成后自动清理临时文件
- ✅ **健康检查**：提供服务状态监控端点
- ✅ **容器化部署**：多阶段Docker构建，最小化镜像体积

## 前提条件

- 服务器上安装了Docker

## 项目结构

```
silk-to-mp3-docker/
├── Dockerfile          # 多阶段Docker构建文件
├── api_server.py        # Flask API服务器
├── silk.sh             # 音频转换脚本
├── silk/               # SILK解码器源码
│   ├── Makefile
│   ├── src/
│   ├── interface/
│   └── test/
└── README.md
```

## 快速开始

### 1. 构建Docker镜像

项目使用多阶段构建，自动编译SILK解码器和FFmpeg：

```bash
# 克隆项目
git clone <repository-url>
cd silk-to-mp3-docker

# 构建镜像（包含SILK解码器和FFmpeg编译）
docker build -t audio-converter .
```

### 2. 运行容器

```bash
# 启动API服务
docker run -d \
  --name audio-converter-api \
  -p 8321:8321 \
  audio-converter:latest
```

### 3. 验证服务

```bash
# 健康检查
curl http://localhost:8321/health
# 返回: {"status": "ok"}
```

## 使用API

### 方法1：将SLK文件转换为MP3

发送POST请求到`/convert`，附带SLK文件：

```bash
curl -F "file=@33921.slk" http://localhost:8321/convert -o converted.mp3
```

### 方法2：将Base64编码的音频数据转换为MP3

发送包含base64编码音频数据的JSON POST请求：

```bash
curl -X POST \
  -H "Content-Type: application/json" \
  -d '{"base64_data": "AiMhU0lMS19WMwwApyt096juSeXgI3BDCwCnK3T3...", "format": "mp3"}' \
  http://localhost:8321/convert \
  -o converted.mp3
```

使用JSON文件的示例：

```bash
curl -X POST \
  -H "Content-Type: application/json" \
  -d @audio_data.json \
  http://localhost:8321/convert \
  -o converted.mp3
```

其中`audio_data.json`包含：
```json
{
  "base64_data": "AiMhU0lMS19WMwwApyt096juSeXgI3BDCwCnK3T3...",
  "format": "mp3"
}
```

### 健康检查

```bash
curl http://localhost:8321/health
```

## 注意事项

- API服务器运行在8321端口上
- 转换后临时文件会自动清理
- 容器包含了所需的gcc和ffmpeg依赖
- Base64输入必须是有效的SILK v3音频文件的base64编码格式

## 原始转换器用法

容器使用silk.sh转换脚本，用法如下：

```bash
sh silk.sh silk_v3_file output_format
```

例如：
```bash
sh silk.sh 33921.slk mp3
```

批量转换：
```bash
sh silk.sh input_folder output_folder mp3
``` 
