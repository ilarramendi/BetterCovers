FROM python:3
RUN apt-get -y update
RUN apt-get install -y wkhtmltopdf ffmpeg wget git tzdata
RUN git clone https://github.com/ilarramendi/BetterCovers
#ADD . /BetterCovers
ENV TZ America/Montevideo
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone
WORKDIR "/BetterCovers"
RUN pip3 install -r ./requirements.txt
ENTRYPOINT python3 ./BetterCovers.py "/media/*" -wd "/config" $parameters
