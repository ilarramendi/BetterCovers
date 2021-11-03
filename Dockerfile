FROM python:3.8-slim
RUN apt-get -y update
RUN apt-get install -y wkhtmltopdf ffmpeg tzdata
ADD . /BetterCovers
ENV TZ America/Montevideo
ENV parameters ""
ENV fileMask "*"
WORKDIR "/BetterCovers"
RUN pip3 install -r ./requirements.txt
ENTRYPOINT python3 ./BetterCovers.py "/media/$fileMask" -wd "/config" $parameters
