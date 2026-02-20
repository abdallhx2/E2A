FROM python:3.12-slim

RUN apt-get update && \
    apt-get install -y ffmpeg curl unzip git && \
    curl -fsSL https://deb.nodesource.com/setup_20.x | bash - && \
    apt-get install -y nodejs && \
    rm -rf /var/lib/apt/lists/* && \
    curl -fsSL https://deno.land/install.sh | DENO_INSTALL=/usr/local sh

WORKDIR /app

# Clone bgutil PO token server, install deps, compile TypeScript
RUN git clone --single-branch --branch 1.2.2 \
    https://github.com/Brainicism/bgutil-ytdlp-pot-provider.git /app/pot-server && \
    cd /app/pot-server/server && \
    npm ci --no-audit --no-fund && \
    npx tsc && \
    npm prune --production

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir --upgrade yt-dlp && \
    pip install --no-cache-dir bgutil-ytdlp-pot-provider

COPY . .

EXPOSE 8000
CMD ["python", "start.py"]
