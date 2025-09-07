# =============================================
# Stage 1: Builder - 编译阶段
# =============================================
FROM ubuntu:20.04 AS builder

ENV DEBIAN_FRONTEND=noninteractive

# 安装编译所需的依赖
RUN apt-get update && apt-get install -y \
    make gcc g++ \
    wget build-essential coreutils yasm cmake libtool \
    libopencore-amrnb-dev libopencore-amrwb-dev \
    libmp3lame-dev \
    python3 python3-pip python3-dev \
    && rm -rf /var/lib/apt/lists/*

# 编译FFmpeg
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
    strip /opt/ffmpeg/bin/ffmpeg /opt/ffmpeg/bin/ffprobe && \
    cd .. && \
    rm -rf ffmpeg-7.1.1 ffmpeg-7.1.1.tar.xz

# 复制silk源码并进行编译
COPY silk /app/silk/
WORKDIR /app/silk
# 修改: 同时编译 decoder 和 encoder, 并使用 strip 减小体积
RUN make && make decoder && make encoder && strip decoder encoder

# 安装Python依赖
RUN pip3 install --target /app/deps flask

# 为所有二进制文件添加可执行权限
RUN chmod +x /opt/ffmpeg/bin/ffmpeg /opt/ffmpeg/bin/ffprobe /app/silk/decoder /app/silk/encoder

# =============================================
# Stage 2: 运行时镜像 - 使用distroless
# =============================================
FROM gcr.io/distroless/python3-debian11

ENV PYTHONPATH=/app/deps
WORKDIR /app

COPY --from=builder --chown=nonroot:nonroot /app/deps /app/deps
COPY --from=builder /opt/ffmpeg/bin/ffmpeg /usr/local/bin/ffmpeg
COPY --from=builder /opt/ffmpeg/bin/ffmpeg /usr/local/bin/ffmpeg
COPY --from=builder /opt/ffmpeg/bin/ffprobe /usr/local/bin/ffprobe
COPY --from=builder /app/silk/decoder /app/silk/decoder
COPY --from=builder /app/silk/encoder /app/silk/encoder
COPY --chown=nonroot:nonroot api_server.py .
COPY --from=builder /usr/lib/x86_64-linux-gnu/libmp3lame.so.0 /usr/lib/x86_64-linux-gnu/

EXPOSE 8321
CMD ["api_server.py"]
