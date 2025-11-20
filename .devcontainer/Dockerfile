FROM daviddanieldiaz/fvs:FS2025.4c

RUN groupadd -g 1000 microfvs-dev && \
    useradd -m -u 1000 -g microfvs-dev microfvs-dev
RUN chown microfvs-dev:microfvs-dev /home/microfvs-dev
COPY requirements.txt .
RUN pip install --upgrade pip && pip install --no-cache-dir -r requirements.txt && rm requirements.txt
USER microfvs-dev