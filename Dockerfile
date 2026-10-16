# Dockerfile cho Hugging Face Spaces
# Su dung Python 3.12 slim de giam kich thuoc image
FROM python:3.12-slim

# Cai cac package he thong can thiet
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    g++ \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Tao user non-root (HF khuyen nghi)
RUN useradd -m -u 1000 user
USER user
ENV HOME=/home/user \
    PATH=/home/user/.local/bin:$PATH

# Set working directory
WORKDIR /home/user/app

# Copy requirements truoc de tan dung cache layer
COPY --chown=user requirements.txt ./

# Cai Python packages vao user space
RUN pip install --no-cache-dir --user --upgrade pip && \
    pip install --no-cache-dir --user -r requirements.txt

# Copy toan bo code
COPY --chown=user . .

# Hugging Face Spaces luon listen o port 7860
ENV PORT=7860
EXPOSE 7860

# Chay server (server.py da duoc patch de doc PORT env)
CMD ["python", "server.py"]