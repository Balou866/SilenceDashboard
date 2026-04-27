# Silence Dashboard

Tableau de bord local pour scooter électrique **Silence S01 / SEAT MÓ**, déployable en une stack Portainer.

Basé sur [silence-private-server](https://github.com/lorenzo-deluca/silence-private-server) de lorenzo-deluca.

## Architecture

```
Scooter ──TCP 38955──► silence-server ──MQTT──► mosquitto ──MQTT──► Node-RED ──► navigateur :1880/ui
```

- **silence-server** : proxy TCP qui intercepte la connexion du scooter et publie la télémétrie en MQTT
- **mosquitto** : broker MQTT interne
- **Node-RED** : dashboard web avec jauges, état, et boutons de commande

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
      - nodered-data:/nodered-data
    command:
      - sh
      - -c
      - |
        set -e
        RAW="https://raw.githubusercontent.com/Balou866/SilenceDashboard/main"

        wget -qO /mosquitto-config/mosquitto.conf \
          "$$RAW/mosquitto/mosquitto.conf"

        wget -qO- "$$RAW/silence/configuration.template.json" | \
          sed "s/TON_IMEI/$$IMEI/g" > /silence-config/configuration.json

        wget -qO /nodered-data/package.json \
          "$$RAW/nodered/package.json"

        if [ ! -f /nodered-data/flows.json ]; then
          wget -qO- "$$RAW/nodered/flows.template.json" | \
            sed "s/TON_IMEI/$$IMEI/g" > /nodered-data/flows.json
        fi

        echo "Init done!"

  mosquitto:
    image: eclipse-mosquitto:latest
    container_name: mosquitto
    restart: unless-stopped
    depends_on:
      init:
        condition: service_completed_successfully
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

  nodered:
    image: nodered/node-red:3
    container_name: nodered
    restart: unless-stopped
    depends_on:
      init:
        condition: service_completed_successfully
      mosquitto:
        condition: service_started
    ports:
      - "1880:1880"
    volumes:
      - nodered-data:/data
    entrypoint: sh -c "cd /data && npm install 2>&1 | tail -3 && node-red --userDir /data"

volumes:
  mosquitto-config:
  mosquitto-data:
  silence-config:
  nodered-data:
```

## Accès

| Service | URL |
|---|---|
| Dashboard scooter | `http://<ip-serveur>:1880/ui` |
| Éditeur Node-RED | `http://<ip-serveur>:1880` |

## Comportement au démarrage

Au premier lancement, le service `init` télécharge automatiquement les fichiers de configuration depuis ce repo GitHub, injecte l'IMEI, et les écrit dans les volumes Docker. Les autres services attendent sa complétion avant de démarrer.

Les flows Node-RED ne sont écrits **qu'au premier démarrage**. Toute personnalisation faite via l'éditeur Node-RED est préservée aux redémarrages suivants.

## Modifier la configuration

Changer l'IMEI ou tout autre paramètre : modifier la variable d'environnement dans la stack Portainer et redéployer.

Pour **réinitialiser les flows** Node-RED (effacer les personnalisations) : supprimer le volume `nodered-data` depuis Portainer avant de redéployer.

## Changer la DNS de redirection du scooter

Le scooter doit pointer vers votre serveur sur le port 38955. La procédure dépend de votre routeur/DNS local — voir la documentation de [silence-private-server](https://github.com/lorenzo-deluca/silence-private-server) pour les détails.
