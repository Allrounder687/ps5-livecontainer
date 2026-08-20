FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive
ENV PS5_PAYLOAD_SDK=/opt/ps5-payload-sdk

RUN apt-get update && apt-get install -y \
    build-essential \
    clang-15 \
    lld-15 \
    git \
    python3-pyelftools \
    && rm -rf /var/lib/apt/lists/*

RUN ln -sf /usr/bin/clang-15 /usr/bin/clang && \
    ln -sf /usr/bin/clang++-15 /usr/bin/clang++ && \
    ln -sf /usr/bin/lld-15 /usr/bin/lld && \
    ln -sf /usr/bin/lld-15 /usr/bin/ld.lld

RUN git clone https://github.com/john-tornblom/ps5-payload-sdk.git ${PS5_PAYLOAD_SDK}
WORKDIR ${PS5_PAYLOAD_SDK}
RUN make -j$(nproc)

WORKDIR /app
CMD ["make"]
