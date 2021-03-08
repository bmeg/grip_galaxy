# build stage
FROM ubuntu:20.04 AS build-env
RUN apt-get update && apt-get install -y curl git gcc
RUN curl -L https://golang.org/dl/go1.16.linux-amd64.tar.gz | tar -xz -C /usr/local
ENV PATH="${PATH}:/usr/local/go/bin/"
WORKDIR /
RUN git clone https://github.com/bmeg/grip.git && cd grip && git checkout develop-0.7.0 && go build ./
RUN git clone https://github.com/bmeg/sifter.git && cd sifter && git checkout develop && go build ./


# final stage
FROM ubuntu:20.04
WORKDIR /data
VOLUME /data
ENV PATH="/app:${PATH}"
COPY --from=build-env /grip/grip /usr/local/bin/grip
COPY --from=build-env /sifter/sifter /usr/local/bin/sifter
RUN apt-get update && \
    apt-get install -y python3 python3-pip git && \
    pip3 install --no-cache-dir jupyterlab matplotlib pandas \
    "git+https://github.com/bmeg/grip.git@develop-0.7.0#subdirectory=gripql/python" && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

EXPOSE 8888

ADD grip_entrypoint.sh /grip_entrypoint.sh
