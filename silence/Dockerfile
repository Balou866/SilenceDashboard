FROM python:3.9-slim

WORKDIR /app
ENV PYTHONUNBUFFERED=1

# Tarball de l'upstream plutôt qu'un git clone : pas d'apt install git, et
# BuildKit revalide l'URL à chaque build (un nouveau commit upstream invalide
# le cache, ce que le clone dans un RUN ne faisait pas).
ADD https://github.com/lorenzo-deluca/silence-private-server/archive/refs/heads/master.tar.gz /tmp/upstream.tgz
RUN tar xzf /tmp/upstream.tgz --strip-components=1 && rm /tmp/upstream.tgz && \
    pip install --no-cache-dir -r requirements.txt

COPY silence/configuration.template.json /configuration.template.json
CMD sed "s/TON_IMEI/$IMEI/g" /configuration.template.json > /app/configuration.json && python silence-server.py
