# Better Covers
BetterCovers is a script to automaticaly generate covers and backdrops with embeded ratings, mediainfo, language, certifications, age ratings, source, production companies, etc!

## Examples
<img src="https://user-images.githubusercontent.com/30437204/170800614-e4f1ff01-7fff-4cae-91a9-1a83528b9865.jpg" title="Free Guy" width="49.7%"> <img src="https://user-images.githubusercontent.com/30437204/170798832-ce6621fd-06e7-4442-8dbf-1614de14af8e.jpg" title="Family Guy Season 11" width="49.7%">
<img src="https://user-images.githubusercontent.com/30437204/170798830-06c0388d-f294-4b91-91d9-e8b8f969bd98.jpg" title="Castle Rock Season 1 Episode 6" width="100%">
<img src="https://user-images.githubusercontent.com/30437204/170800901-0389e701-e491-4b6a-8b10-654c3bffd97f.jpg" title="Free Guy" width="100%">

The script is made to be fully customizable, all properties can be disabled and custom cover templates can be selected based on a large number of filters!   
After executing the script you have to refresh the library on Emby/Plex/Jellyfin for this to take effect! (Or configure the agent in the config file to automaticaly update the library!)

## Downloading
### Docker
The easiest option for running is using [docker](https://hub.docker.com/r/ilarramendi/bettercovers).  
``` 
docker run -i --rm \
  -v /path/to/media:/media \
  -v /path/to/config:/config \
  -e parameters="-w 50" `#OPTIONAL` \
  -e fileMask="*" `#OPTIONAL` \
  ilarramendi/bettercovers
```
### Python
Clone the project: `git clone https://github.com/ilarramendi/BetterCovers`  
Install python requirments: `pip3 install -r requests jellyfish exif`  
Install program requirments: `sudo apt install -y wkhtmltopdf ffmpeg`  
Run: `python3 BetterCovers.py '/path/to/media/*'`  
 
## Folder structure
Each movie needs to be inside a unique folder.  
Each TV show season must be inside a unique folder.  
For better identification folders names can have imdb and/or tmdb ids like: `[tmdbid=123456]` or `[imdbid=123456]`   

## Planned features
- [ ] Option to save images on Agent metadata folder to improve menu loading time (media images on HDD load a bit slow on emby) (linx file to another drive with linux?)
- [ ] Different themes (suggestions are apreciate)
- [ ] Use existing cover
- [ ] Add aditional mediainfo properties (dolby, ATMOS, audio channels)
- [ ] Add connection with Sonarr and Radarr api (or script on import)
- [ ] Add connection to plex api
- [ ] Add original downloaded image cache for faster cover creation (wkhtmltopdf cache not working)
- [ ] Make docker container lighter and faster
- [ ] Way to choose cover (web ui?)


## Config.json
[config.md](https://github.com/ilarramendi/BetterCovers/blob/main/docs/config.md)

## Parameters
`-o` Ovewrite any cover found (images are automaticaly overwriten if info changes)  
`-wd /path/to/wd` Change the default working directory (where config files, images and covers are stored)    
`-w number` Number of workers to use, default 20 (using too many workers can result in images not loading correctly or hitting api limits)  
`--log-level number` Verbose level from 0 to 5, default 2.  
`--dry` Performs a dry run, only getting metadata, not generating any image.  
`--json` Save metadata to metadata.json (usefull for debugin and getting data out for other programs).  
`--no-colors` Remove colors from output (Usefull for docker).  
