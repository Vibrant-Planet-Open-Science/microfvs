FROM python:3.11-slim

USER root

WORKDIR /build
ENV FC=gfortran
RUN apt-get update &&\
 apt-get install -y git build-essential gfortran cmake unixodbc-dev rename 
RUN git clone --recurse-submodules https://github.com/USDAForestService/ForestVegetationSimulator.git --branch FS2024.4 &&\
 cd /build/ForestVegetationSimulator/volume/NVEL &&\
 rename 'y/A-Z/a-z/' *
RUN cd /build/ForestVegetationSimulator/bin &&\
 make US -j5 &&\
 mv /build/ForestVegetationSimulator/bin/FVS??.so /usr/local/lib &&\ 
 mv /build/ForestVegetationSimulator/bin/FVS?? /usr/local/bin &&\
 rm -rf /build
RUN apt-get clean &&\
 rm -rf /var/lib/apt/lists/*

WORKDIR /code
COPY ./requirements.txt /code/requirements.txt
ENV PIP_PREFER_BINARY=1
RUN pip install --upgrade pip pip-tools &&\
 pip install --no-cache-dir --upgrade -r /code/requirements.txt
COPY ./microfvs /code/microfvs

CMD ["uvicorn", "microfvs.main:app", "--host", "0.0.0.0", "--port", "80"]