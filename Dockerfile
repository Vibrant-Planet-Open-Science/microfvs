ARG FVS_TAG=FS2026.2
ARG FVS_IMAGE=ghcr.io/vibrant-planet-open-science/usfs-fvs:${FVS_TAG}

FROM ${FVS_IMAGE} AS fvs-python-base
ENV DEBIAN_FRONTEND=noninteractive
# Upgrade inherited base-image packages to pull in security patches, and
# install only python3 (uv creates its own venv, so python3-venv — which
# drags in the vulnerable python3-pip-whl — is unnecessary).
# The upgrade only sees fixes Ubuntu has published by build time. A fix
# published after an image was pushed (e.g. perl 5.38.2-3.2ubuntu0.7 for
# CVE-2026-82560) needs a new build; CI rebuilds this stage uncached on every
# merge to main. Don't purge perl-base: it is Essential on Ubuntu.
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
COPY pyproject.toml uv.lock /code/
RUN uv sync --frozen --no-dev --extra server --no-install-project
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
