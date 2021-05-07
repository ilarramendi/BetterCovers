FROM debian
RUN apt-get -y update
RUN apt-get install -y wkhtmltopdf ffmpeg wget
RUN wget -O BetterCovers 'https://github.com/ilarramendi/Cover-Ratings/releases/download/v0.8-linux/BetterCovers' -q
RUN chmod +x ./BetterCovers
ENV w 20
ENV v 2
ENTRYPOINT ./BetterCovers \
        "/media/*" \
        -wd "/config" \
        -tmdb "$tmdb" \
        -omdb "$omdb" \
        -w "$w" \
        -o "$o" \
        -v "$v"