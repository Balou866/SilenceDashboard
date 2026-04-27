# Silence Dashboard

Tableau de bord local pour scooter électrique **Silence S01 / SEAT MÓ**, déployable en une stack Portainer.

Basé sur [silence-private-server](https://github.com/lorenzo-deluca/silence-private-server) de lorenzo-deluca.

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

        wget -qO /mosquitto-config/mosquitto.conf \
          "$$RAW/mosquitto/mosquitto.conf"

        wget -qO /tmp/config.json "$$RAW/silence/configuration.template.json"
        sed "s/TON_IMEI/$$IMEI/g" /tmp/config.json > /silence-config/configuration.json

        wget -qO /tmp/index.html "$$RAW/dashboard/index.template.html"
        sed "s/TON_IMEI/$$IMEI/g" /tmp/index.html > /dashboard-data/index.html

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
      interval: 5s
      timeout: 5s
      retries: 5

  silence-server:
    image: lorenzodeluca/silence-server:latest
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

volumes:
  mosquitto-config:
  mosquitto-data:
  silence-config:
  dashboard-data:
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
