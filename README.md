# Better Covers
_**This is still a WIP!**_  

This project was inspired by [RPDB](https://ratingposterdb.com/)!  
Better-Covers is a script to automaticaly generate cover images (and backdrops) with embeded ratings, mediainfo, language, certifications, age ratings and production companies! 

# Examples
<img src="https://user-images.githubusercontent.com/30437204/118219642-48ff3400-b450-11eb-8aa4-ca602c28fe08.png" width="49.7%"> <img src="https://user-images.githubusercontent.com/30437204/117389362-a16b8a00-aec2-11eb-8c9c-67a896c5dd41.png" width="49.7%">
<img src="https://user-images.githubusercontent.com/30437204/118219636-44d31680-b450-11eb-89f4-65b3074518da.png" width="100%">

Cover images are saved as folder.png, episode covers as filename.png and backdrops as backdrop.png and thumb.png (customizable).     
The script is made to be fully customizable, all properties can be disabled and custom covers can be selected based on a large number of filters!   
Most important things can be customized in the [config](#configjson) file, and and visual changes can be done adjusting html/css [cover](#covers-1) files.    
After executing the script you have to refresh the library on Emby/Plex/Jellyfin for this to take effect! (Or configure the agent in the config file to automaticaly update the library!)

# Downloading
The easiest option for running is using [docker](https://hub.docker.com/r/ilarramendi/better-covers).  
``` 
docker run -i --rm \
  -v /path/to/media:/media \
  -v /path/to/config:/config \
  -e o=false \
  -e w=20 \
  -e tmdb=xxxxxx \
  -e omdb=xxxxxx \
  -e v=2 \
  ilarramendi/better-covers 
```

To download the latest executable (LINUX) of the script run:  
```wget https://github.com/ilarramendi/Cover-Ratings/releases/download/v0.9-linux/BetterCovers; chmod +x BetterCovers```  
Alternatively you can download the whole project and run `python3 BetterCovers.py` (aditional pypi dependencies need to be installed).

# Api keys
At the moment the scripts works the best with 2 api keys, but only 1 is needed (TMDB recommended). 
To get the metadata / cover images it uses [TMDB](https://www.themoviedb.org/), to get a key you have to create an account.

And to get missing metadata and missing ratings it uses [OMDBApi](http://www.omdbapi.com/) to get a free api key visit [this](http://www.omdbapi.com/apikey.aspx) link.  
(OMDB is not realy needed but it covers some missing ratings)  

To save the api keys edit ```config.json``` or execute the script like this to automaticaly save them:  
 ```./CoverRatings '/Movies/*' -tmdb TMDBApiKey -omdb OMDBApiKey```  
 
 # Dependencies
To run the script outside of docker 2 dependencies need to be installed: `wkhtmltopdf` and `ffmpeg`.  
This can be done with: `sudo apt install -y wkhtmltopdf ffmpeg`.  
 
# Usage
If library looks like this:

Movies:
```
/media
  ├── Movie 1 (year)
  │      └── Movie 1.mkv
  ├── Movie 2 (year)
  │      └── Movie 2.mp4 
  └──  ...

```  
TV Shows:
```
/media
  ├── Tv Show 1 (year)
  │      ├── Season 1
  │      └──  ...
  ├── Tv show 2 (year)
  │      └── Season 1
  └──  ...
```  
***Use:*** ```./BetterCovers '/media/*'```

## Supported media folder names
 ```/media/Media Name (year)```  
 ```/media/Media Name year```  
 ```/media/Media.Name.year```  
 ```/media/Media_Name year```  
 ```/media/Media Name (year) [tags]```  
 The year is not needed but its recommended to find the correct media

# Planned features
- [ ] Option to save images on Agent metadata folder to improve menu loading time (if metadata is on faster drive)
- [ ] Different themes (suggestions are apreciate)
- [x] Improve to run periodicaly
- [ ] Add to PyPi?
- [ ] Use existing cover
- [ ] Add aditional mediainfo properties (dolby, ATMOS, audio channels)
- [ ] Add aditional ratings providers (suggestions?)
- [ ] Add python dependencies file
- [ ] Add connection with Sonarr and Radarr api
- [ ] Add connection to plex api
- [ ] Add original downloaded image cache for faster cover creation (wkhtmltopdf cache not working)

# Customization
The idea of this script is to be fully customizable, for this purpouse you can change the values on each section of the config.json file, edit the Ratings/MediaInfo images or even create your own css/html files!

## Config.json
### Sections
The config file is divided in 5 sections: `tv`, `season`, `episode`, `backdrop` and `movie`. Each section can be customized individually.  
Most options on this part just turn on and off icons / ratings these are the different ones:
| Name                | Description                                        | Values                     |
| ------------------- | -------------------------------------------------- | -------------------------- | 
| generateImages      | Extract images from media instead of downloading   | true or false              |
| audio               | Audio languages to use (uses first language found) | ENG,SPA,JPN (ISO 639-2/T)  |
| output              | Output file names separated by ';'                 | poster.jpg;cover.png       |
| productionCompanies | Show production companies logos                    | true or false              |

### Global
| Name                   | Description                                        | Values                          |
| ---------------------- | -------------------------------------------------- | ------------------------------- | 
| defaultAudio           | Default language to use if no language found       | ENG (ISO 639-2/T), empty for off|
| englishUSA             | Use USA flag for english language instead of UK    | true or false                   |
| metadataUpdateInterval | Time to update metadata and mediainfo (days)       | 14                              |
| usePercentage          | Show a percentage instead of 0 to 10               | true or false                   |

### Agent (To update library)
| Name           | Description                                        | Values                     |
| -------------- | -------------------------------------------------- | -------------------------- | 
| type           | Media agent to update                              | jellyfin or emby           |
| url            | Full path to media agent                           | http://192.168.1.7:8989    |
| apiKey         | Media agent api key                                | 123456456                  |

### Scraping
| Name           | Description                                        | Values                     |
| -------------- | -------------------------------------------------- | -------------------------- | 
| RT             | Get certifications and audience ratings            | true or false              |
| IMDB           | Get up to date ratings from IMDB, MTC and MTC-MS   | true or false              |
| textlessPosters| Use textless poster if found in MovieMania (SLOW!) | true or false              |
| LB             | Scrapping letterbox                                | true or false              |

### Covers
This is where most customization happends, media can have a specific html cover based on type, media propery, ratings, type, age ratings, etc.
This process is detailed in [Covers](##covers).
The only required property is: `cover`
| Name                | Description                                                | Values                           |
| ------------------- | ---------------------------------------------------------- | -------------------------------- | 
| cover               | Html file to use, needs to be located on /media/covers     | newCover, goodMovies, etc...     |
| ratings             | Filter by ratings with a value > or < than a number        | "TMDB": ">7.5"                   |
| path                | Filter by text on path                                     | /media/kidsMovies                |
| type                | Filter by type of media, sepparated by ','                 | movie,tv,backdrop,season,episode |
| productionCompanies | Filter by production company TMDB id, int array            | [150, 250, 2]                    |
| ageRating           | Filter by age rating < than value                          | G, PG, PG-13, R, NC-17, NR       |


## Replacing Assets
Assets can be placed inside a folder called `media` in the work directory (can be changed with -wd, default wd is next to script), paths have to be the same as [here](https://github.com/ilarramendi/Cover-Ratings/tree/main/media).  

## Covers 
This is how you can customize covers however you like, after selecting wich cover file to used based on the filters of [config](#configjson), the script replaces certain tags on the html file.
Examples cover templates can be found on [media/covers](https://github.com/ilarramendi/Cover-Ratings/tree/main/media/covers)
| TAG                         | Raplace Value                                                                                                                            |
| --------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------- |
| `<!--TITLE-->`              | Title of media                                                                                                                           |
| `$IMGSRC`                   | Path to cover/backdrop                                                                                                                   |
| `<!--RATINGS-->`            | `<div class='ratingContainer ratings-NAME'><img src='...' class='ratingIcon'/>VALUE<label class='ratingText'></div>` <br>For each rating |
| `<!--MEDIAINFO-->`          | `<div class='mediainfoImgContainer mediainfo-PROPERY'><img src= '...' class='mediainfoIcon'></div>` <br>For each mediainfo property      |
| `<!--PRODUCTIONCOMPANIES-->`| `<div class='pcWrapper producionCompany-ID'><img src='...' class='producionCompany'/></div>` <br>For production company                  |
| `<!--CERTIFICATIONS-->`     | `<img src= "..." class="certification"/>`<br>For each certification                                                                      |

# Parameters
`-o true` Ovewrite any cover found  
`-a true` Overwrite only files created by the script with different settings/ratings/etc  
`-wd /path/to/wd` Change the default working directory (where config files, images and covers are stored)    
`-w number` Number of workers to use, default 20 (using too many workers can result in images not loading correctly or hitting api limits)  
`-omdb apiKey` Store the OMDB api key  
`-tmdb apiKey` Store TMDB api key
`-v number` Verbose level from 0 to 3, default 2.
