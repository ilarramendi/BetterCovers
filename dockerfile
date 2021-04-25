FROM debian
RUN apt-get -y update
RUN apt-get install -y cutycapt xvfb mediainfo ffmpeg wget
RUN wget -O BetterCovers 'https://github.com/ilarramendi/Cover-Ratings/releases/download/latest-linux/BetterCovers' -q
RUN chmod +x ./BetterCovers
RUN mkdir /tmp/runtime
RUN chmod 0700 /tmp/runtime
ENV XDG_RUNTIME_DIR /tmp/runtime
ENV DISPLAY :99
ENTRYPOINT xvfb-run -a ./BetterCovers "/media/*" -o -c "/config.json"