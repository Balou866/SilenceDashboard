# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Règles de développement

- Laisser toujours l'utilisateur réaliser les commits et les push
- Mettre à jour CLAUDE.md quand c'est nécessaire — il doit toujours refléter le code actuel
- L'installation se fait uniquement via Portainer (modification du docker-compose via stack)
- **Toujours synchroniser le bloc `docker-compose` dans README.md** quand `docker-compose.yml` est modifié — le README contient une copie complète du compose pour Portainer

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
| `mqtt-retain/relay.py` | Relais MQTT (service `mqtt-retain`) : republie chaque message en `retain` (snapshot au chargement du dashboard) **et** détecte/persiste les trajets dans `trips.json` (volume `trip-data`, monté `:ro` sur `…/html/data` côté dashboard). Machine à états : **un trajet = une session moteur allumé** — démarre quand `status` quitte `OFF_STATUSES` (`{0,1,5}`, cf. `messageParser.off_statuses`), finit quand il y revient. Ce choix élimine les faux positifs (feu rouge / standby : moteur tournant mais `status≠4`, le trajet ne se coupe plus). Enregistre date, durée, distance (**somme haversine du tracé GPS brut** via `_path_distance` — l'odomètre scooter est en km entiers, donc Δodo s'arrondit toujours au km ; fallback Δodo si pas de fix GPS / tracé < 2 points), batterie (Δsoc — **`None` si SOC de départ ou d'arrivée inconnu**, `_get_soc` retourne `None` et jamais un faux 0), vmax, vavg (**= dist/durée NON arrondie `dur_f`** — sinon un trajet de 40 s arrondi à 1 min divise la moyenne par ~2), **températures moyennes du trajet** (`tamb`/`tmot`/`tinv` = moyennes Ambiance/Moteur/Onduleur via accumulateurs `temps` dans le trajet actif, `TEMP_FIELDS`, `None` si jamais reçu p.ex. pas de poll CAN), **efficacité** (`eff` en Wh/km = Δsoc% × `BATTERY_WH` / dist ; `BATTERY_WH` défaut 5600 = pack Silence S01, override via env ; 0 si `bat` `None`) **et le tracé GPS** (`path` = liste `[lat,lon]` échantillonnée toutes les 3 s via `latitude`/`longitude`, proto Z ; **simplifié Douglas-Peucker à l'enregistrement**, `SIMPLIFY_EPS` ≈ 5 m, la distance est calculée AVANT simplification ; **seuls les `PATHFUL_TRIPS`=20 trajets les plus récents gardent leur `path`**, les plus anciens sont vidés pour garder `trips.json` léger — re-téléchargé entier à chaque chargement). **Filtres de cohérence** avant enregistrement (inspirés de noiwid/silence-scooter-homeassistant) : rejette `dist<0.1`, `avg_spd>120`, **`max_spd==0`** (jamais bougé — jitter GPS d'un scooter garé qui accumule >0.1 km en haversine), `dur<1.5min & dist>2km`, **`bat<-2`** (SoC qui monte = session de charge, pas un trajet). **Garde anti-charge** : la charge 230V réveille le scooter avec un status hors `{0,1,5}` sans que le moteur tourne → pas de démarrage de trajet si `charging` est vrai ; transitions `charging` gérées symétriquement (débranché avec status "on" → démarre le trajet, branché en plein trajet actif → le clôt). Les transitions de `status` sont loguées (`Status: X -> Y`) pour diagnostiquer le statut réel émis en charge. Même garde côté client (`trackTrip` : `&& !d.charging`). ⚠️ Tout `_track_field` doit recevoir `now_ms` en argument (ne pas s'appuyer sur une variable globale — bug historique qui faisait planter le thread et laissait `trips.json` vide) |
| `dashboard/index.template.html` | Interface HTML, placeholder `TON_IMEI` dans `var IMEI`. Connexion MQTT en `wss://` auto si la page est servie en HTTPS (reverse-proxy), sinon `ws://`. **Re-render débouncé** : les messages MQTT par champ n'appellent plus `update()` directement mais `scheduleUpdate()` (100 ms) — un burst SYNC = 1 render au lieu de dizaines ; favicon régénéré seulement quand le % entier de SOC change. Desktop : grille **4 colonnes** (`.col-left` contrôles / `.col-mid` batterie-moteur-coûts-trajets / `.col-diag` diagnostics **toujours affichés** / `.col-right` carte-trajet). Mobile : **4 pages** swipe (`mp-0`..`mp-3`, la 4e = diagnostics), dots (vrais `<button>` + `aria-label`) en `position:fixed` bas d'écran ; le swipe ignore les gestes commencés sur une carte Leaflet et exige `|dx|>|dy|` (pas de changement de page en scrollant/pannant). Diagnostics mobiles via mirroring `m-` (`txt2`, `setTemp`, `renderCellGrid`). Sélecteur de thème (aurora/indigo/teal) persistant via `localStorage` ; swatches avec zone tactile élargie (`::after` inset -8px). Boutons de commande = `<button>` accessibles (`aria-label`, focus clavier). État initial : `<body class="predata">` atténue toutes les `.card` tant qu'aucune donnée (retiré au 1er `update()` ou au 1er `renderTripsTable` avec trajets). `prefers-reduced-motion` respecté (pulse/spin/transitions coupés). Sparklines SVG maison (buffer client échantillonné 10s, fenêtre ~10 min = `HIST_MAX` 60 × 10s) pour temp/élec dans `.col-diag` (desktop uniquement). Chaque sparkline porte une légende d'échelle `.spark-cap` : `↕ min–max + unité` (°C / V / A, calculé par `renderSparks`/`renderArea`) et `↔ ~10 min` pour l'axe temps. **Position actuelle** : carte **Leaflet live** (`showPosMap`/`_posMarkers`, `#pos-map`/`#m-pos-map`) — marqueur déplacé à chaque fix GPS, recentrage seulement si le marqueur sort de la vue (l'ancienne iframe OSM restait figée sur le 1er fix). **Toutes les tuiles OSM sont assombries** via filtre CSS `.leaflet-tile` (invert + hue-rotate) pour coller au thème sombre. **Dernier trajet** : tuile unique `.trip-card` (gros chiffre `.trip-card-head` + grille détail **2 colonnes** `#lt-data` : durée/dist/bat/vavg/vmax/eff) — mobile identique (`#m-lt-data`, page 2), peuplé via `txt2` dans `renderLastTrip` ; le « il y a … » (`lt-ago`) est rafraîchi par le même interval que `updateLastUpdate` (`_lastTripTs`). **Trajet en cours** : card desktop `#trip-live-card` (col-right) + **card mobile séparée `#m-trip-live-card` en enfant direct de `<body>`** (`position:fixed` au-dessus des dots) — ⚠️ ne pas la remettre dans `<main>` : `main` est `display:none` sur mobile, un `fixed` à l'intérieur serait invisible. Les valeurs live lisent `lastData.odo`/`lastData.SOCbatteria` dans le callback du timer (pas les arguments figés dans la closure au démarrage du trajet). **Tracé de trajet** : clic sur une ligne du tableau « Trajets récents » → polyline **Leaflet sur fond OSM** (`renderRoute`/`_ensureMap`, `fitBounds` auto, marqueurs départ/arrivée) dans la carte « Tracé du trajet » (col-right desktop / page 2 mobile, message « Pas de points GPS » si `path` vide — cas des trajets anciens dont le relay a purgé le tracé) ; la ligne cliquée reçoit la classe `.sel` (fond teal). Tableau « Trajets récents » : **table plate 7 colonnes** Date / Durée / Dist. / Vmax/Moy (km/h) / Bat. (conso %, `--` si `bat` null) / Effic. (Wh/km) / T° A/O/M (°C, `--` si absent) ; colonne T° masquée sous 400px ; en-têtes alignés à droite (sauf 1re colonne). Tous les trajets rendus dans `.trips-scroll` (hauteur ~5 lignes, en-tête `sticky`). Le tableau est refetché à chaque reconnexion MQTT **et** par un poll 60 s (`fetchTrips`). Durées formatées `fmtDur` (`75min` → `1h15`). Heures formatées **côté client depuis `t.ts`** (`formatTripDate`, locale navigateur) |
| `dashboard/rambo-silence.png` | Visuel du scooter (PNG détouré rembg/isnet, fond transparent) affiché dans `.scooter-area` (fallback emoji 🛵 si absent) |
| `dashboard/manifest.json` | Manifest PWA (nom, icônes, `display:standalone`, `theme_color`). Installable sur écran d'accueil mobile |
| `dashboard/sw.js` | Service worker PWA — stratégie réseau d'abord, cache en repli (shell offline ; précache `leaflet.css`/`leaflet.js`). `/data/*` (trips.json) et tuiles `*.tile.openstreetmap.org` jamais mis en cache. Repli `index.html` **réservé aux navigations** (`req.mode === 'navigate'`) — un asset manquant offline reçoit `Response.error()`, pas du HTML |
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
