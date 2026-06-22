# Silence Dashboard

Tableau de bord local pour scooter électrique **Silence S01 / SEAT MÓ**, déployable en une stack Portainer.

Basé sur [silence-private-server](https://github.com/lorenzo-deluca/silence-private-server) de lorenzo-deluca pour le serveur TCP/MQTT, et sur le travail de [noiwid](https://github.com/noiwid/silence-scooter-homeassistant) pour la définition des données et l'inspiration du dashboard.

## Architecture

```
Scooter ──TCP 38955──► silence-server ──MQTT──► mosquitto ──WebSocket 9002──► navigateur :8083
```

- **silence-server** : proxy TCP qui intercepte la connexion du scooter et publie la télémétrie en MQTT
- **mosquitto** : broker MQTT (port 1883 interne + port 9001 WebSocket exposé sur 9002)
- **dashboard** : page HTML statique servie par nginx, se connecte directement au broker via MQTT/WebSocket

## Prérequis

- Docker + Portainer installés sur le serveur
- Port **38955** ouvert vers l'extérieur (le scooter doit pouvoir joindre le serveur sur ce port)
- L'**IMEI** de votre scooter (visible dans l'app Silence ou sur l'écran du scooter)

## Déploiement via Portainer

1. Dans Portainer, aller dans **Stacks → Add stack**
2. Nommer la stack (ex: `silence-dashboard`)
3. Coller le contenu ci-dessous dans l'éditeur
4. En bas, dans **Environment variables**, ajouter :
   - Nom : `IMEI` — Valeur : votre IMEI (ex: `860123456789012`)
5. Cliquer **Deploy the stack**

```yaml
services:

  init:
    image: alpine:latest
    environment:
      - IMEI=${IMEI:-TON_IMEI}
    volumes:
      - mosquitto-config:/mosquitto-config
      - silence-config:/silence-config
      - dashboard-data:/dashboard-data
    command:
      - sh
      - -c
      - |
        set -e
        RAW="https://raw.githubusercontent.com/Balou866/SilenceDashboard/master"

        # Crée le mountpoint du volume trip-data AVANT que dashboard ne monte
        # /usr/share/nginx/html en :ro (sinon mkdir impossible -> conteneur bloqué)
        mkdir -p /dashboard-data/data

        wget -qO /mosquitto-config/mosquitto.conf \
          "$$RAW/mosquitto/mosquitto.conf"

        wget -qO /tmp/config.json "$$RAW/silence/configuration.template.json"
        sed "s/TON_IMEI/$$IMEI/g" /tmp/config.json > /silence-config/configuration.json

        wget -qO /tmp/index.html "$$RAW/dashboard/index.template.html"
        sed "s/TON_IMEI/$$IMEI/g" /tmp/index.html > /dashboard-data/index.html

        wget -qO /dashboard-data/mqtt.min.js \
          "$$RAW/dashboard/mqtt.min.js"

        wget -qO /dashboard-data/rambo-silence.png \
          "$$RAW/dashboard/rambo-silence.png"

        # PWA : manifest, service worker et icônes
        wget -qO /dashboard-data/manifest.json      "$$RAW/dashboard/manifest.json"
        wget -qO /dashboard-data/sw.js              "$$RAW/dashboard/sw.js"
        wget -qO /dashboard-data/icon-192.png       "$$RAW/dashboard/icon-192.png"
        wget -qO /dashboard-data/icon-512.png       "$$RAW/dashboard/icon-512.png"
        wget -qO /dashboard-data/apple-touch-icon.png "$$RAW/dashboard/apple-touch-icon.png"

        # Leaflet (fond de carte OSM pour le tracé du trajet) — auto-hébergé
        # dans dashboard-data, servi en same-origin (cache PWA possible)
        wget -qO /dashboard-data/leaflet.css "https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"
        wget -qO /dashboard-data/leaflet.js  "https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"

        echo "Init done!"

  mosquitto:
    image: eclipse-mosquitto:latest
    container_name: mosquitto
    restart: unless-stopped
    depends_on:
      init:
        condition: service_completed_successfully
    ports:
      - "9002:9001"
    volumes:
      - mosquitto-config:/mosquitto/config
      - mosquitto-data:/mosquitto/data
    healthcheck:
      test: ["CMD", "mosquitto_pub", "-t", "health", "-m", "1", "-q", "0"]
      interval: 30s
      timeout: 5s
      retries: 5

  mqtt-retain:
    build:
      context: https://github.com/Balou866/SilenceDashboard.git
      dockerfile: mqtt-retain/Dockerfile
    container_name: silence-retain
    restart: unless-stopped
    environment:
      - TZ=Europe/Paris
    depends_on:
      mosquitto:
        condition: service_healthy
    volumes:
      - trip-data:/data

  silence-server:
    build:
      context: https://github.com/Balou866/SilenceDashboard.git
      dockerfile: silence/Dockerfile
    container_name: silence-server
    restart: unless-stopped
    environment:
      - PYTHONUNBUFFERED=1
    depends_on:
      init:
        condition: service_completed_successfully
      mosquitto:
        condition: service_healthy
    ports:
      - "38955:38955"
    volumes:
      - silence-config:/config
    entrypoint: sh -c "cp /config/configuration.json /app/configuration.json && python silence-server.py"

  dashboard:
    image: nginx:alpine
    container_name: silence-dashboard
    restart: unless-stopped
    depends_on:
      init:
        condition: service_completed_successfully
    ports:
      - "8083:80"
    volumes:
      - dashboard-data:/usr/share/nginx/html:ro
      - trip-data:/usr/share/nginx/html/data:ro

volumes:
  mosquitto-config:
  mosquitto-data:
  silence-config:
  dashboard-data:
  trip-data:
```

## Accès

| Service | URL |
|---|---|
| Dashboard scooter | `http://<ip-serveur>:8083` |

## Comportement au démarrage

Au premier lancement, le service `init` télécharge les fichiers de configuration depuis ce repo GitHub, injecte l'IMEI, et les écrit dans les volumes Docker. La page HTML est toujours régénérée depuis le template à chaque redémarrage — un changement d'IMEI dans la stack Portainer est donc pris en compte sans manipulation supplémentaire.

## Modifier la configuration

Changer l'IMEI : modifier la variable d'environnement dans la stack Portainer et redéployer.

## Changer la DNS de redirection du scooter

Le scooter doit pointer vers votre serveur sur le port 38955. Voir la documentation de [silence-private-server](https://github.com/lorenzo-deluca/silence-private-server) pour la procédure.
