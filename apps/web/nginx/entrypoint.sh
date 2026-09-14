#!/bin/sh
set -e

: "${API_BASE_URL:=http://localhost:8080}"

envsubst '${API_BASE_URL}' < /usr/share/nginx/html/config.template.js > /usr/share/nginx/html/config.js

exec nginx -g 'daemon off;'