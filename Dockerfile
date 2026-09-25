# syntax=docker/dockerfile:1
ARG FVS_TAG=FS2026.2
ARG FVS_IMAGE=ghcr.io/vibrant-planet-open-science/usfs-fvs:${FVS_TAG}

FROM ${FVS_IMAGE} AS fvs-python-base
ENV DEBIAN_FRONTEND=noninteractive
# Upgrade inherited base-image packages to pull in security patches, and
# install only python3 (uv creates its own venv, so python3-venv — which
# drags in the vulnerable python3-pip-whl — is unnecessary).
RUN apt-get update \
    && apt-get upgrade -y --no-install-recommends \
    && apt-get install -y --no-install-recommends \
    python3 \
    && rm -rf /var/lib/apt/lists/*
COPY --from=ghcr.io/astral-sh/uv:0.7 /uv /uvx /bin/

FROM fvs-python-base AS runtime-base
ENV UV_PROJECT_ENVIRONMENT=/opt/venv
RUN uv venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH" \
    VIRTUAL_ENV="/opt/venv"

FROM runtime-base AS microfvs
LABEL org.opencontainers.image.licenses=MIT
WORKDIR /code
# Bind-mount the project files rather than COPY them: uv.lock also pins the dev
# extras, and leaving it in the image makes scanners report those packages as
# present even though they are never installed.
RUN --mount=type=bind,source=pyproject.toml,target=/code/pyproject.toml \
    --mount=type=bind,source=uv.lock,target=/code/uv.lock \
    uv sync --frozen --no-dev --no-install-project
COPY microfvs /code/microfvs
EXPOSE 8080
CMD ["uvicorn", "microfvs.main:app", "--host", "0.0.0.0", "--port", "8080", "--root-path", "/microfvs"]

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
