FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .


# 修改 Debian 软件源
RUN sed -i 's|deb.debian.org|mirrors.aliyun.com|g' /etc/apt/sources.list.d/debian.sources || true


RUN apt-get update && apt-get install -y \
    gcc \
    pkg-config \
    default-libmysqlclient-dev \
    && rm -rf /var/lib/apt/lists/*


RUN pip install --no-cache-dir -r requirements.txt


COPY . .


CMD ["gunicorn","tripgenius.wsgi:application","--bind","0.0.0.0:8000"]