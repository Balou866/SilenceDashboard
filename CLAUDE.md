# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Règles de développement

- Laisser toujours l'utilisateur réaliser les commits et les push
- Mettre à jour CLAUDE.md quand c'est nécessaire — il doit toujours refléter le code actuel
- L'installation se fait uniquement via Portainer (modification du docker-compose via stack)
- **Toujours synchroniser le bloc `docker-compose` dans README.md** quand `docker-compose.yml` est modifié — le README contient une copie complète du compose pour Portainer

## Design Context

- `PRODUCT.md` (racine) — register `product`, utilisateurs, positionnement, principes de design. À lire avant tout travail UI.
- `DESIGN.md` (racine) — système visuel : tokens (couleurs/typo/radius), règles nommées (verre unique, teal parlant, gris honnête, chiffres vedettes), do's & don'ts. Sidecar machine : `.impeccable/design.json`.
- Toute passe design passe par le skill `/impeccable` (installé globalement), qui lit ces deux fichiers.

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
- `dashboard-data` — `index.html` généré depuis le template + assets statiques `mqtt.min.js`, `rambo-silence.png`, **`leaflet.css`/`leaflet.js`** (téléchargés par init depuis unpkg, auto-hébergés pour le fond de carte OSM du tracé) et fichiers PWA (`manifest.json`, `sw.js`, `icon-192.png`, `icon-512.png`, `apple-touch-icon.png`) (tous téléchargés par init depuis le repo). **L'init fait aussi `mkdir -p /dashboard-data/data`** : le service `dashboard` monte `dashboard-data` en `:ro` sur `/usr/share/nginx/html` PUIS `trip-data` en `:ro` sur `…/html/data` (montage imbriqué). Sans le dossier `data/` pré-créé dans le volume, Docker tente un `mkdir` sur un FS read-only → conteneur bloqué en *Created* → **deploy Portainer KO (500 nu)**. Ne pas retirer ce `mkdir`.

## Fichiers clés

