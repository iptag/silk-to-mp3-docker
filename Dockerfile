# =============================================
# Stage 1: Builder - 编译阶段
# =============================================
FROM ubuntu:20.04 AS builder

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y \
    make gcc g++ \
    wget build-essential coreutils yasm cmake libtool \
    libopencore-amrnb-dev libopencore-amrwb-dev \
    libmp3lame-dev \
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
        --enable-libmp3lame \
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

# 确保二进制文件有执行权限
RUN chmod +x /opt/ffmpeg/bin/ffmpeg /app/silk/decoder

# =============================================
# Stage 2: 运行时镜像 - 使用distroless
# (此阶段保持不变)
# =============================================
FROM gcr.io/distroless/python3-debian11

ENV PYTHONPATH=/app/deps

WORKDIR /app

# 使用 --chown 将所有拷贝的文件和目录的所有者设置为 nonroot
COPY --from=builder --chown=nonroot:nonroot /app/deps /app/deps
COPY --from=builder /opt/ffmpeg/bin/ffmpeg /usr/local/bin/ffmpeg
COPY --from=builder /app/silk/decoder /app/silk/decoder
COPY --chown=nonroot:nonroot api_server.py .

EXPOSE 8321

CMD ["api_server.py"]
