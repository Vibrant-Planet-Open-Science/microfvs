FROM daviddanieldiaz/fvs:FS2025.4c

RUN groupadd -g 5000 microfvs-dev && \
    useradd -m -u 5000 -g microfvs-dev microfvs-dev
RUN chown microfvs-dev:microfvs-dev /home/microfvs-dev
USER microfvs-dev
COPY requirements.txt /tmp/requirements.txt
RUN pip install --upgrade pip && pip install --no-cache-dir -r /tmp/requirements.txt
