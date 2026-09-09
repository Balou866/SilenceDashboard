#!/bin/sh
# nginx:alpine exécute tous les /docker-entrypoint.d/*.sh avant de démarrer nginx.
# Injecte l'IMEI (variable d'environnement de la stack) dans la page servie.
set -e
sed "s/TON_IMEI/$IMEI/g" /index.template.html > /usr/share/nginx/html/index.html
