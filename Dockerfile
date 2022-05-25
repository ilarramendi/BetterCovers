FROM python:3.9-slim
RUN apt-get -y update && apt-get install -y wkhtmltopdf ffmpeg tzdata && pip3 install requests exif
ENV TZ="America/Montevideo" \
    parameters="" \
    fileMask="*"
ADD . /BetterCovers
ENTRYPOINT sh /BetterCovers/src/scripts/start_container.sh