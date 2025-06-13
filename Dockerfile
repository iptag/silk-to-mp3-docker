# =============================================
# Stage 1: Builder - 编译阶段
# =============================================
FROM ubuntu:20.04 AS builder

ENV DEBIAN_FRONTEND=noninteractive

# 安装编译依赖
RUN apt-get update && apt-get install -y \
    make gcc g++ \
    wget build-essential yasm cmake libtool \
    libopencore-amrnb-dev libopencore-amrwb-dev \
    python3 python3-pip python3-dev \
    && rm -rf /var/lib/apt/lists/*

# 编译静态链接的FFmpeg
RUN wget -q https://ffmpeg.org/releases/ffmpeg-7.1.1.tar.xz && \
    tar -xf ffmpeg-7.1.1.tar.xz && \
    cd ffmpeg-7.1.1 && \
    ./configure \
        --prefix=/opt/ffmpeg \
        --enable-version3 \
        --enable-gpl \
        --enable-nonfree \
        --enable-libopencore-amrnb \
        --enable-libopencore-amrwb \
        --disable-doc \
        --disable-htmlpages \
        --disable-manpages \
        --disable-podpages \
        --disable-txtpages \
        --disable-debug \
        --enable-static \
        --disable-shared \
        --extra-cflags="-static" \
        --extra-ldflags="-static" \
        --pkg-config-flags="--static" && \
    make install && \
    strip /opt/ffmpeg/bin/ffmpeg && \
    cd .. && \
    rm -rf ffmpeg-7.1.1 ffmpeg-7.1.1.tar.xz

# 编译silk decoder
COPY silk /app/silk/
WORKDIR /app/silk
RUN make && make decoder && strip decoder

# 安装Python依赖到指定目录
RUN pip3 install --target /app/deps flask

# =============================================
# Stage 2: 运行时镜像 - 使用distroless
# =============================================
FROM gcr.io/distroless/python3-debian11

# 设置Python路径
ENV PYTHONPATH=/app/deps

# 拷贝必要文件
COPY --from=builder /opt/ffmpeg/bin/ffmpeg /usr/local/bin/ffmpeg
COPY --from=builder /app/silk/decoder /app/silk/decoder
COPY --from=builder /app/deps /app/deps

# 拷贝应用文件
COPY api_server.py /app/
COPY silk.sh /app/

WORKDIR /app

# 暴露端口
EXPOSE 8321

# 启动命令
CMD ["api_server.py"]
