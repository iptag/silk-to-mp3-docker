# =============================================
# Stage 1: Builder - 编译阶段
# 使用一个包含完整构建工具的镜像来编译代码
# =============================================
FROM ubuntu:20.04 AS builder

# 1. 安装编译所需的依赖
#    *** FIX: 添加 g++ 以解决链接错误 ***
RUN apt-get update && apt-get install -y make gcc g++

# 2. 拷贝源代码并编译
COPY silk /app/silk/
WORKDIR /app/silk
# 将两条 make 命令合并为一条，因为 make decoder 通常会依赖 make 的结果
RUN make && make decoder


# =============================================
# Stage 2: Final - 最终运行阶段
# 使用一个轻量的 Python 官方镜像
# =============================================
FROM python:3.8-slim-buster

# 设置环境变量，避免交互提示
ENV DEBIAN_FRONTEND=noninteractive

# 1. 安装仅在运行时需要的依赖
#    - 使用 --no-install-recommends 避免安装不必要的包
#    - 安装完成后立即清理 apt 缓存
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# 2. 安装 Python 依赖
#    - 使用 --no-cache-dir 避免缓存，减小镜像层大小
RUN pip install --no-cache-dir flask

# 3. 从 'builder' 阶段拷贝已编译好的文件
COPY --from=builder /app/silk/decoder /app/silk/decoder
COPY api_server.py .
COPY silk.sh .
RUN chmod +x /app/silk.sh

# 暴露端口
EXPOSE 8321

# 启动服务
CMD ["python3", "api_server.py"]
