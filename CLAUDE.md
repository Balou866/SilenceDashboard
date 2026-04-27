# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Silence-Dashboard is a self-hosted Docker stack for managing a Silence S01 / SEAT MÓ electric scooter locally. It proxies the scooter's TCP connection through `silence-private-server`, publishes telemetry to Mosquitto via MQTT, and exposes a Node-RED dashboard on port 1880.

Upstream references:
- Proxy server: https://github.com/lorenzo-deluca/silence-private-server
- Home Assistant integration (sensors/entities reference): https://github.com/noiwid/silence-scooter-homeassistant

## Architecture

```
Scooter  ──TCP 38955──▶  silence-server  ──MQTT──▶  mosquitto  ──MQTT──▶  node-red  ──▶  browser :1880/ui
                          (bridge mode:                                      (node-red-dashboard)
                           also forwards to
                           api.connectivity.silence.eco)
```

**Service startup order** (enforced via `depends_on`):
1. `init` — télécharge les fichiers de config depuis le repo GitHub public et les écrit dans les named volumes. Se termine avant que les autres services démarrent.
2. `mosquitto` — broker MQTT, démarre après `init`.
3. `silence-server` et `nodered` — démarrent après `init` + `mosquitto`.

**Named volumes** (persistance) :
- `mosquitto-config` — contient `mosquitto.conf` (réécrit à chaque démarrage par `init`)
- `mosquitto-data` — persistance MQTT
- `silence-config` — contient `configuration.json` avec l'IMEI injecté (réécrit à chaque démarrage)
- `nodered-data` — contient les flows Node-RED, les modules npm, et la config Node-RED runtime (flows.json réécrit uniquement au premier démarrage)

## Configuration

Le seul paramètre à fournir est l'**IMEI** du scooter.

Via `.env` (développement local) :
```
cp .env.example .env
# éditer .env et remplacer TON_IMEI par l'IMEI réel
```

Via Portainer (production) : ajouter `IMEI=<valeur>` dans les variables d'environnement de la stack.

## Commandes Docker

```bash
# Démarrer la stack
docker compose up -d

# Voir les logs de l'init (vérifier que les fichiers sont bien téléchargés)
docker compose logs init

# Voir les logs du serveur Silence
docker compose logs -f silence-server

# Forcer la réinitialisation des flows Node-RED (supprime les personnalisations)
docker compose down -v && docker compose up -d

# Redémarrer uniquement Node-RED (sans recréer les volumes)
docker compose restart nodered
```

## Mécanique du service `init`

Le service `init` (image `alpine`) télécharge les fichiers depuis les raw URLs du repo GitHub public avec `wget`, puis substitue le placeholder `TON_IMEI` par la valeur de `$IMEI` via `sed`.

- `mosquitto.conf` → toujours re-téléchargé
- `configuration.json` → toujours re-téléchargé et regénéré (IMEI injecté)
- `package.json` → toujours re-téléchargé
- `flows.json` → téléchargé **uniquement si absent** (préserve les personnalisations Node-RED)

Dans le YAML docker-compose, `$$VAR` est nécessaire dans les blocs `command`/`entrypoint` pour qu'un `$` littéral parvienne au shell du conteneur (Compose interprète `$$` → `$`).

## Modifier les flows Node-RED

Deux approches :
1. **Via l'UI Node-RED** (`http://<host>:1880`) — les modifications sont sauvegardées dans le volume `nodered-data`. Elles survivent aux redémarrages normaux.
2. **Via `nodered/flows.template.json`** — modifier ce fichier dans le repo, puis forcer la réinitialisation du volume `nodered-data` (`docker compose down -v`).

## Topics MQTT

Format : `home/silence-server/<IMEI>/status` (télémétrie) et `home/silence-server/<IMEI>/command/<CMD>` (commandes).

Commandes disponibles : `TURN_ON_SCOOTER`, `TURN_OFF_SCOOTER`, `OPEN_SEAT`, `FLASH`, `BEEP_FLASH`.

Le topic de souscription Node-RED utilise le wildcard `+` : `home/silence-server/+/status`.
