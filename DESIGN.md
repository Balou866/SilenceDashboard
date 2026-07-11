---
name: Silence Dashboard
description: Cockpit MQTT local pour scooter Silence S01 — télémétrie temps réel, commandes et historique de trajets
colors:
  teal-electrique: "#00D4AA"
  nuit-teal: "#0D1F33"
  bleu-nuit: "#1A2150"
  violet-nuit: "#3A1F5C"
  magenta-nuit: "#561F50"
  bleu-route: "#2196F3"
  lavande-charge: "#B39DDB"
  vert-ok: "#4CAF50"
  jaune-alerte: "#FF9800"
  rouge-critique: "#F44336"
  violet-mesure: "#7C4DFF"
  encre: "#FFFFFF"
  encre-muette: "#FFFFFFA8"
  encre-eteinte: "#FFFFFF52"
  verre: "#FFFFFF17"
  trait-verre: "#FFFFFF29"
typography:
  display:
    fontFamily: "system-ui, -apple-system, sans-serif"
    fontSize: "2.1em"
    fontWeight: 700
    lineHeight: 1
  headline:
    fontFamily: "system-ui, -apple-system, sans-serif"
    fontSize: "1.9em"
    fontWeight: 700
  title:
    fontFamily: "system-ui, -apple-system, sans-serif"
    fontSize: "0.68em"
    fontWeight: 400
    letterSpacing: "1.5px"
  body:
    fontFamily: "system-ui, -apple-system, sans-serif"
    fontSize: "0.82em"
    fontWeight: 400
  label:
    fontFamily: "system-ui, -apple-system, sans-serif"
    fontSize: "0.62em"
    fontWeight: 400
    letterSpacing: "0.7px"
rounded:
  cell: "6px"
  tile: "10px"
  control: "12px"
  card: "14px"
  pill: "20px"
spacing:
  xs: "6px"
  sm: "8px"
  md: "12px"
  lg: "14px"
components:
  card:
    backgroundColor: "{colors.verre}"
    rounded: "{rounded.card}"
    padding: "14px"
  tile-metric:
    backgroundColor: "{colors.verre}"
    rounded: "{rounded.tile}"
    padding: "10px"
  button-on:
    backgroundColor: "{colors.vert-ok}"
    textColor: "{colors.encre}"
    rounded: "{rounded.tile}"
    padding: "11px"
  button-off:
    backgroundColor: "{colors.rouge-critique}"
    textColor: "{colors.encre}"
    rounded: "{rounded.tile}"
    padding: "11px"
  button-command:
    backgroundColor: "{colors.verre}"
    textColor: "{colors.encre-muette}"
    rounded: "{rounded.control}"
    padding: "10px 6px"
  pill-status:
    backgroundColor: "{colors.verre}"
    textColor: "{colors.encre}"
    rounded: "{rounded.pill}"
    padding: "4px 16px"
---

# Design System: Silence Dashboard

## 1. Overview

**Creative North Star : « Le garage personnel »**

L'atelier du passionné, la nuit : un fond de nuit teal (dégradé teal → bleu → violet → magenta, halos radiaux teal et magenta), et posés dessus, des instruments en verre où chaque chiffre a sa place. L'interface est dense mais calme — beaucoup d'informations, zéro bruit. Les valeurs de télémétrie sont les vedettes (grosses, en gras, en teal électrique) ; tout le reste (étiquettes, bordures, titres de cartes) s'efface en majuscules discrètes et en blanc atténué. Le système rejette explicitement l'app constructeur (simpliste, qui cache la télémétrie) et l'admin SaaS froid (gris/blanc corporate sans personnalité).

Un seul thème de fond (teal) — les anciens presets aurora/indigo ont été retirés. Le mode d'affichage est double, commuté depuis l'en-tête et persistant (`localStorage.mode`) : **sobre** (défaut : batterie, autonomie, statut, trajets, position) et **technique** (le cockpit complet : moteur, BMS, cellules, coûts, diagnostics). Le technique est un sur-ensemble du sobre (classe `tech` masquée), jamais un autre design.

**Key Characteristics:**
- Fond dégradé aurore fixe, cartes en verre flouté par-dessus (une seule couche)
- Chiffres télémétrie en vedette : gras, tabular-nums, teal électrique
- Étiquettes en capitales espacées, blanc atténué — jamais en concurrence avec les valeurs
- Sémantique d'état continue : la couleur SOC glisse du rouge au vert, jamais par paliers
- Données absentes ou périmées toujours signalées (`--`, tuiles atténuées, dot horodaté)

