#!/bin/bash
if [[ $radarr_eventtype == "Download" ]] ; then
    /BetterCovers "$radarr_movie_path" -o -w 1 -c /config/config.json >> /config/better-covers.log
fi
