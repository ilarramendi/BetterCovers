# Better Covers
BetterCovers is a script to automaticaly generate covers and backdrops with embeded ratings, mediainfo, language, certifications, age ratings, source, production companies, etc!

## Examples
<img src="https://user-images.githubusercontent.com/30437204/139999685-99a366ab-a3f7-4967-a690-b73482827328.jpg" width="49.7%"> <img src="https://user-images.githubusercontent.com/30437204/139999850-99fd67a6-bfad-41cf-99fb-b3572907330b.jpg" width="49.7%">
<img src="https://user-images.githubusercontent.com/30437204/139999682-c146b1fc-0021-4c26-b4e9-048cc763fa2d.jpg" width="100%">

The script is made to be fully customizable, all properties can be disabled and custom cover templates can be selected based on a large number of filters!   
After executing the script you have to refresh the library on Emby/Plex/Jellyfin for this to take effect! (Or configure the agent in the config file to automaticaly update the library!)

## Downloading
### Docker
The easiest option for running is using [docker](https://hub.docker.com/r/ilarramendi/bettercovers).  
``` 
docker run -i --rm \
  -v /path/to/media:/media \
  -v /path/to/config:/config \
  -e parameters="-w 20" `#OPTIONAL` \
  -e TZ=America/New_York `#OPTIONAL` \
  -e fileMask="*" `#OPTIONAL` \
  ilarramendi/bettercovers asd
```
### Python
Clone the project: `git clone https://github.com/ilarramendi/BetterCovers`  
Install python requirments: `pip3 install -r requirements.txt`  
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
[config.md](https://github.com/ilarramendi/BetterCovers/blob/main/config.md)

## Parameters
`-o` Ovewrite any cover found (images are automaticaly overwriten if info changes)  
`-wd /path/to/wd` Change the default working directory (where config files, images and covers are stored)    
`-w number` Number of workers to use, default 20 (using too many workers can result in images not loading correctly or hitting api limits)  
`--log-level number` Verbose level from 0 to 5, default 2.  
`--dry` Performs a dry run, only getting metadata, not generating any image.  
`--json` Save metadata to metadata.json (usefull for debugin and getting data out for other programs).  
`--no-colors` Remove colors from output (Usefull for docker).  