## 2. Colors

Une nuit d'aurore saturée portée par le fond, une seule voix accentuée : le teal électrique.

### Primary
- **Teal électrique** (#00D4AA) : l'énergie électrique du scooter, néon doux sur fond nuit. Réservé aux valeurs de télémétrie vivantes, à l'état actif (dot de page, sync en cours, focus) et au tracé GPS. Jamais décoratif.

### Secondary
- **Sémantique d'état** — Vert OK (#4CAF50), Jaune alerte (#FF9800), Rouge critique (#F44336) : température, tension cellules, SOC, alarmes. Le violet mesure (#7C4DFF) porte la tension dans les sparklines.
- **Teintes de pastille de statut** — Bleu route (#2196F3, « En route ») et Lavande charge (#B39DDB, « En charge ») complètent la sémantique ; la veille utilise un gris-bleu discret (rgba(124,140,180,.22)).
- La couleur SOC est **continue** (HSL rouge→vert calculé par `getSocColor`), appliquée via `--soc-color`.

### Neutral
- **Encre** (#FFFFFF) : valeurs et texte principal.
- **Encre muette** (#FFFFFFA8, `--muted`) : étiquettes, titres de cartes, texte secondaire. Plancher de contraste : ne jamais descendre sous cette opacité pour du texte porteur d'information.
- **Encre éteinte** (#FFFFFF52, `--muted2`) : états inactifs uniquement (badges d'alarme au repos, dots de page).
- **Verre** (#FFFFFF17, `--card`) et **Trait de verre** (#FFFFFF29, `--border`) : surface et bordure de toutes les cartes.
- **Nuit teal** (#0D1F33) → **Bleu nuit** (#1A2150) → **Violet nuit** (#3A1F5C) → **Magenta nuit** (#561F50) : les jalons du dégradé de fond, réchauffé par deux halos radiaux (magenta rgba(190,40,130,.32) et teal rgba(0,180,170,.18)).

### Named Rules
**La règle du teal parlant.** Le teal signale une donnée vivante ou une action en cours. S'il apparaît sur un élément purement décoratif, c'est une faute.

**La règle du gris honnête.** Une donnée absente s'affiche `--`, une carte sans données live est atténuée (`.dimmed`), une donnée en cache est horodatée 📦. On n'invente jamais une valeur.

## 3. Typography

**Display Font:** system-ui (pile native, aucune webfont)
**Body Font:** system-ui (même famille, graisses 400/600/700)

**Character:** une seule famille système, silencieuse et rapide à charger — la hiérarchie vient du poids, de la taille et de la casse, pas d'un changement de fonte. `font-variant-numeric: tabular-nums` sur tout le body : les valeurs qui se rafraîchissent en MQTT ne sautent pas.

### Hierarchy
- **Display** (700, 2.1em, lh 1) : le chiffre unique d'une carte (distance du dernier trajet).
- **Headline** (700, 1.9em) : le pourcentage central de la jauge batterie.
- **Value** (700, 0.85–1.25em, teal ou encre) : toute valeur de tuile ou de tableau.
- **Body** (400, 0.8–0.85em) : lignes libellé/valeur, tableau des trajets.
- **Title/Label** (400, 0.62–0.68em, MAJUSCULES, tracking 0.7–1.5px, encre muette) : titres de cartes et étiquettes de tuiles.

### Named Rules
**La règle des chiffres vedettes.** Dans chaque tuile, la valeur est l'élément le plus gros et le plus contrasté ; l'étiquette ne dépasse jamais 0.68em. Si l'œil lit l'étiquette avant la valeur, la hiérarchie est cassée.

## 4. Elevation

Le verre EST la hiérarchie : une couche unique de cartes translucides floutées (`rgba(255,255,255,.09)` + `backdrop-filter: blur(10px)` + bordure #FFFFFF29) posée sur le dégradé de fond fixe. La profondeur vient du flou et de l'ombre ambiante, pas d'un empilement.

### Shadow Vocabulary
- **Ombre ambiante** (`box-shadow: 0 8px 30px rgba(0,0,0,.28)`, `--shadow`) : toutes les cartes, valeur unique.
- **Header flottant** (`0 1px 0 rgba(255,255,255,.06), 0 4px 20px rgba(0,0,0,.35)`) : uniquement la barre sticky.

### Named Rules
**La règle du verre unique.** Une seule couche de verre sur le fond. Jamais de carte dans une carte : à l'intérieur d'une carte, les sous-blocs utilisent `rgba(255,255,255,.04)` sans flou ni ombre (tuiles internes, cellules 14S).

## 5. Components

Denses et calmes : beaucoup d'infos, zéro bruit — bordures fines, étiquettes discrètes, chiffres en vedette.

### Commutateur de mode (signature)
- Segmented control en en-tête (Sobre | Technique), pill 20px, segment actif en teal translucide 18%. Persistant (`localStorage.mode`), raccourci clavier M. Le sobre masque la classe `tech` ; la grille desktop se resserre en 3 colonnes.

### Buttons
- **Shape:** coins nets arrondis (10px boutons pleins, 12px boutons de commande)
- **Allumer / Éteindre:** aplats francs vert #4CAF50 / rouge #F44336, texte blanc 700 ; double confirmation obligatoire (état `pending` = bordure blanche pointillée, libellé « Confirmer ? », timeout 2.5s)
- **Commandes (Sync/Selle/Flash/Beep):** vrais `<button>` verre + icône SVG trait 2 + libellé majuscules ; hover éclaircit le verre, sync en cours = icône en rotation teal. **Toute commande répond par un toast** (`#toast`, bas d'écran, role=status) : envoyée, hors-ligne ou échec
- **Hover / Focus:** hover `brightness(1.1)` sur aplats ; `:focus-visible` = anneau teal 2px offset 2px, partout

### Cards / Containers
- **Corner Style:** 14px
- **Background:** verre #FFFFFF17 + blur 10px
- **Shadow Strategy:** ombre ambiante unique (cf. Elevation)
- **Border:** 1px trait de verre #FFFFFF29
- **Internal Padding:** 14px ; grilles internes gap 6–12px

### Tuiles métriques (st-cell / s3cell / c4cell)
- Verre + bordure, radius 10px, valeur 700 teal ou encre au-dessus d'une étiquette majuscule muette. Version intra-carte : fond `rgba(255,255,255,.04)` sans flou.

### Tableau des trajets
- Table plate 7 colonnes, en-tête sticky majuscule muet, valeurs alignées à droite en teal 600 ; lignes cliquables ET focusables (Tab + Entrée = tracé GPS), hover/focus = voile blanc 6%.

### Pastille de statut (signature)
- Pill 20px traduisant l'état scooter : chaque état a sa teinte (gris éteint, orange démarrage, vert prêt, bleu en route, violet charge, rouge sans batterie) en fond translucide 20% + texte et bordure de la même teinte.

### Jauge SOC (signature)
- Arc SVG 270° monochrome dont la couleur suit `--soc-color` (continu rouge→vert), pourcentage central en headline. Le favicon reproduit la même jauge en 32px.

### Sparklines (signature)
- SVG maison 100×32, trait 1.5 non-scaling, aire dégradée sous la courbe ; légende d'échelle `↕ min–max` + `↔ ~10 min`. Couleurs : rouge moteur, orange onduleur, teal batterie, violet tension.

## 6. Do's and Don'ts

### Do:
- **Do** réserver le teal #00D4AA aux données vivantes et aux états actifs (la règle du teal parlant).
- **Do** signaler l'absence ou la péremption des données : `--`, `.dimmed`, horodatage 📦 (la règle du gris honnête).
- **Do** exiger la double confirmation sur toute commande qui change l'état du scooter.
- **Do** garder `tabular-nums`, les cibles tactiles ≥ 28px, `:focus-visible` teal et le bloc `prefers-reduced-motion`.
- **Do** faire de toute nouvelle donnée une tuile dense et calme : valeur 700 en vedette, étiquette majuscule muette en dessous.

### Don't:
- **Don't** ressembler à « l'app constructeur » : ne jamais cacher une donnée que le scooter fournit ; on hiérarchise, on ne supprime pas.
- **Don't** ressembler à « l'admin SaaS froid » : pas de fond blanc/gris corporate, pas de tuiles génériques sans hiérarchie.
- **Don't** empiler du verre sur du verre (la règle du verre unique) — les sous-blocs intra-carte sont mats à 4% blanc.
- **Don't** utiliser de bordure latérale colorée > 1px, de texte en dégradé (`background-clip: text`), ni de texte porteur d'info sous #FFFFFFA8.
- **Don't** coder un état uniquement par la couleur : toujours doubler d'un libellé, d'une icône ou d'une valeur.
- **Don't** ajouter de webfont ni d'animation d'entrée orchestrée : famille système, motion = feedback d'état uniquement (150–400 ms).
