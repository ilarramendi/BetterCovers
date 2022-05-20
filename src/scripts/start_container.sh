cp -n -r /BetterCovers/config /config
cp -n -r /BetterCovers/assets /config
python3 src/BetterCovers.py "/media/$fileMask" -wd "/config" $parameters