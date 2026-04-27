# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Règles de développement

- Laisser toujours l'utilisateur réaliser les commits et les push
- Mettre à jour CLAUDE.md quand c'est nécessaire — il doit toujours refléter le code actuel
- L'installation se fait uniquement via Portainer (modification du docker-compose via stack)

## Project Overview

Silence-Dashboard est une stack Docker auto-hébergée pour piloter un scooter Silence S01 / SEAT MÓ depuis un navigateur. La page HTML se connecte directement au broker MQTT via WebSocket — pas de middleware comme Node-RED.

Upstream : https://github.com/lorenzo-deluca/silence-private-server

## Architecture

```
Scooter ──TCP 38955──► silence-server ──MQTT 1883──► mosquitto ──WebSocket 9001/9002──► navigateur :8083
```

**Services :**
- `init` (alpine) — télécharge les configs depuis le repo GitHub public et injecte l'IMEI via `sed`. S'exécute une seule fois avant les autres services.
- `mosquitto` — broker MQTT, écoute sur 1883 (interne) et 9001 WebSocket (exposé sur 9002)
- `silence-server` — proxy TCP/MQTT, attend que mosquitto soit healthy
- `dashboard` (nginx:alpine) — sert `index.html` depuis le volume `dashboard-data`

**Volumes :**
- `mosquitto-config` — `mosquitto.conf` (toujours réécrit par init)
- `mosquitto-data` — persistance MQTT
- `silence-config` — `configuration.json` avec IMEI injecté (toujours réécrit par init)
- `dashboard-data` — `index.html` généré depuis le template (toujours réécrit par init)

## Fichiers clés

| Fichier | Rôle |
|---|---|
| `docker-compose.yml` | Stack complète — seul fichier à coller dans Portainer |
| `mosquitto/mosquitto.conf` | Listeners MQTT (1883) et WebSocket (9001) |
| `silence/configuration.template.json` | Config silence-server, placeholder `TON_IMEI` |
| `dashboard/index.template.html` | Interface HTML, placeholder `TON_IMEI` dans `var IMEI` |

## Configuration

Seul paramètre requis : `IMEI` (variable d'environnement dans la stack Portainer).

Le placeholder `TON_IMEI` est substitué dans `configuration.json` et `index.html` à chaque démarrage de l'init container via `sed "s/TON_IMEI/$IMEI/g"`.

Note YAML : `$$IMEI` dans les blocs `command` du docker-compose est nécessaire — Compose interprète `$$` comme un `$` littéral passé au shell du conteneur.

## Commandes utiles

```bash
# Vérifier que init a réussi
docker logs silenceserver-init-1

# Logs du serveur Silence
docker logs -f silence-server

# Forcer la régénération de tous les fichiers (ex: après changement IMEI)
# → redéployer la stack dans Portainer (init tourne à chaque déploiement)
```

## Ports exposés

| Port | Service |
|---|---|
| 8083 | Dashboard HTML (nginx) |
| 9002 | MQTT WebSocket (mosquitto) |
| 38955 | TCP scooter (silence-server) |

## Topics MQTT

- Télémétrie : `home/silence-server/<IMEI>/status` (JSON)
- Commandes : `home/silence-server/<IMEI>/command/<CMD>`
- Commandes disponibles : `TURN_ON_SCOOTER`, `TURN_OFF_SCOOTER`, `OPEN_SEAT`, `FLASH`, `BEEP_FLASH`
