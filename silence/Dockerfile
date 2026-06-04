FROM python:3.9-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends git && \
    git clone --depth=1 https://github.com/lorenzo-deluca/silence-private-server.git . && \
    apt-get purge -y git && apt-get autoremove -y && rm -rf /var/lib/apt/lists/* && \
    pip install --no-cache-dir -r requirements.txt

COPY silence/helpers/messageParser.py helpers/messageParser.py
COPY silence/helpers/commands_definition.json helpers/commands_definition.json
COPY silence/services/CommandService.py services/CommandService.py

CMD ["python", "silence-server.py"]
