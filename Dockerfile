FROM ubuntu:latest AS builder

USER root

WORKDIR /build
ENV FC=gfortran
ARG FVS_VERSION
RUN apt-get update &&\
    apt-get install -y git build-essential gfortran cmake unixodbc-dev
RUN git clone -b "${FVS_VERSION}" --recurse-submodules https://github.com/USDAForestService/ForestVegetationSimulator.git 
RUN cd /build/ForestVegetationSimulator/bin &&\
    make US


FROM python:3.11-slim AS runtime
RUN apt-get update &&\
    apt-get install -y git build-essential gfortran cmake unixodbc-dev &&\
    pip install --upgrade pip pip-tools &&\
    pip install --no-cache-dir --upgrade pytest &&\
    apt-get clean &&\
    rm -rf /var/lib/apt/lists/*
COPY --from=builder /build/ForestVegetationSimulator/bin/FVS??.so /usr/local/lib
COPY --from=builder /build/ForestVegetationSimulator/bin/FVS?? /usr/local/bin

WORKDIR /code
COPY ./requirements.txt /code/requirements.txt
ENV PIP_PREFER_BINARY=1
RUN pip install --upgrade pip pip-tools &&\
    pip install --no-cache-dir --upgrade -r /code/requirements.txt
COPY ./microfvs /code/microfvs
CMD ["uvicorn", "microfvs.main:app", "--host", "0.0.0.0", "--port", "80"]