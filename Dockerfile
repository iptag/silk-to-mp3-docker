# ===================================================================
# Stage 1: silk-builder - 编译 silk 解码器
# 职责：只负责编译生成 silk 的 decoder 可执行文件
# ===================================================================
FROM debian:buster-slim AS silk-builder

# 1. 安装编译依赖，使用 --no-install-recommends 减少不必要的安装，并清理缓存
RUN apt-get update && \
    apt-get install -y --no-install-recommends make gcc g++ && \
    rm -rf /var/lib/apt/lists/*

# 2. 拷贝源代码并编译
COPY silk /app/silk/
WORKDIR /app/silk
RUN make && make decoder


# ===================================================================
# Stage 2: ffmpeg-builder - 编译 FFmpeg
# 职责：独立编译 FFmpeg，将编译工具链和源码隔离在此阶段
# ===================================================================
FROM debian:buster AS ffmpeg-builder

# 1. 安装 FFmpeg 编译依赖
#    *** 修正：添加 ca-certificates 以解决 wget 的 SSL 证书验证错误 ***
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        ca-certificates \
        wget build-essential yasm cmake libtool \
        libopencore-amrnb-dev libopencore-amrwb-dev && \
    rm -rf /var/lib/apt/lists/*

# 2. 下载、编译和安装 FFmpeg
WORKDIR /usr/src
RUN wget -q https://ffmpeg.org/releases/ffmpeg-7.1.1.tar.xz && \
    tar -xf ffmpeg-7.1.1.tar.xz && \
    cd ffmpeg-7.1.1 && \
    ./configure \
        --enable-version3 \
        --enable-gpl \
        --enable-nonfree \
        --enable-libopencore-amrnb \
        --enable-libopencore-amrwb && \
    make -j$(nproc) install && \
    cd /usr/src && \
    rm -rf ffmpeg-7.1.1 ffmpeg-7.1.1.tar.xz


# ===================================================================
# Stage 3: Final - 最终运行阶段
# 职责：构建最小化的运行环境
# ===================================================================
FROM python:3.8-slim-buster

# 设置环境变量
ENV DEBIAN_FRONTEND=noninteractive

# 1. 安装 Python 依赖和 FFmpeg 的「运行时」依赖
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        libopencore-amrnb0 \
        libopencore-amrwb0 && \
    pip install --no-cache-dir flask && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

# 2. 从 'silk-builder' 阶段拷贝已编译好的 silk decoder
COPY --from=silk-builder /app/silk/decoder /app/silk/decoder

# 3. 从 'ffmpeg-builder' 阶段拷贝已编译好的 ffmpeg 二进制文件及其依赖的动态库
COPY --from=ffmpeg-builder /usr/local/bin/ffmpeg /usr/local/bin/
COPY --from=ffmpeg-builder /usr/local/lib/ /usr/local/lib/

# 4. 拷贝应用代码和脚本
COPY api_server.py .
COPY silk.sh .

# 5. 更新动态链接库缓存并赋予脚本执行权限
RUN ldconfig && chmod +x /app/silk.sh

# 暴露端口
EXPOSE 8321

# 启动服务
CMD ["python3", "api_server.py"]
