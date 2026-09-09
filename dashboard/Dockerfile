FROM nginx:alpine

COPY dashboard/mqtt.min.js dashboard/rambo-silence.png dashboard/manifest.json \
     dashboard/sw.js dashboard/icon-192.png dashboard/icon-512.png \
     dashboard/apple-touch-icon.png /usr/share/nginx/html/

# Leaflet (fond de carte OSM du tracé) — auto-hébergé, servi en same-origin
# pour que le service worker puisse le mettre en cache.
ADD https://unpkg.com/leaflet@1.9.4/dist/leaflet.css /usr/share/nginx/html/
ADD https://unpkg.com/leaflet@1.9.4/dist/leaflet.js  /usr/share/nginx/html/
RUN chmod 644 /usr/share/nginx/html/leaflet.css /usr/share/nginx/html/leaflet.js

# Mountpoint du volume trip-data, monté en :ro sur .../html/data
RUN mkdir -p /usr/share/nginx/html/data

# Le template reste hors de la racine servie : la page publiée est l'index.html
# généré au démarrage, jamais le gabarit avec le placeholder TON_IMEI.
COPY dashboard/index.template.html /index.template.html
COPY dashboard/40-imei.sh /docker-entrypoint.d/40-imei.sh
RUN chmod +x /docker-entrypoint.d/40-imei.sh
