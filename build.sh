pyinstaller -F BetterCovers.py \
    --add-data ./media/languages:/files/media/languages \
    --add-data ./media/mediainfo:/files/media/mediainfo \
    --add-data ./media/ratings:/files/media/ratings \
    --add-data ./media/covers:/files/media/covers \
    --add-data ./media/ageRatings:/files/media/ageRatings \
    --add-data ./config.json:/files