pyinstaller -F BetterCovers.py \
    --add-data ./media/languages:/files/media/languages \
    --add-data ./media/certifications:/files/media/certifications \
    --add-data ./media/mediainfo:/files/media/mediainfo \
    --add-data ./media/ratings:/files/media/ratings \
    --add-data ./media/overlays:/files/media/overlays \
    --add-data ./config.json:/files \
    --add-data ./cover.*:/files
