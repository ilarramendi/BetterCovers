FROM debian
RUN apt-get -y update
RUN apt-get install -y cutycapt xvfb mediainfo ffmpeg wget
RUN wget -O BetterCovers 'https://github.com/ilarramendi/Cover-Ratings/releases/download/v0.6-linux/BetterCovers' -q
RUN chmod +x ./BetterCovers
RUN mkdir /tmp/runtime
RUN chmod 0700 /tmp/runtime
ENV XDG_RUNTIME_DIR /tmp/runtime
ENTRYPOINT xvfb-run -a ./BetterCovers \
        "/media/*" \
        -c "/config/config.json" \
        -tmdb "$TMDB" \
        -omdb "$OMDB" \
        -w "$w" \
        -o "$o"