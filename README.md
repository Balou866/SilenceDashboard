# 🛵 Silence Dashboard

Tableau de bord auto-hébergé pour scooter électrique **Silence S01 / SEAT MÓ**.
Une stack Docker à coller dans Portainer : votre scooter se connecte à **votre** serveur, et vous suivez tout depuis un navigateur — sans cloud, sans compte, sans app.

## 📸 Aperçu

<!-- Déposez vos captures d'écran dans docs/screenshots/ puis décommentez / adaptez : -->
<!--
![Vue d'ensemble du dashboard](docs/screenshots/dashboard.png)
![Version mobile](docs/screenshots/mobile.png)
-->

> _Captures d'écran à venir._

## ✨ Fonctionnalités

- **Télémétrie en direct** : vitesse, batterie (SOC), odomètre, températures, état de charge — poussés en MQTT/WebSocket dès que le scooter émet
- **Commandes à distance** : allumer / éteindre, ouvrir la selle, flash, klaxon+flash, synchronisation immédiate (`SYNC`)
- **Deux modes d'affichage** : *sobre* (l'essentiel : batterie, autonomie, statut, trajets, position) ou *technique* (cockpit complet : cellules batterie, diagnostics, sparklines)
- **Historique des trajets** : détection automatique (une session moteur = un trajet), avec durée, distance, consommation, vitesses, efficacité Wh/km et **tracé GPS sur carte OSM** (Leaflet)
- **Position en direct** : carte avec marqueur suivi au fil des fixes GPS
- **Coûts d'usage** : estimation semaine / mois / total selon votre tarif électricité
- **PWA** : installable sur l'écran d'accueil mobile, fonctionne hors ligne (shell)

## 🏗️ Architecture

```
Scooter ──TCP 38955──► silence-server ──MQTT──► mosquitto ──WebSocket 9002──► navigateur :8083
```

| Service | Rôle |
|---|---|
| `init` | Télécharge les configs depuis ce repo, injecte l'IMEI, puis s'arrête |
| `silence-server` | Proxy TCP qui intercepte la connexion du scooter et publie la télémétrie en MQTT |
| `mosquitto` | Broker MQTT (1883 interne, WebSocket 9001 exposé sur 9002) |
| `mqtt-retain` | Republie les messages en `retain` (snapshot instantané au chargement) et enregistre les trajets dans `trips.json` |
| `dashboard` | Page HTML statique servie par nginx, connectée directement au broker en WebSocket |

Aucun middleware (pas de Node-RED, pas de base de données externe).

## ✅ Prérequis

- Docker + Portainer sur votre serveur
- Port **38955** joignable par le scooter (ouverture/redirection selon votre réseau)
- L'**IMEI** du scooter (visible dans l'app Silence ou sur l'écran du scooter)
- Le scooter redirigé vers votre serveur — voir la [documentation de silence-private-server](https://github.com/lorenzo-deluca/silence-private-server)

## 🚀 Déploiement (Portainer)

1. **Stacks → Add stack**, nommer la stack (ex. `silence-dashboard`)
2. Coller le compose ci-dessous dans l'éditeur
3. Dans **Environment variables**, ajouter : `IMEI` = votre IMEI (ex. `860123456789012`)
4. **Deploy the stack**

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

## 🌐 Accès et ports

| Port | Service |
|---|---|
| **8083** | Dashboard (`http://<ip-serveur>:8083`) |
| 9002 | MQTT WebSocket (mosquitto) |
| 38955 | Connexion TCP du scooter (silence-server) |

## ⚙️ Configuration

Seul paramètre requis : **`IMEI`** (variable d'environnement de la stack).

À chaque (re)déploiement, le service `init` retélécharge les fichiers depuis ce repo et réinjecte l'IMEI — changer d'IMEI = modifier la variable dans Portainer et redéployer, rien d'autre.

## 📡 Topics MQTT

- Télémétrie : `home/silence-server/<IMEI>/status` (JSON)
- Commandes : `home/silence-server/<IMEI>/command/<CMD>` — `TURN_ON_SCOOTER`, `TURN_OFF_SCOOTER`, `OPEN_SEAT`, `FLASH`, `BEEP_FLASH`, `SYNC`

## 🙏 Crédits

- [lorenzo-deluca/silence-private-server](https://github.com/lorenzo-deluca/silence-private-server) — serveur TCP/MQTT et rétro-ingénierie du protocole
- [noiwid/silence-scooter-homeassistant](https://github.com/noiwid/silence-scooter-homeassistant) — définition des données et inspiration du dashboard
