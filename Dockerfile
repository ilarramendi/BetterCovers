FROM python:3
RUN apt-get -y update
RUN apt-get install -y wkhtmltopdf ffmpeg wget git
RUN git clone https://github.com/ilarramendi/BetterCovers
WORKDIR "/BetterCovers"
RUN python3 -m pip install -r ./requirements.txt
ENTRYPOINT python3 ./BetterCovers.py "/media/*" -wd "/config"
