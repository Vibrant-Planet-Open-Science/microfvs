ARG FVS_TAG=FS2026.1
ARG FVS_IMAGE=ghcr.io/vibrant-planet-open-science/usfs-fvs:${FVS_TAG}
FROM ${FVS_IMAGE} AS fvs

FROM ubuntu:24.04 AS runtime-base
ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        libgfortran5 \
        libquadmath0 \
        python3 \
        python3-pip \
        python3-venv \
    && rm -rf /var/lib/apt/lists/*
COPY --from=fvs /usr/local/bin/FVS* /usr/local/bin/
COPY --from=fvs /usr/local/lib/libFVS*.so /usr/local/lib/
RUN chmod +x /usr/local/bin/FVS* && ldconfig
RUN python3 -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH" \
    VIRTUAL_ENV="/opt/venv" \
    PIP_PREFER_BINARY=1

FROM runtime-base AS microfvs
WORKDIR /code
COPY requirements.txt /code/requirements.txt
RUN pip install --no-cache-dir -r /code/requirements.txt
COPY microfvs /code/microfvs
EXPOSE 80
CMD ["uvicorn", "microfvs.main:app", "--host", "0.0.0.0", "--port", "80"]

FROM runtime-base AS dev
RUN groupadd -g 5000 microfvs-dev \
    && useradd -m -u 5000 -g microfvs-dev microfvs-dev
COPY requirements.txt /tmp/requirements.txt
RUN pip install --upgrade pip \
    && pip install --no-cache-dir -r /tmp/requirements.txt
USER microfvs-dev
WORKDIR /workspaces/microfvs
