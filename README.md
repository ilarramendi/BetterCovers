# Better Covers
BetterCovers is a script to automaticaly generate covers and backdrops with embeded ratings, mediainfo, language, certifications, age ratings, source, production companies, etc!

## Examples
<img src="https://user-images.githubusercontent.com/30437204/139999685-99a366ab-a3f7-4967-a690-b73482827328.jpg" width="49.7%"> <img src="https://user-images.githubusercontent.com/30437204/139999850-99fd67a6-bfad-41cf-99fb-b3572907330b.jpg" width="49.7%">
<img src="https://user-images.githubusercontent.com/30437204/139999682-c146b1fc-0021-4c26-b4e9-048cc763fa2d.jpg" width="100%">

The script is made to be fully customizable, all properties can be disabled and custom cover templates can be selected based on a large number of filters!   
After executing the script you have to refresh the library on Emby/Plex/Jellyfin for this to take effect! (Or configure the agent in the config file to automaticaly update the library!)

## Downloading
### Docker
The easiest option for running is using [docker](https://hub.docker.com/r/ilarramendi/better-covers) (Runs 50% slower than the script for some reason).  
``` 
docker run -i --rm \
  -v /path/to/media:/media \
  -v /path/to/config:/config \
  -e parameters="-o -w 20" \
  ilarramendi/better-covers 
```
### Python
Clone the project: `git clone https://github.com/ilarramendi/BetterCovers`  
Install python requirments: `pip3 install -r requirements.txt`  
Install program requirments: `sudo apt install -y wkhtmltopdf ffmpeg`  
Run: `python3 BetterCovers.py '/path/to/media/*'`  
 
## Folder structure
Each movie needs to be inside a unique folder.  
Each TV show season must be inside a unique folder.  
For better identification folders names can have imdb or tmdb ids like: `[tmdbid=123456]` or `[imdbid=123456]`   

## Planned features
- [ ] Option to save images on Agent metadata folder to improve menu loading time (if metadata is on faster drive)
- [ ] Different themes (suggestions are apreciate)
- [ ] Use existing cover
- [ ] Add aditional mediainfo properties (dolby, ATMOS, audio channels)
- [ ] Add connection with Sonarr and Radarr api (or script on import)
- [ ] Add connection to plex api
- [ ] Add original downloaded image cache for faster cover creation (wkhtmltopdf cache not working)

## Config.json
This specifies settings for running the scrip.
| Name                      | Description                                             | Values                                 |
| ------------------------- | ------------------------------------------------------- | -------------------------------------- | 
| defaultAudioLanguage      | Default language to use if no language found            | ENG (ISO 639-2/T), empty for off       |
| mediainfoUpdateInterval   | Time to update mediainfo (days)                         | 14                                     |
| IMDBTitlesUpdateInterval  | Time to update IMDB titles dataset (days)               | 7                                      |
| IMDBRatingsUpdateInterval | Time to update IMDB ratings dataset (days)              | 7                                      |
| preferedImageLanguage     | Prefered image language to download                     | en-US (Language code)                  |
| ratingsOrder              | Order to show ratings                                   | (dont remove items, just change order) |
| mediainfoOrder            | Prefered image language to download                     | (dont remove items, just change order) |
| wkhtmltoimagePath         | Path to wkhtmltoimage                                   | /usr/bin/wkhtmltoimage                 |
| tmdbApi                   | TMDB api key (can be changed if tmdb api limit reached) | 123456789                              |
| omdbApi                   | OMDB api key (used to get missing metadata, not needed) | 123456789                              |

### Agent (Automaticaly update library)
| Name           | Description                                        | Values                     |
| -------------- | -------------------------------------------------- | -------------------------- | 
| type           | Media agent to update                              | jellyfin or emby           |
| url            | Full path to media agent                           | http://192.168.1.7:8989    |
| apiKey         | Media agent api key                                | 123456456                  |

### Scraping
This section enables/disables different ratings providers
| Name           | Description                                           | Values                     |
| -------------- | ---------------------------------------------------   | -------------------------- | 
| RT             | Get RT-CF certification, RT and RTA ratings (SLOWEST) | true or false              |
| IMDB           | Get IMDB ratings from dataset                         | true or false              |
| textlessPosters| Not workint ATM!                                      | true or false              |
| LB             | Get LB ratings                                        | true or false              |
| TVTime         | Get TVTime ratings (Almost all are positive ratings)  | true or false              |
| MetaCritic     | Get MTC-MS certifications and MTC ratings             | true or false              |
| Trakt          | Get Trakt ratings                                     | true or false              |

### Templates
This section defined wich template is going to be used based on media properties/ratings/etc, the first template matching will be selected so place the more restrictive options first.
The only required property is: `cover`
| Name                | Description                                                | Values                           |
| ------------------- | ---------------------------------------------------------- | -------------------------------- | 
| cover               | Html file to use, needs to be located on media/templates   | cover, goodMovies, etc...        |
| ratings             | Filter by ratings with a value > or < than a number        | "TMDB": ">7.5"                   |
| path                | Filter by text on path                                     | /media/kidsMovies                |
| type                | Filter by type of media, sepparated by ','                 | movie,tv,season,episode,movie_backdrop,<br>tv_backdrop,season_backdrop |
| productionCompanies | Filter by production company TMDB id, int array            | [150, 250, 2]                    |
| ageRating           | Filter by age rating < than value                          | G, PG, PG-13, R, NC-17, NR       |



## Covers.json
This folder specifies wich properties are enabled for each cover type, most options are self-explanatory, these are the other options.
| Name                         | Description                                                         | Values                     |
| ---------------------------- | ------------------------------------------------------------------- | -------------------------- | 
| generateImages               | Extract images from media instead of downloading (NOT WORKING ATM)  | true or false              |
| audio                        | Audio languages to use (uses first language found)                  | ENG,SPA,JPN (ISO 639-2/T)  |
| output                       | Output file names separated by ';' ($NAME is replaced with filename)| poster.jpg;cover.png       |
| productionCompanies          | Array of production companies to show (IMDB PC id)                  | [123, 456, 451]            |
| productionCompaniesBlacklist | Blacklist or whitelist production companies                         | true or false              |
| productionCompaniesBlacklist | Blacklist or whitelist production companies                         | true or false              |
| usePercentage                | Use percentage for ratings instead of 0 - 10                        | true or false              |
| extractImage                 | Extract image with ffmpeg from media (EP cover, MV and TV backdrops)| true or false              |
| useExistingImage             | Use existing cover image if exists                                  | true or false              |


## Replacing Assets
Assets can be replaced inside the folder `media` in the work directory (can be changed with `-wd`, default wd is next to script or `/config` in docker), paths need to be the same as [here](https://github.com/ilarramendi/BetterCovers/tree/main/media).  


## Templates 
This is how you can customize covers however you like, just edit the html cover and generate images again with parameter `-o`.
Example templates can be found on [media/templates](https://github.com/ilarramendi/BetterCovers/tree/main/media/templates)
The script replaces certain tags on the html file.
| TAG                         | Raplace Value                                                                                                                            |
| --------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------- |
| `<!--TITLE-->`              | Title of media                                                                                                                           |
| `$IMGSRC`                   | Path to cover/backdrop                                                                                                                   |
| `<!--RATINGS-->`            | `<div class='ratingContainer ratings-NAME'><img src='...' class='ratingIcon'/>VALUE<label class='ratingText'></div>` <br>For each rating |
| `<!--MEDIAINFO-->`          | `<div class='mediainfoImgContainer mediainfo-PROPERY'><img src= '...' class='mediainfoIcon'></div>` <br>For each mediainfo property      |
| `<!--PRODUCTIONCOMPANIES-->`| `<div class='pcWrapper producionCompany-ID'><img src='...' class='producionCompany'/></div>` <br>For production company                  |
| `<!--CERTIFICATIONS-->`     | `<img src= "..." class="certification"/>`<br>For each certification                                                                      |


## Parameters
`-o true` Ovewrite any cover found  
`-wd /path/to/wd` Change the default working directory (where config files, images and covers are stored)    
`-w number` Number of workers to use, default 20 (using too many workers can result in images not loading correctly or hitting api limits)  
`-v number` Verbose level from 0 to 5, default 2.

## Credits
This project was inspired by [RPDB](https://ratingposterdb.com/)!  
