# =============================================
# Stage 1: Builder - 编译阶段
# =============================================
FROM ubuntu:22.04 AS builder

ENV DEBIAN_FRONTEND=noninteractive

# 安装编译所需的所有依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    make gcc g++ python3 python3-pip python3-dev git-core sed \
    libopencore-amrnb-dev libopencore-amrwb-dev \
    autoconf automake build-essential cmake coreutils libaom-dev libass-dev \
    libdav1d-dev libfreetype6-dev libgnutls28-dev libmp3lame-dev libsdl2-dev \
    libtool libunistring-dev libva-dev libvdpau-dev libvorbis-dev \
    libxcb-shm0-dev libxcb-xfixes0-dev libxcb1-dev meson ninja-build \
    pkg-config texinfo wget yasm zlib1g-dev \
    && rm -rf /var/lib/apt/lists/*

# 编译FFmpeg (保持不变)
RUN wget -q https://ffmpeg.org/releases/ffmpeg-7.1.1.tar.xz && \
    tar -xf ffmpeg-7.1.1.tar.xz && \
    cd ffmpeg-7.1.1 && \
    ./configure \
        --prefix=/opt/ffmpeg --enable-version3 --enable-gpl --enable-nonfree \
        --enable-libopencore-amrnb --enable-libopencore-amrwb \
        --enable-libmp3lame --enable-libvorbis --disable-doc --disable-htmlpages \
        --disable-manpages --disable-podpages --disable-txtpages --disable-debug \
        --enable-static --disable-shared --extra-cflags="-static" \
        --extra-ldflags="-static" --pkg-config-flags="--static" && \
    make -j$(nproc) install && \
    strip /opt/ffmpeg/bin/ffmpeg /opt/ffmpeg/bin/ffprobe && \
    cd .. && \
    rm -rf ffmpeg-7.1.1 ffmpeg-7.1.1.tar.xz

# 编译 SILK 库和我们自己的编码器
COPY silk_encoder /app/silk_encoder/
COPY silk_decoder /app/silk_decoder/
COPY custom_encoder.cpp /app/

WORKDIR /app/silk_encoder

# 使用node-silk兼容的编译设置 - 只编译静态库
RUN make clean || true
RUN make lib

WORKDIR /app
# Build custom_encoder with correct linking
RUN echo "Building custom_encoder..." && \
    g++ -std=c++11 -O3 -Wall custom_encoder.cpp \
    -I/app/silk_encoder/interface -I/app/silk_encoder/src \
    /app/silk_encoder/libSKP_SILK_SDK.a \
    -o custom_encoder && \
    echo "Custom encoder built successfully"

# Build silk_decoder decoder (the working one)
WORKDIR /app/silk_decoder
RUN echo "Building silk_decoder decoder..." && \
    make clean || true && \
    make all && \
    echo "Silk_decoder decoder built successfully"

WORKDIR /app
RUN strip /app/custom_encoder /app/silk_decoder/decoder

# 安装Python依赖
RUN pip3 install --target /app/deps flask

# 为所有二进制文件添加可执行权限
RUN chmod +x /opt/ffmpeg/bin/ffmpeg /opt/ffmpeg/bin/ffprobe /app/custom_encoder /app/silk_decoder/decoder

# =============================================
# Stage 2: 运行时镜像 - 使用带shell的镜像用于调试
# =============================================
FROM python:3.11-slim-bookworm

# 安装调试工具
RUN apt-get update && apt-get install -y --no-install-recommends \
    bc xxd file && \
    rm -rf /var/lib/apt/lists/*

ENV PYTHONPATH=/app/deps
WORKDIR /app

# 安装Python依赖
RUN pip3 install flask

# ==================== 复制编译好的文件 ====================
COPY --from=builder /opt/ffmpeg/bin/ffmpeg /usr/local/bin/ffmpeg
COPY --from=builder /opt/ffmpeg/bin/ffprobe /usr/local/bin/ffprobe
COPY --from=builder /app/custom_encoder /app/silk_encoder/encoder
COPY --from=builder /app/silk_decoder/decoder /app/silk_decoder/decoder

# 确保所有二进制文件有执行权限
RUN chmod +x /usr/local/bin/ffmpeg /usr/local/bin/ffprobe /app/silk_encoder/encoder /app/silk_decoder/decoder
# =========================================================
COPY api_server.py .

EXPOSE 8321
CMD ["python3", "api_server.py"]