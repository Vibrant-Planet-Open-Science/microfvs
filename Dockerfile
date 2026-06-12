ARG FVS_TAG=FS2026.1
ARG FVS_IMAGE=ghcr.io/vibrant-planet-open-science/usfs-fvs:${FVS_TAG}

FROM ${FVS_IMAGE} AS fvs-python-base
ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
    python3 \
    python3-venv \
    && rm -rf /var/lib/apt/lists/*
COPY --from=ghcr.io/astral-sh/uv:0.7 /uv /uvx /bin/

FROM fvs-python-base AS runtime-base
ENV UV_PROJECT_ENVIRONMENT=/opt/venv
RUN uv venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH" \
    VIRTUAL_ENV="/opt/venv"

FROM runtime-base AS microfvs
WORKDIR /code
COPY pyproject.toml uv.lock /code/
RUN uv sync --frozen --no-dev --no-install-project
COPY microfvs /code/microfvs
EXPOSE 80
CMD ["uvicorn", "microfvs.main:app", "--host", "0.0.0.0", "--port", "80", "--root-path", "/microfvs"]

FROM fvs-python-base AS dev
RUN apt-get update \
    && apt-get install -y --no-install-recommends wget \
    && rm -rf /var/lib/apt/lists/* \
    && if id -u ubuntu >/dev/null 2>&1; then \
    usermod -l microfvs-dev ubuntu \
    && groupmod -n microfvs-dev ubuntu \
    && usermod -d /home/microfvs-dev -m microfvs-dev; \
    fi
WORKDIR /workspaces/microfvs
