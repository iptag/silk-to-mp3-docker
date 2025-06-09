# SLK to MP3 Converter API

这个Docker容器提供了一个API服务，可以将Silk v3 (.slk)音频文件转换为MP3格式。它支持直接文件上传和base64编码的音频数据。
源代码参考[kn007/silk-v3-decoder](https://github.com/kn007/silk-v3-decoder)，这里只是将原作者的功能使用了docker进行实现，方便直接通过api调用

## 前提条件

- 服务器上安装了Docker

## 文件结构

所有文件都位于Ubuntu服务器的`/root/silk/`目录下：
```
/root/silk/
├── Dockerfile
├── api_server.py
├── silk.sh
└── silk/
    └── (silk解码器源文件)
```

## 构建容器

在`/root/silk/`目录中执行以下命令构建Docker镜像：
```bash
docker build -t silk-converter .
```

## 运行容器

启动容器：
```bash
docker run -d \
  --name silk-converter-api \
  -p 8321:8321 \
  -v /root/silk/api_server.py:/app/api_server.py \
  silk-converter:latest
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
