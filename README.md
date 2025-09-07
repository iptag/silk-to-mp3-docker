# 音频格式转换 API 服务

这个Docker容器提供了一个强大的音频格式转换API服务，专注于SILK v3音频解码和多格式音频转换。

## 核心功能

- ✅ **SILK v3 音频解码**：将微信语音等SILK v3格式音频转换为常见音频格式
- ✅ **多格式音频转换**：支持MP3、WAV、SILK等多种音频格式之间的转换
- ✅ **双输入模式**：支持文件上传和Base64编码数据输入
- ✅ **智能格式处理**：自动检测SILK文件头，处理非标准格式
- ✅ **特殊格式转换**：WAV或MP3到SILK转换，返回Base64编码数据及原始音频时长
- ✅ **自动清理**：转换完成后自动清理临时文件
- ✅ **健康监控**：提供服务状态监控端点
- ✅ **高效容器化**：多阶段Docker构建，优化镜像体积

## 技术特点

- **FFmpeg静态编译**：将FFmpeg静态编译到镜像中，减少依赖
- **SILK解码器整合**：基于[kn007/silk-v3-decoder](https://github.com/kn007/silk-v3-decoder)
- **Flask API服务**：提供RESTful API接口
- **自动填充修复**：优化处理畸形Base64数据
- **Distroless容器**：使用轻量级distroless容器减小镜像体积

## 快速开始

### 直接使用
```bash
docker run -d \
  --name audio-converter-api \
  -p 8321:8321 \
  iptag/audio-converter:latest
```

### 1. 构建Docker镜像

项目使用多阶段构建，自动编译SILK解码器和FFmpeg：

```bash
# 克隆项目
git clone https://github.com/iptag/silk-to-mp3-docker.git
cd silk-to-mp3-docker

# 构建镜像
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

## API使用方法

### 1. 通过文件上传转换音频

上传音频文件并指定输出格式：

```bash
curl -F "file=@/path/to/audio.slk" \
     -F "format=mp3" \
     http://localhost:8321/convert \
     -o converted.mp3
```

### 2. 通过Base64编码数据转换

发送包含Base64编码的音频数据：

```bash
curl -X POST \
     -H "Content-Type: application/json" \
     -d '{"base64_data": "AiMhU0lMS19WMwwApyt096...", "format": "mp3"}' \
     http://localhost:8321/convert \
     -o converted.mp3
```

### 3. WAV/MP3转换SILK

当将WAV文件或者MP3文件转换为SILK格式时，API将返回Base64编码的SILK音频数据以及原始WAV/MP3音频的时长(向上取整的整数)：

```bash
curl -F "file=@/path/to/audio.wav" \
     -F "format=silk" \
     http://localhost:8321/convert
```

```bash
curl -F "file=@/path/to/audio.mp3" \
     -F "format=silk" \
     http://localhost:8321/convert
```

响应示例：
```json
{
  "duration": 10,
  "silk_base64": "IyFTSUxLX1Yz...（此处为很长的Base64编码字符串）...AAA="
}
```

## 项目结构

```
silk-to-mp3-docker/
├── Dockerfile          # 多阶段Docker构建文件
├── api_server.py       # Flask API服务器
├── silk/               # SILK解码器源码
│   ├── Makefile
│   └── src/
└── README.md           # 项目文档
```

## 技术细节

### API服务器

- 基于Flask框架
- 端口: 8321
- 临时目录: /app/uploads
- 支持健康检查: GET /health
- 主要转换端点: POST /convert

### 音频处理

- SILK文件头自动检测: "#!SILK_V3" 和 "\x02#!SILK_V3"
- Base64输入自动修复填充
- 支持批量转换
- 使用FFmpeg进行格式转换

### Docker镜像

- 基础镜像: gcr.io/distroless/python3-debian11
- 多阶段构建减小镜像体积
- 第一阶段: 编译FFmpeg和SILK解码器
- 第二阶段: 仅复制必要的二进制文件和依赖

## 注意事项

- API仅转换音频内容，不处理元数据
- 临时文件在转换完成后自动清理
- 不支持超大文件，可能会导致内存不足
- 为确保最佳转换质量，建议提供高质量源文件

## 开发与贡献

源代码参考[kn007/silk-v3-decoder](https://github.com/kn007/silk-v3-decoder)，在原作者功能基础上增加了完整的REST API接口、多格式支持和Docker容器化部署。 
