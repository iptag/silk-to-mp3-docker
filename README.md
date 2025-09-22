# SILK-to-MP3 Docker 音频转换服务

[![Docker](https://img.shields.io/badge/Docker-Multi--Stage-blue.svg)](https://www.docker.com/)
[![Python](https://img.shields.io/badge/Python-3.11-green.svg)](https://www.python.org/)
[![FFmpeg](https://img.shields.io/badge/FFmpeg-7.1.1-red.svg)](https://ffmpeg.org/)
[![SILK](https://img.shields.io/badge/SILK-v3-orange.svg)](https://github.com/kn007/silk-v3-decoder)

一个专业的容器化音频转换服务，专门针对微信SILK格式进行深度优化，支持多种音频格式之间的高质量转换。基于Skype SILK SDK v3和FFmpeg 7.1.1构建，提供企业级的音频处理能力。

## 🏗️ 项目架构

### 核心架构设计
```
┌─────────────────────────────────────────────────────────────┐
│                    Flask API Layer                         │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────┐ │
│  │   File Upload   │  │   Base64 Input  │  │ Health Check│ │
│  └─────────────────┘  └─────────────────┘  └─────────────┘ │
└─────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────┐
│                 Audio Processing Engine                     │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────┐ │
│  │  Format Router  │  │  Quality Check  │  │ Duration    │ │
│  │  (Smart Path)   │  │   Validator     │  │ Calculator  │ │
│  └─────────────────┘  └─────────────────┘  └─────────────┘ │
└─────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────┐
│                   Codec Layer                               │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────┐ │
│  │   SILK Encoder  │  │   SILK Decoder  │  │   FFmpeg    │ │
│  │  (Custom C++)   │  │   (Official)    │  │  (Static)   │ │
│  └─────────────────┘  └─────────────────┘  └─────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

### 技术栈组成
- **容器化**: Docker多阶段构建 (Builder + Runtime)
- **Web框架**: Flask 3.x (Python 3.11)
- **音频处理**: FFmpeg 7.1.1 (静态编译)
- **SILK处理**: Skype SILK SDK v3 + 自定义优化编码器
- **编程语言**: Python (API层) + C/C++ (编解码器)

## 🎵 核心功能特性

### 🔧 专业音频处理
- ✅ **SILK v3 专业支持**：基于官方Skype SDK，完全兼容微信语音格式
- ✅ **智能转换路径**：自动选择最优转换策略（直接转换 vs PCM中转）
- ✅ **质量保证机制**：多层验证确保转换质量（文件头检查、零字节检测、时长验证）
- ✅ **高精度时长**：使用FFprobe获取精确音频时长信息（向上取整）

### 🚀 企业级特性
- ✅ **双输入模式**：支持文件上传和Base64编码数据输入
- ✅ **自动资源管理**：转换完成后自动清理临时文件
- ✅ **容器化部署**：多阶段Docker构建，生产环境优化
- ✅ **详细错误处理**：完整的异常捕获和用户友好的错误信息

## 📋 支持的音频格式

### 输入格式支持
| 格式 | 扩展名 | 描述 | 采样率支持 |
|------|--------|------|------------|
| **SILK** | `.silk`, `.slk` | 微信语音格式，Skype开发的低比特率语音编解码器 | 8-48kHz |
| **WAV** | `.wav` | 无损音频格式，PCM编码 | 任意 |
| **MP3** | `.mp3` | MPEG-1 Audio Layer III，广泛使用的有损压缩格式 | 任意 |
| **OGA** | `.oga` | Telegram语音格式，Ogg Vorbis格式，开源的有损压缩格式 | 任意 |

### 输出格式配置
| 格式 | 编码器 | 参数配置 | 适用场景 |
|------|--------|----------|----------|
| **MP3** | LAME | 128kbps, 可变比特率 | 通用音频播放 |
| **OGA** | Vorbis | 质量等级8, 高质量压缩 | Telegram语音消息 |
| **SILK** | Custom | 24kHz, 24kbps, 单声道 | 微信语音消息 |
| **WAV** | PCM | 24kHz, 16-bit, 单声道 | 无损音频存储 |

## 🔄 智能转换路径

### 转换策略矩阵
```
输入格式 → 输出格式    转换路径              性能等级
─────────────────────────────────────────────────────
WAV/MP3/OGA → MP3/OGA   FFmpeg直接转换        ⚡ 高性能
WAV/MP3/OGA → SILK      FFmpeg→PCM→SILK编码   🔄 中等性能
SILK → MP3/OGA/WAV      SILK解码→PCM→FFmpeg   🔄 中等性能
Base64 → 任意格式       解码→对应转换路径      📦 灵活处理
```

### 转换流程详解
1. **直接转换流程**（高效路径）
   - 输入验证 → FFmpeg格式转换 → 质量检查 → 输出
   - 适用：WAV/MP3/OGA之间的转换

2. **PCM中转流程**（兼容路径）
   - 输入验证 → 解码到PCM → 编码到目标格式 → 质量检查 → 输出
   - 适用：所有涉及SILK格式的转换

## 🚀 快速部署

### 方式一：直接拉取Docker镜像

```bash
docker run -d \
  --name silk-converter \
  -p 8321:8321 \
  --restart unless-stopped \
  iptag/audio-converter:latest
```

### 方式二：Docker构建部署

```bash
# 1. 克隆项目
git clone <repository-url>
cd silk-to-mp3-docker

# 2. 构建镜像（多阶段构建，约需5-10分钟）
docker build -t silk-to-mp3-converter .

# 3. 启动服务
docker run -d \
  --name silk-converter \
  -p 8321:8321 \
  --restart unless-stopped \
  silk-to-mp3-converter

# 4. 验证服务
curl http://localhost:8321/health
```

### 方式三：Docker Compose部署

```yaml
# docker-compose.yml
version: '3.8'
services:
  silk-converter:
    build: .
    ports:
      - "8321:8321"
    restart: unless-stopped
    environment:
      - PYTHONUNBUFFERED=1
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8321/health"]
      interval: 30s
      timeout: 10s
      retries: 3
```

```bash
# 启动服务
docker-compose up -d

# 查看日志
docker-compose logs -f silk-converter
```

## 📡 API接口文档

### 接口概览
| 端点 | 方法 | 功能 | 响应格式 |
|------|------|------|----------|
| `/health` | GET | 健康检查 | JSON |
| `/convert` | POST | 音频转换 | 文件/JSON |

### 1. 健康检查接口

```bash
GET /health

# 响应
{
  "status": "ok"
}
```

### 2. 音频转换接口

#### 2.1 文件上传转换

**请求格式**
```bash
POST /convert
Content-Type: multipart/form-data

# 参数
file: 音频文件 (必需)
format: 目标格式 (可选，默认mp3)
```

**基础格式转换示例**
```bash
# WAV转MP3（返回文件 + 时长响应头）
curl -F "file=@audio.wav" -F "format=mp3" \
     http://localhost:8321/convert \
     --output converted.mp3 -v

# 查看响应头中的时长信息
# X-Audio-Duration: 18

# MP3转OGA（Telegram语音格式）
curl -F "file=@audio.mp3" -F "format=oga" \
     http://localhost:8321/convert \
     --output converted.oga -v

# OGA转MP3
curl -F "file=@audio.oga" -F "format=mp3" \
     http://localhost:8321/convert \
     --output converted.mp3 -v
```

**SILK格式转换示例**
```bash
# SILK转MP3（返回文件）
curl -F "file=@voice.silk" -F "format=mp3" \
     http://localhost:8321/convert \
     --output converted.mp3 -v

# WAV转SILK（返回JSON）
curl -F "file=@audio.wav" -F "format=silk" \
     http://localhost:8321/convert

# 响应示例
{
  "base64": "AiMhU0lMS19WMwwApyt096...",
  "duration": 18
}
```

#### 2.2 Base64数据转换

**请求格式**
```bash
POST /convert
Content-Type: application/json

{
  "base64_data": "SILK格式的Base64编码数据",
  "format": "目标格式"
}
```

**使用示例**
```bash
# Base64 SILK数据转MP3
curl -X POST \
     -H "Content-Type: application/json" \
     -d '{
       "base64_data": "AiMhU0lMS19WMwwApyt096...",
       "format": "mp3"
     }' \
     http://localhost:8321/convert \
     --output converted.mp3 -v

# Base64 SILK数据转OGA
curl -X POST \
     -H "Content-Type: application/json" \
     -d '{
       "base64_data": "AiMhU0lMS19WMwwApyt096...",
       "format": "oga"
     }' \
     http://localhost:8321/convert \
     --output converted.oga -v
```

### 3. 响应格式详解

#### 3.1 文件响应（非SILK输出格式）
```http
HTTP/1.1 200 OK
Content-Type: audio/mp3
Content-Disposition: attachment; filename="audio.mp3"
X-Audio-Duration: 18
Content-Length: 284672

[音频文件二进制数据]
```

#### 3.2 JSON响应（SILK输出格式）
```json
{
  "base64": "AiMhU0lMS19WMwwApyt096Qx8A5wgANABgAE...",
  "duration": 18
}
```

**字段说明**
- `base64`: SILK格式音频的Base64编码数据
- `duration`: 音频时长（秒，向上取整）

#### 3.3 错误响应
```json
{
  "error": "错误描述信息",
  "details": {
    "command": "执行的命令",
    "stdout": "标准输出",
    "stderr": "错误输出"
  }
}
```

**常见错误码**
- `400`: 请求参数错误（文件格式不支持、缺少必需参数等）
- `500`: 服务器内部错误（转换失败、文件处理错误等）

## 🛠️ 技术架构深度解析

### 核心组件架构
```
┌─────────────────────────────────────────────────────────────┐
│                    Docker 多阶段构建                        │
│  ┌─────────────────┐              ┌─────────────────────────┐ │
│  │   Builder Stage │              │    Runtime Stage        │ │
│  │                 │              │                         │ │
│  │ • Ubuntu 22.04  │    ────────► │ • Python 3.11-slim     │ │
│  │ • 编译工具链     │              │ • 运行时二进制文件      │ │
│  │ • FFmpeg源码编译 │              │ • Flask应用             │ │
│  │ • SILK SDK编译   │              │ • 调试工具              │ │
│  └─────────────────┘              └─────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

### 项目文件结构
```
silk-to-mp3-docker/
├── 🐳 Dockerfile                    # 多阶段Docker构建配置
├── 🐍 api_server.py                 # Flask API服务器主程序
├── ⚙️ custom_encoder.cpp            # 优化的SILK编码器实现
├── 📁 silk_decoder/                 # SILK解码器模块
│   ├── Makefile                    # 解码器编译配置
│   ├── interface/                  # API头文件
│   │   ├── SKP_Silk_SDK_API.h     # 主API接口定义
│   │   ├── SKP_Silk_control.h     # 控制结构定义
│   │   ├── SKP_Silk_errors.h      # 错误码定义
│   │   └── SKP_Silk_typedef.h     # 类型定义
│   ├── src/                       # 解码器源码
│   └── test/                      # 测试程序
├── 📁 silk_encoder/                 # SILK编码器模块
│   ├── Makefile                    # 编码器编译配置
│   ├── interface/                  # API头文件（与decoder相同）
│   ├── src/                       # 编码器源码
│   └── test/                      # 测试程序
└── 📖 README.md                     # 项目文档
```

### 核心技术组件

#### 1. FFmpeg 7.1.1 (静态编译)
```bash
# 编译配置
./configure \
  --prefix=/opt/ffmpeg \
  --enable-version3 --enable-gpl --enable-nonfree \
  --enable-libopencore-amrnb --enable-libopencore-amrwb \
  --enable-libmp3lame --enable-libvorbis \
  --enable-static --disable-shared \
  --extra-cflags="-static" --extra-ldflags="-static"
```

#### 2. SILK SDK v3 架构
```c
// 编码器控制结构
typedef struct {
    SKP_int32 API_sampleRate;        // 8000/12000/16000/24000
    SKP_int32 maxInternalSampleRate; // 最大内部采样率
    SKP_int   packetSize;            // 20/40/60/80/100ms包大小
    SKP_int32 bitRate;               // 目标比特率
    SKP_int   packetLossPercentage;  // 丢包率 (0-100)
    SKP_int   complexity;            // 复杂度 (0-2)
    SKP_int   useInBandFEC;          // 带内前向纠错
    SKP_int   useDTX;                // 不连续传输
} SKP_SILK_SDK_EncControlStruct;
```

#### 3. 自定义编码器优化
- **内存管理**: 动态分配编码器状态结构
- **错误处理**: 容错机制，警告而非中断
- **格式兼容**: 标准SILK v3头部格式
- **性能优化**: O3编译优化，静态链接

### 编码参数配置表
| 格式 | 编码器 | 采样率 | 比特率 | 声道 | 质量设置 |
|------|--------|--------|--------|------|----------|
| **MP3** | LAME | 保持原始 | 128kbps | 保持原始 | VBR模式 |
| **OGA** | Vorbis | 保持原始 | 质量等级8 | 保持原始 | 高质量压缩 |
| **SILK** | Custom | 24kHz | 24kbps | 单声道 | 语音优化 |
| **PCM** | - | 24kHz | 16-bit | 单声道 | 中间格式 |

## 🧪 测试与验证

### 1. 服务健康检查
```bash
# 基础健康检查
curl -f http://localhost:8321/health

# 详细健康检查（包含响应时间）
time curl -s http://localhost:8321/health | jq .

# 预期响应
{
  "status": "ok"
}
```

### 2. 功能测试套件

#### 2.1 基础格式转换测试
```bash
# 创建测试音频文件（使用FFmpeg）
ffmpeg -f lavfi -i "sine=frequency=1000:duration=5" -ar 44100 test.wav

# WAV转MP3测试
curl -F "file=@test.wav" -F "format=mp3" \
     http://localhost:8321/convert \
     --output test_converted.mp3 -v

# 验证转换结果
ffprobe test_converted.mp3

# OGA转MP3测试
curl -F "file=@test.oga" -F "format=mp3" \
     http://localhost:8321/convert \
     --output test_oga_to_mp3.mp3 -v
```

#### 2.2 SILK格式测试
```bash
# WAV转SILK测试（返回JSON）
curl -F "file=@test.wav" -F "format=silk" \
     http://localhost:8321/convert | jq .

# 预期响应格式
{
  "base64": "AiMhU0lMS19WMwwApyt096...",
  "duration": 5
}

# SILK转MP3测试（如果有SILK文件）
curl -F "file=@voice.silk" -F "format=mp3" \
     http://localhost:8321/convert \
     --output silk_to_mp3.mp3 -v
```

#### 2.3 Base64数据测试
```bash
# 使用之前转换得到的Base64数据
BASE64_DATA="AiMhU0lMS19WMwwApyt096..."

# Base64转MP3
curl -X POST \
     -H "Content-Type: application/json" \
     -d "{\"base64_data\": \"$BASE64_DATA\", \"format\": \"mp3\"}" \
     http://localhost:8321/convert \
     --output base64_to_mp3.mp3 -v

# Base64转OGA
curl -X POST \
     -H "Content-Type: application/json" \
     -d "{\"base64_data\": \"$BASE64_DATA\", \"format\": \"oga\"}" \
     http://localhost:8321/convert \
     --output base64_to_oga.oga -v
```

### 3. 性能测试
```bash
# 并发测试（需要安装apache2-utils）
ab -n 100 -c 10 -p test_data.json -T application/json \
   http://localhost:8321/convert

# 大文件测试
curl -F "file=@large_audio.wav" -F "format=mp3" \
     http://localhost:8321/convert \
     --output large_converted.mp3 -v

# 响应时间测试
time curl -F "file=@test.wav" -F "format=silk" \
          http://localhost:8321/convert > /dev/null
```

### 4. 错误处理测试
```bash
# 无效文件格式测试
curl -F "file=@invalid.txt" -F "format=mp3" \
     http://localhost:8321/convert

# 缺少参数测试
curl -X POST http://localhost:8321/convert

# 无效Base64数据测试
curl -X POST \
     -H "Content-Type: application/json" \
     -d '{"base64_data": "invalid_base64", "format": "mp3"}' \
     http://localhost:8321/convert
```

## 💡 客户端集成示例

### 1. Node.js客户端
```javascript
const axios = require('axios');
const fs = require('fs');
const FormData = require('form-data');

class SilkConverter {
    constructor(baseURL = 'http://localhost:8321') {
        this.baseURL = baseURL;
    }

    // 文件转换
    async convertFile(audioPath, format = 'mp3') {
        const formData = new FormData();
        formData.append('file', fs.createReadStream(audioPath));
        formData.append('format', format);

        try {
            const response = await axios.post(`${this.baseURL}/convert`, formData, {
                headers: { ...formData.getHeaders() },
                responseType: format === 'silk' ? 'json' : 'stream'
            });

            // 获取音频时长
            const duration = parseInt(response.headers['x-audio-duration'] || '0');

            return {
                data: response.data,
                duration: duration,
                format: format
            };
        } catch (error) {
            throw new Error(`转换失败: ${error.response?.data?.error || error.message}`);
        }
    }

    // Base64数据转换
    async convertBase64(base64Data, format = 'mp3') {
        try {
            const response = await axios.post(`${this.baseURL}/convert`, {
                base64_data: base64Data,
                format: format
            }, {
                headers: { 'Content-Type': 'application/json' },
                responseType: 'stream'
            });

            const duration = parseInt(response.headers['x-audio-duration'] || '0');

            return {
                data: response.data,
                duration: duration,
                format: format
            };
        } catch (error) {
            throw new Error(`转换失败: ${error.response?.data?.error || error.message}`);
        }
    }

    // 健康检查
    async healthCheck() {
        try {
            const response = await axios.get(`${this.baseURL}/health`);
            return response.data.status === 'ok';
        } catch (error) {
            return false;
        }
    }
}

// 使用示例
async function example() {
    const converter = new SilkConverter();

    // 检查服务状态
    if (!(await converter.healthCheck())) {
        console.error('服务不可用');
        return;
    }

    try {
        // WAV转SILK
        const silkResult = await converter.convertFile('audio.wav', 'silk');
        console.log(`SILK转换完成，时长: ${silkResult.duration}秒`);
        console.log(`Base64数据: ${silkResult.data.base64.substring(0, 50)}...`);

        // SILK Base64转MP3
        const mp3Result = await converter.convertBase64(silkResult.data.base64, 'mp3');
        console.log(`MP3转换完成，时长: ${mp3Result.duration}秒`);

        // 保存MP3文件
        mp3Result.data.pipe(fs.createWriteStream('converted.mp3'));

    } catch (error) {
        console.error('转换失败:', error.message);
    }
}

module.exports = SilkConverter;
```

### 2. Python客户端
```python
import requests
import base64
from typing import Optional, Union, BinaryIO

class SilkConverter:
    def __init__(self, base_url: str = "http://localhost:8321"):
        self.base_url = base_url

    def health_check(self) -> bool:
        """健康检查"""
        try:
            response = requests.get(f"{self.base_url}/health")
            return response.json().get("status") == "ok"
        except:
            return False

    def convert_file(self, file_path: str, format: str = "mp3") -> dict:
        """文件转换"""
        with open(file_path, 'rb') as f:
            files = {'file': f}
            data = {'format': format}

            response = requests.post(f"{self.base_url}/convert",
                                   files=files, data=data)

            if response.status_code != 200:
                raise Exception(f"转换失败: {response.json().get('error', '未知错误')}")

            # SILK格式返回JSON
            if format == 'silk':
                return response.json()

            # 其他格式返回文件数据
            duration = int(response.headers.get('X-Audio-Duration', 0))
            return {
                'data': response.content,
                'duration': duration,
                'format': format
            }

    def convert_base64(self, base64_data: str, format: str = "mp3") -> dict:
        """Base64数据转换"""
        payload = {
            "base64_data": base64_data,
            "format": format
        }

        response = requests.post(f"{self.base_url}/convert", json=payload)

        if response.status_code != 200:
            raise Exception(f"转换失败: {response.json().get('error', '未知错误')}")

        duration = int(response.headers.get('X-Audio-Duration', 0))
        return {
            'data': response.content,
            'duration': duration,
            'format': format
        }

# 使用示例
if __name__ == "__main__":
    converter = SilkConverter()

    # 健康检查
    if not converter.health_check():
        print("服务不可用")
        exit(1)

    try:
        # WAV转SILK
        silk_result = converter.convert_file("audio.wav", "silk")
        print(f"SILK转换完成，时长: {silk_result['duration']}秒")

        # SILK转MP3
        mp3_result = converter.convert_base64(silk_result['base64'], "mp3")
        print(f"MP3转换完成，时长: {mp3_result['duration']}秒")

        # 保存MP3文件
        with open("converted.mp3", "wb") as f:
            f.write(mp3_result['data'])

    except Exception as e:
        print(f"转换失败: {e}")
```

## 🔧 运维与监控

### 1. 容器监控
```bash
# 查看容器状态
docker ps | grep silk-converter

# 查看容器日志
docker logs -f silk-converter

# 查看容器资源使用
docker stats silk-converter

# 进入容器调试
docker exec -it silk-converter bash
```

### 2. 性能监控
```bash
# 监控API响应时间
while true; do
  time curl -s http://localhost:8321/health > /dev/null
  sleep 5
done

# 监控转换性能
time curl -F "file=@test.wav" -F "format=mp3" \
          http://localhost:8321/convert > /dev/null
```

### 3. 故障排查
```bash
# 检查FFmpeg版本
docker exec silk-converter ffmpeg -version

# 检查SILK编码器
docker exec silk-converter ls -la /app/silk_encoder/encoder

# 检查Python依赖
docker exec silk-converter pip list

# 查看临时文件目录
docker exec silk-converter ls -la /app/uploads/
```

## 🚨 注意事项与最佳实践

### ⚠️ 重要注意事项
- **时长信息**: 所有时长都是向上取整的整数（秒），使用FFprobe精确计算
- **SILK格式**: 专为语音优化，固定采样率24kHz，单声道，比特率24kbps
- **文件清理**: 转换完成后自动清理临时文件，避免磁盘空间占用
- **响应格式**: SILK输出返回JSON格式，其他格式返回文件+时长响应头
- **编码质量**: 建议使用高质量源文件以获得最佳转换效果

### 🎯 最佳实践
1. **生产环境部署**
   - 使用Docker Compose进行服务编排
   - 配置健康检查和自动重启策略
   - 设置适当的资源限制（CPU、内存）
   - 配置日志轮转避免日志文件过大

2. **性能优化**
   - 对于高并发场景，考虑使用负载均衡
   - 监控转换时间，必要时进行水平扩展
   - 定期清理临时文件目录

3. **安全考虑**
   - 在生产环境中添加文件大小限制
   - 实施请求频率限制防止滥用
   - 考虑添加身份验证机制

### 🔍 故障排查指南
| 问题 | 可能原因 | 解决方案 |
|------|----------|----------|
| 转换失败 | 文件格式不支持 | 检查输入文件格式，确保在支持列表中 |
| SILK编码错误 | PCM文件异常 | 检查FFmpeg转换步骤，验证PCM文件完整性 |
| 服务无响应 | 容器资源不足 | 增加内存限制，检查CPU使用率 |
| 时长信息错误 | FFprobe执行失败 | 检查FFprobe版本和文件权限 |

## 🤝 贡献指南

### 开发环境搭建
```bash
# 1. 克隆项目
git clone <repository-url>
cd silk-to-mp3-docker

# 2. 本地开发（需要安装FFmpeg和Python依赖）
pip install flask
python api_server.py

# 3. 代码格式化
black api_server.py
flake8 api_server.py

# 4. 测试
python -m pytest tests/
```

### 提交规范
- 遵循Conventional Commits规范
- 提供详细的测试用例
- 更新相关文档

## 📄 许可证

MIT License - 详见 [LICENSE](LICENSE) 文件

## 🙏 致谢

- [Skype SILK SDK](https://github.com/kn007/silk-v3-decoder) - 提供SILK编解码核心功能

---

**项目维护**: 如有问题或建议，请提交Issue或Pull Request