| Fichier | Rôle |
|---|---|
| `docker-compose.yml` | Stack complète — seul fichier à coller dans Portainer |
| `mosquitto/mosquitto.conf` | Listeners MQTT (1883) et WebSocket (9001) |
| `silence/configuration.template.json` | Config silence-server, placeholder `TON_IMEI` dans `IMEI_List` (tableau) |
| `silence/Dockerfile` | Build silence-server depuis l'upstream + override `messageParser.py`, `commands_definition.json`, `CommandService.py` |
| `silence/helpers/messageParser.py` | Parser des trames scooter (protocole Z, `$RCAN`, `$STMS`) |
| `silence/helpers/commands_definition.json` | Override des commandes TCP (ajoute `SYNC` → `$STMS`) |
| `silence/services/CommandService.py` | Override : corrige bug upstream `NameError: name 'imei'` (→ `self.IMEI`) qui crashait le thread après chaque commande |
| `mqtt-retain/relay.py` | Relais MQTT (service `mqtt-retain`) : republie chaque message en `retain` (snapshot au chargement du dashboard) **et** détecte/persiste les trajets dans `trips.json` (volume `trip-data`, monté `:ro` sur `…/html/data` côté dashboard). Machine à états : **un trajet = une session moteur allumé** — démarre quand `status` quitte `OFF_STATUSES` (`{0,1,5}`, cf. `messageParser.off_statuses`), finit quand il y revient. Ce choix élimine les faux positifs (feu rouge / standby : moteur tournant mais `status≠4`, le trajet ne se coupe plus). Enregistre date, durée, distance (**somme haversine du tracé GPS** via `_path_distance` — l'odomètre scooter est en km entiers, donc Δodo s'arrondit toujours au km ; fallback Δodo si pas de fix GPS / tracé < 2 points), batterie (Δsoc), vmax, vavg (**= dist/durée**), **températures moyennes du trajet** (`tamb`/`tmot`/`tinv` = moyennes Ambiance/Moteur/Onduleur via accumulateurs `temps` dans le trajet actif, `TEMP_FIELDS`, `None` si jamais reçu p.ex. pas de poll CAN), **efficacité** (`eff` en Wh/km = Δsoc% × `BATTERY_WH` / dist ; `BATTERY_WH` défaut 5600 = pack Silence S01, override via env) **et le tracé GPS** (`path` = liste `[lat,lon]` échantillonnée toutes les 3 s via `latitude`/`longitude`, proto Z). **Filtres de cohérence** avant enregistrement (inspirés de noiwid/silence-scooter-homeassistant) : rejette `dist<0.1`, `avg_spd>120`, `max_spd==0 & avg_spd>10`, `dur<1.5min & dist>2km` — élimine les trajets aberrants (sauts GPS, glitch odo). ⚠️ Tout `_track_field` doit recevoir `now_ms` en argument (ne pas s'appuyer sur une variable globale — bug historique qui faisait planter le thread et laissait `trips.json` vide) |
| `dashboard/index.template.html` | Interface HTML, placeholder `TON_IMEI` dans `var IMEI`. Desktop : grille **4 colonnes** (`.col-left` contrôles / `.col-mid` batterie-moteur-coûts-trajets / `.col-diag` diagnostics **toujours affichés** / `.col-right` carte-trajet). Mobile : **4 pages** swipe (`mp-0`..`mp-3`, la 4e = diagnostics), dots en `position:fixed` bas d'écran. Diagnostics mobiles via mirroring `m-` (`txt2`, `setTemp`, `renderCellGrid`). Sélecteur de thème (aurora/indigo/teal) persistant via `localStorage`. Sparklines SVG maison (buffer client échantillonné 10s, fenêtre ~10 min = `HIST_MAX` 60 × 10s) pour temp/élec dans `.col-diag` (desktop uniquement). Chaque sparkline porte une légende d'échelle `.spark-cap` : `↕ min–max + unité` (°C / V / A, calculé par `renderSparks`/`renderArea`) et `↔ ~10 min` pour l'axe temps (pas d'axes SVG, juste min/max + fenêtre). **Dernier trajet** : tuile unique `.trip-card` (gros chiffre `.trip-card-head` + grille détail **2 colonnes** `#lt-data` : durée/dist/bat/vavg/vmax/eff) — header et détail fusionnés pour gagner en hauteur 1080p. Mobile identique (`#m-lt-data`, page 2), peuplé via `txt2` (mirroring `m-`) dans `renderLastTrip`. **Tracé de trajet** : clic sur une ligne du tableau « Trajets récents » → polyline **Leaflet sur fond de tuiles OpenStreetMap** (`renderRoute`/`_ensureMap`, conteneur `<div id="route-map">`, `path` GPS `[lat,lon]` passé directement, `fitBounds` auto, marqueurs départ/arrivée) dans la carte « Tracé du trajet » (col-right desktop / page 2 mobile). Tableau « Trajets récents » : **table plate 7 colonnes** Date / Durée / Dist. / Vmax/Moy (km/h) / Bat. (conso %) / Effic. (Wh/km) / T° A/O/M (°C = Ambiance/Onduleur/Moteur moyennes, `--` si absent) ; en-têtes alignés à droite (comme les valeurs, sauf 1re colonne). Tous les trajets sont rendus dans un conteneur `.trips-scroll` (hauteur bornée ~5 lignes, `overflow-y:auto`, scrollbar fine, **en-tête `sticky`**) — l'historique antérieur se consulte au scroll, pas de bouton. Clic sur une ligne = **trace le GPS uniquement** (pas de ligne dépliée). Les heures du tableau et du dernier trajet sont formatées **côté client depuis `t.ts`** (`formatTripDate`, locale navigateur) — pas l'ancien champ `date` préformaté UTC côté relay |
| `dashboard/rambo-silence.png` | Visuel du scooter (PNG détouré rembg/isnet, fond transparent) affiché dans `.scooter-area` (fallback emoji 🛵 si absent) |
| `dashboard/manifest.json` | Manifest PWA (nom, icônes, `display:standalone`, `theme_color`). Installable sur écran d'accueil mobile |
| `dashboard/sw.js` | Service worker PWA — stratégie réseau d'abord, cache en repli (shell offline ; précache `leaflet.css`/`leaflet.js`). `/data/*` (trips.json) et tuiles `*.tile.openstreetmap.org` jamais mis en cache |
| `dashboard/icon.svg` | Source de l'icône (dégradé aurora + éclair). Rasterisée en `icon-192.png` / `icon-512.png` / `apple-touch-icon.png` (180px, fond opaque pour iOS) via PIL |

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
- Commandes disponibles : `TURN_ON_SCOOTER`, `TURN_OFF_SCOOTER`, `OPEN_SEAT`, `FLASH`, `BEEP_FLASH`, `SYNC`
- `SYNC` envoie `$STMS\r\n` au scooter → snapshot complet immédiat. Réponse `$STMS,...`
  (protocole Astra) décodée par `_parse_stms()` dans `silence/helpers/messageParser.py`.
  Bouton « 🔄 Sync » dans le dashboard. Commande définie dans
  `silence/helpers/commands_definition.json` (override copié dans l'image via `silence/Dockerfile`).
