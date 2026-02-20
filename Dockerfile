FROM python:3.12-slim

RUN apt-get update && apt-get install -y ffmpeg curl unzip git && rm -rf /var/lib/apt/lists/* && \
    curl -fsSL https://deno.land/install.sh | DENO_INSTALL=/usr/local sh

WORKDIR /app

# Clone bgutil PO token server (generates tokens to bypass YouTube bot detection)
RUN git clone --single-branch --branch 1.2.2 \
    https://github.com/Brainicism/bgutil-ytdlp-pot-provider.git /app/pot-server && \
    cd /app/pot-server/server && \
    deno install --allow-scripts=npm:canvas --frozen && \
    deno cache --frozen src/main.ts

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir --upgrade yt-dlp && \
    pip install --no-cache-dir bgutil-ytdlp-pot-provider

COPY . .

EXPOSE 8000
CMD ["bash", "entrypoint.sh"]
