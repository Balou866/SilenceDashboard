---
target: dashboard
total_score: 25
p0_count: 0
p1_count: 3
timestamp: 2026-07-11T13-13-54Z
slug: dashboard-index-template-html
---
Method: dual-agent (A: critique-A · B: critique-B) — critique sur code source uniquement (pas d'outil navigateur exposé, visualisation navigateur sautée)

# Critique — dashboard/index.template.html

## Design Health Score

| # | Heuristique | Score | Problème clé |
|---|-----------|-------|-----------|
| 1 | Visibilité de l'état système | 3 | Fraîcheur excellente (dot live/📦/dimmed) mais commandes Flash/Beep/Selle fire-and-forget, zéro retour |
| 2 | Correspondance monde réel | 3 | Jargon brut : « SOC Astra », « Flags BMS 0x0000 », « NTC 1/2/3 », « Bus V » |
| 3 | Contrôle et liberté | 3 | Sync verrouillé 12 s sans annulation ; tarif appliqué à chaque frappe (`oninput`) |
| 4 | Cohérence et standards | 3 | Arbres desktop/`m-` déjà divergents (mobile sans SOC Astra, Courant BMS, driveReady) |
| 5 | Prévention d'erreurs | 3 | Double-confirm ON/OFF bien ; publish MQTT hors-ligne perdu en silence |
| 6 | Reconnaissance vs rappel | 3 | Pages mobiles non titrées : il faut mémoriser qui contient quoi |
| 7 | Flexibilité et efficience | 2 | Aucun raccourci clavier ; seul le tableau de trajets est focusable |
| 8 | Esthétique et minimalisme | 2 | Desktop déverse tout, ~15 cartes de même poids, pas de point focal |
| 9 | Récupération d'erreurs | 2 | `catch(e){}` avale tout ; aucun message d'erreur, aucune guidance |
| 10 | Aide et documentation | 1 | Aucun tooltip sur le jargon ; empty states nus |
| **Total** | | **25/40** | **Acceptable — fondations solides, trous en flexibilité/récupération/aide** |

## Anti-Patterns Verdict

**Évaluation LLM** : pas du slop — vraie voix (« le garage personnel »), système d'honnêteté des données unique (dot live, 📦, `.dimmed`, `predata`). Trois tells à surveiller : glassmorphism appliqué **partout** par défaut (assumé par le North Star mais jamais questionné), halos radiaux décoratifs du fond, et **mélange emoji (⚡🏎️📍🔋) / SVG trait 2** — deux langages d'icônes qui trahissent l'assemblage.

**Scan déterministe** : 38 findings — 1 `em-dash-overuse` **faux positif** (somme fichier-entier de tirets isolés dans commentaires/microcopie, aucune prose >2 tirets) ; 2 `design-system-radius` **faux positifs** (scrollbar 3px, puce légende 2px) ; 35 `design-system-color` = **drift de documentation, pas de code** : DESIGN.md n'énumère pas les palettes des thèmes indigo/teal, les stops intermédiaires aurora, les teintes des pastilles de statut (`#2196f3` en-route ≠ `--blue:#1565c0` défini), ni `#4a9eff` (fallback d'un `--accent` jamais défini — règle CSS morte). Résolution : compléter DESIGN.md, pas toucher au code (sauf la règle morte).

