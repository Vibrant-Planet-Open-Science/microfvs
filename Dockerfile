FROM daviddanieldiaz/fvs:FS2024.4

WORKDIR /code
COPY ./requirements.txt /code/requirements.txt
ENV PIP_PREFER_BINARY=1
RUN pip install --upgrade pip pip-tools &&\
 pip install --no-cache-dir --upgrade -r /code/requirements.txt
COPY ./microfvs /code/microfvs

CMD ["uvicorn", "microfvs.main:app", "--host", "0.0.0.0", "--port", "80"]