# Product

## Register

product

## Platform

web

## Users

Le propriétaire du scooter, en usage personnel auto-hébergé (un seul scooter Silence S01 / SEAT MÓ). Le code est public sur GitHub : d'autres propriétaires peuvent déployer la stack chez eux, la config doit donc rester générique (seul l'IMEI est paramétré). Contexte d'usage : surtout mobile en coup d'œil rapide (PWA sur écran d'accueil), desktop pour l'analyse.

## Product Purpose

Dashboard temps réel qui pilote et surveille le scooter via MQTT, entièrement en local. Trois jobs principaux, par ordre d'importance : le coup d'œil avant départ (batterie/autonomie en 2 secondes), l'analyse post-trajet (trajets récents, efficacité Wh/km, tracé GPS), et le suivi de charge (SOC, tension, températures). Succès = l'info cherchée est visible sans interaction, et les commandes à distance répondent de façon fiable.

## Positioning

Piloter et comprendre son Silence S01 en local, sans dépendre du cloud constructeur.

## Brand Personality

Deux registres selon le profil de l'utilisateur, idéalement exposés comme deux modes d'affichage : **sobre** (calme, l'essentiel d'abord, détails au second plan) et **technique** (cockpit dense : BMS, cellules, températures, chiffres exacts). Aujourd'hui le desktop affiche tout (registre technique) et le mobile pagine ; un vrai commutateur simple/expert est la cible. Ton chaleureux et personnel (visuel du scooter, thèmes), jamais corporate.

## Anti-references

- L'app constructeur : UI grand public simpliste qui cache la télémétrie.
- L'admin SaaS froid : tableau de bord corporate gris/blanc sans personnalité.

## Design Principles

1. **L'info avant l'interaction** — l'état clé (batterie, autonomie, statut) se lit sans clic, sans scroll, même sur mobile.
2. **La télémétrie est un droit** — ne jamais cacher une donnée que le scooter fournit ; la hiérarchiser au lieu de la supprimer.
3. **Deux profils, une interface** — le mode sobre et le mode technique partagent le même vocabulaire visuel ; l'un est un sous-ensemble de l'autre, pas un redesign.
4. **Les commandes inspirent confiance** — action destructive = double confirmation ; feedback visible (spin sync, états) ; jamais d'ambiguïté sur ce qui a été envoyé.
5. **Honnête sur la fraîcheur** — données périmées ou en cache toujours signalées (dot live, horodatage, tuiles atténuées scooter éteint).

## Accessibility & Inclusion

Pas d'exigence formelle. Bonnes pratiques par défaut : contraste ≥ 4.5:1, navigation clavier, `prefers-reduced-motion`, cibles tactiles ≥ 28px, ne pas coder l'info uniquement par la couleur quand c'est peu coûteux.
