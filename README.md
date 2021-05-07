# Better Covers
_**This is still a WIP!**_  

This project was inspired by [RPDB](https://ratingposterdb.com/)!  
Better-Covers is a script to automaticaly generate cover images (and backdrops) with embeded ratings, mediainfo, language and age certifications! 

# Examples
<img src="https://user-images.githubusercontent.com/30437204/117388955-f78bfd80-aec1-11eb-946d-98f9db120ee6.png" width="49.7%"> <img src="https://user-images.githubusercontent.com/30437204/117389362-a16b8a00-aec2-11eb-8c9c-67a896c5dd41.png" width="49.7%">
<img src="https://user-images.githubusercontent.com/30437204/117389444-c3fda300-aec2-11eb-82c5-44ffd9b040c3.png" width="100%">

Cover images are saved as folder.png, episode covers as filename.png and backdrops as backdrop.png (customizable).     
Most important things can be customized in the [config](#configjson) file, and it can be fully customized modifying `cover.html` and `cover.css`  
After executing the script you have to refresh the library on Emby/Plex/Jellyfin for this to take effect! (Now you can also configure the agent in config file to automaticaly update agent!)

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
```wget https://github.com/ilarramendi/Cover-Ratings/releases/download/v0.8-linux/BetterCovers; chmod +x BetterCovers```  

Alternatively you can download the whole project and run `python3 BetterCovers.py` (aditional pypi dependencies need to be installed).

# Api keys
At the moment the scripts works the best with 2 api keys, but only 1 is needed (TMDB recommended). 
To get the metadata / cover images it uses [TMDB](https://www.themoviedb.org/), to get a key you have to create an account.

And to get missing metadata and ratings from IMDB, RT and MTS it uses [OMDBApi](http://www.omdbapi.com/) to get a free api key visit [this](http://www.omdbapi.com/apikey.aspx) link.  
<!--The script can work without any api key, but it only will generate covers for episodes with embeded mediainfo if generateImages is enabled, in the future this will also be posible with existing cover images.-->

To save the api keys edit ```config.json``` or execute the script like this to automaticaly save them:  
 ```./CoverRatings '/Movies/*' -tmdb TMDBApiKey -omdb OMDBApiKey```  

 
 # Dependencies
The only non optional external dependency is `wkhtmltopdf` to generate the images.  
This can be installed with: `sudo apt install -y wkhtmltopdf`.  
Aditionaly to get screenshots and get mediainfo it uses `ffmpeg` 
 
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

or

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
- [ ] Executable for windows
- [ ] Option to save images on Emby metadata folder to improve menu loading time (if metadata is on faster drive)
- [ ] Different themes (suggestions are apreciate)
- [ ] Improve to run as a service and make script to create service on linux
- [ ] Add to PyPi?
- [ ] Plugin for most common media servers
- [ ] Use existing cover
- [x] Episodes support, get cover from internet or extract with ffmpeg
- [ ] Add aditional mediainfo properties (dolby, ATMOS, language?, audio channels)
- [ ] Add studio/provider
- [ ] Add aditional providers (suggestions?)
- [ ] Add certifications
- [ ] Add python dependencies file
- [x] Add docker container
- [x] Make docker container fully customizable like script
- [x] Flags for audio language
- [x] Add backdrop support
- [ ] Add connection with Sonarr and Radarr api
- [x] Add connection to emby and jellyfin api
- [ ] Add connection to plex api
- [x] Add age certifications
- [x] Add source (blueray, web, dvd...)
- [x] Add custom overlays

# Customization
The idea of this script is to be fully customizable, for this purpouse you can change the values on each section of the config.json file, edit the Ratings/MediaInfo images or even create your own css/html files!

## Config.json
### Sections
The config file is divided in 5 sections: `tv`, `season`, `episode`, `backdrop` and `movie`. Each section can be customized individually.  
| Name           | Description                                        | Values                     |
| -------------- | -------------------------------------------------- | -------------------------- | 
| config         | Sets which ratings/mediainfo item is enabled       |                            |
| position       | Position of item                                   | top, bottom, left or right |
| alignment      | Alignment on position                              | start, center or end       |
| imgSize        | Icon size                                          | HTML size, ex: 60px        |
| padding        | Container padding                                  | HTML size, ex: 60px        |
| space          | Space between each icon                            | HTML size, ex: 60px        |
| color          | Container background color                         | HTML Color, ex: #ff0000ff  |
| fontFamily     | Text font family                                   | HTML Font, ex: Arial       |
| textColor      | Text color                                         | HTML Color ex: #ff0000ff   |
| fontSize       | Text size                                          | HTML size, ex: 60px        |
| iconSpace      | Space between ratings icon and text                | HTML size, ex: 60px        |
| generateImages | Generate images with ffmpeg instead of downloading | boolean                    |
| audio          | Audio languages to use (uses first language found) | str, ex: ENG,SPA,JPN       |
| outpu          | Image file name                                    | str, ex: cover.jpg         |
| width          | Image Width                                        | int, ex: 2000              |
| heigh          | Image Height                                       | int, ex: 3000              |

### Global
| Name                  | Description                                        | Values                     |
| --------------------- | -------------------------------------------------- | -------------------------- | 
| defaultAudio          | Default language to use if no language found       | str, ex: ENG, empty for off|
| englishUSA            | Use USA flag for english language instead of UK    | boolean                    |
| metadataUpdateInterval| Time to update metadata and mediainfo (days)       | number                     |


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
| IMDB           | Get up to date ratings from IMDB and MTC (MustSee) | true or false              |
| textlessPosters| Use textless poster if found in MovieMania (SLOW!) | true or false              |

### Overlays
Custom overlays can be placed on `media/overlays`, an example is available on: `media/overlays/kids.html`
| Name           | Description                                               | Values                          |
| -------------- | --------------------------------------------------------- | ------------------------------- | 
| type           | Type of media separated by ',' or * for any               | movie,tv,backdrop,season,episode|
| name           | Name of the html file to use (without .html)              | kids                            |
| path           | Text that needs to be on path to be applied (or * for any)| /media/kidsMovies               |






## Replacing Assets
Assets can be placed inside a folder called `media` in the work directory (can be changed with -wd, default wd is next to script), paths have to be the same as [here](https://github.com/ilarramendi/Cover-Ratings/tree/main/media).  

## Custom html/css  
This way you can fully customize covers how you like.  
Files need to be stored in the work directory.  
The html file is customized from the script to add the images/ratings (this will probably change in the future),  
it replaces the tag `<!--RATINGS-->` with:
```
<div class = 'ratingContainer'>
   <img src= '../media/providers/PROVIDER.png' class='ratingIcon'> 
   <label class='ratingText'>VALUE</label>
</div>
```  
For each enabled PROVIDER, and `<!--MEDIAINFO-->` with:
```
<div class='mediainfoImgContainer'>
   <img src= '../media/mediainfo/PROPERTY.png' class='mediainfoIcon'> 
</div>
```  

For each enabled mediainfo PROPERTY.  
In addition to this it overwrites the same variables that are on `:root {}` from the css with the values from `config.json` as a style tag in the html and adds a stylesheet import to the default cover.css or a new file located next to the executable.

# Parameters
`-o true` Ovewrite covers  
`-wd /path/to/wd` Change the default working directory (where config and icons are stored)    
`-w number` Number of workers to use, default 20 (using too many workers can result in images not loading correctly)  
`-omdb apiKey` Store the OMDB api key  
`-tmdb apiKey` Store TMDB api key
`-v number` Verbose level from 0 to 3, default 2.