**Visualisation navigateur** : non disponible (pas d'outil navigateur) — aucun overlay affiché.

## Overall Impression

Un cockpit personnel avec une âme et une rigueur rares sur la fraîcheur des données, mais qui n'a pas encore tenu sa propre promesse produit : le mode « sobre » n'existe pas, tout est technique tout le temps. Le plus gros levier : donner un feedback aux commandes et hiérarchiser le coup d'œil batterie.

## What's Working

1. **Le système d'honnêteté de fraîcheur** — dot pulsant live / « il y a Xs » / badge 📦 horodaté / cartes `.dimmed` / classe `predata`. Rigoureux, rare, directement le principe 5.
2. **Sémantique SOC continue** (`getSocColor` rouge→vert) cohérente jauge + favicon + %, toujours doublée du chiffre — jamais d'info par couleur seule sur ce chemin.
3. **A11y au-delà du minimum** : double-confirm à timeout, lignes trajets focusables (Entrée/Espace), `:focus-visible` teal global, `prefers-reduced-motion`, zones tactiles élargies.

## Priority Issues

**[P1] Les commandes n'ont aucun feedback** — `cmd()` publie et n'affiche rien ; ON/OFF confirme avant, rien après ; hors-ligne = perte silencieuse. Contredit le principe 4 « les commandes inspirent confiance ». Fix : toast « envoyé », erreur si `client.connected===false`, idéalement ack via changement d'état. → `/impeccable harden`

**[P1] Le mode « sobre » n'existe pas** — PRODUCT.md le pose comme cible (principe 3) ; desktop 100% technique, mobile pagine la même densité. Fix : commutateur Sobre/Technique persistant (comme le thème), sobre = batterie/autonomie/statut/dernier trajet, sobre par défaut. → `/impeccable shape` puis craft

**[P1] Aide et jargon (1/10)** — « SOC Astra », « Flags BMS 0x0000 », « Déséq. mV », « NTC », « Bus V » sans explication. Fix : tooltips/`<abbr>` ou « ? » par carte diagnostic. → `/impeccable clarify`

**[P2] Desktop sans point focal + zéro raccourci clavier** — 15 cartes de même poids ; aucun accélérateur. Fix : héro batterie+autonomie, raccourcis (S=sync…). → `/impeccable layout`

**[P2] IA mobile à contre-emploi** — page d'atterrissage = contrôles ; la jauge batterie (le job « 5 s au réveil ») est un swipe plus loin ; le badge 📦 aussi. Fix : batterie en page 0 ou héro compact en tête. → `/impeccable layout`

## Persona Red Flags

**Alex (power user)** : aucun raccourci clavier ; `oninput` du tarif écrit localStorage à chaque frappe ; tout est cul-de-sac clavier hors tableau trajets.

**Sam (accessibilité)** : `--muted2` (.32) très sous 4.5:1 ; contraste imprévisible du verre sur dégradé variable ; alarmes = changement de couleur seul, sans `aria-live` ni changement de libellé → lecteur d'écran muet sur TOUTE la télémétrie et sur le « Confirmer ? » du bouton le plus risqué ; pas de déplacement de focus au changement de page mobile.

**Propriétaire au réveil (persona projet)** : atterrit sur les contrôles, pas la batterie ; le SOC n'est qu'une petite tuile en page 0 ; l'indicateur « donnée en cache » est page 1.

## Minor Observations

- `--accent` jamais défini → `#4a9eff` hors palette dans une règle CSS morte (le bouton ciblé n'existe plus). À supprimer.
- En-tête sticky table `rgba(17,19,28,.96)` : surface étrangère aux tokens.
- `speed` affiche « 0 » sans donnée (entorse à la règle du gris honnête).
- Coûts Semaine/Mois/Année = amorti vie-entière, pas dépense périodique — libellé qui surpromet.
- `.s0` couvre Éteint ET Veille : la pastille Veille a le style « éteint ».
- Filtre invert/hue-rotate des tuiles OSM : labels de rue à la limite du lisible.
- « Aucun trajet enregistré » n'enseigne rien (empty state nu).
- Bon soin iOS (safe-area, viewport-fit).

## Questions to Consider

1. Et si « sobre » était le défaut et « technique » l'opt-in — les ~80% de sessions coup-d'œil n'en seraient-elles pas radicalement simplifiées ?
2. Si l'utilisateur ne peut pas savoir si « Ouvrir la selle » a atteint le scooter, le dashboard inspire-t-il confiance ou espère-t-il seulement ?
3. Deux arbres DOM parallèles qui ont déjà divergé : la densité justifie-t-elle la duplication, ou un seul arbre responsive supprimerait-il cette classe de bugs ?
