ARG FVS_TAG=FS2026.1
ARG FVS_IMAGE=ghcr.io/vibrant-planet-open-science/usfs-fvs:${FVS_TAG}

FROM ${FVS_IMAGE} AS runtime-base
ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
    python3 \
    python3-pip \
    python3-venv \
    && rm -rf /var/lib/apt/lists/*
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
RUN apt-get update \
    && apt-get install -y --no-install-recommends git sudo \
    && rm -rf /var/lib/apt/lists/* \
    && if id -u ubuntu >/dev/null 2>&1; then \
    usermod -l microfvs-dev ubuntu \
    && groupmod -n microfvs-dev ubuntu \
    && usermod -d /home/microfvs-dev -m microfvs-dev; \
    fi
COPY requirements.txt requirements-dev.txt /tmp/
RUN pip install --upgrade pip \
    && pip install --no-cache-dir -r /tmp/requirements.txt \
    && pip freeze > /tmp/constraints.txt \
    && pip install --no-cache-dir -r /tmp/requirements-dev.txt -c /tmp/constraints.txt
WORKDIR /workspaces/microfvs
