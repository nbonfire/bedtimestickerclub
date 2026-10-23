#!/bin/sh
set -eu

asset=/assets/button-card.js
expected=5d6e9c6afca01e8014653fa56bb5d6aa9248d832c34fb944a7f2c36329bc22d1

if [ -f "$asset" ] && printf '%s  %s\n' "$expected" "$asset" | sha256sum -c - >/dev/null 2>&1; then
  echo 'Button Card 7.0.1 is already cached.'
  exit 0
fi

echo 'Downloading Button Card 7.0.1...'
curl --fail --location --retry 3 --connect-timeout 15 --max-time 120 \
  https://github.com/custom-cards/button-card/releases/download/v7.0.1/button-card.js \
  --output "$asset.download"
printf '%s  %s\n' "$expected" "$asset.download" | sha256sum -c -
mv "$asset.download" "$asset"
echo 'Button Card is ready.'
