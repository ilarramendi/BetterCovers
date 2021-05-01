# Better Covers
_**This is still a WIP!**_  

This project was inspired by [RPDB](https://ratingposterdb.com/)!  
Better-Covers is a script to automaticaly generate cover images (and backdrops) with embeded ratings, mediainfo, language and age certifications! 

# Examples
<img src="https://user-images.githubusercontent.com/30437204/116767700-17c24500-aa08-11eb-855c-954b6623a863.jpg" width="49.5%"> <img src="https://user-images.githubusercontent.com/30437204/116767716-43452f80-aa08-11eb-985e-d38f6be31da1.jpg" width="49.5%">
<img src="https://user-images.githubusercontent.com/30437204/116767708-24df3400-aa08-11eb-8f3d-5929a16048b3.jpg" width="100%">

Cover images are saved as folder.jpg, episode covers as filename.jpg and backdrops as backdrop.jpg (customizable).     
Most important things can be customized in the [config](#configjson) file, and it can be fully customized modifying `cover.html` and `cover.css`  
After executing the script you have to refresh the library on Emby/Plex/Jellyfin for this to take effect!

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
```wget https://github.com/ilarramendi/Cover-Ratings/releases/download/v0.7-linux/BetterCovers; chmod +x CoverRatings```  

Alternatively you can download the whole project and run `python3 BetterCovers.py` (aditional pypi dependencies need to be installed).

# Api keys
At the moment the scripts works the best with 2 api keys, sorry about that :(  
To get the metadata / cover images it uses [TMDB](https://www.themoviedb.org/), to get a key you have to create an account.

And to get missing metadata and ratings from IMDB, RT and MTS it uses [OMDBApi](http://www.omdbapi.com/) to get a free api key visit [this](http://www.omdbapi.com/apikey.aspx) link.  
<!--The script can work without any api key, but it only will generate covers for episodes with embeded mediainfo if generateImages is enabled, in the future this will also be posible with existing cover images.-->

To save the api keys edit ```config.json``` or execute the script like this to automaticaly save them:  
 ```./CoverRatings '/Movies/*' -tmdb TMDBApiKey -omdb OMDBApiKey```  
 
 # Dependencies
The only non optional external dependency is `cutycapt` to generate the images.  
This can be installed with: `sudo apt install -y cutycapt`.  
Aditionaly to get screenshots and get mediainfo it uses `ffmpeg` 

This script also needs a X server running to execute, if you are not using a graphical display its posible to use a lighweight server like xvfb:  
`xvfb-run -a ./BetterCovers '/movies/*'`
 
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
- [ ] Add aditional providers
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
- [ ] Add source (blueray, web, dvd...)

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
| Name           | Description                                        | Values                     |
| -------------- | -------------------------------------------------- | -------------------------- | 
| defaultAudio   | Default language to use if no language found       | str, ex: ENG, empty for off|
| englishUSA     | Use USA flag for english language instead of UK    | boolean                    |


### Agent
| Name           | Description                                        | Values                     |
| -------------- | -------------------------------------------------- | -------------------------- | 
| type           | Media agent to update                              | jellyfin or emby           |
| url            | Full path to media agent                           | http://192.168.1.7:8989    |
| apiKey         | Media agent api key                                | 123456456                  |


## Replacing Assets
Assets can be placed inside a folder called `media` next to the executable/script, paths have to be the same as [here](https://github.com/ilarramendi/Cover-Ratings/tree/main/media).  

If a file is not found it uses the one stored inside the executable

## Custom html/css  
This way you can fully customize covers how you like.  
Its recommended editing the scss file and compiling it to css!  
Files need to be stored next to the executable/script.  
The html file is customized from the script to add the images/ratings (this will probably change in the future),  
it replaces the tag `<!--RATINGS-->` with:
```
<div class = 'ratingContainer'>
   <img src= './PROVIDER.png' class='ratingIcon'> 
   <label class='ratingText'>VALUE</label>
</div>
```  
For each enabled PROVIDER, and `<!--MEDIAINFO-->` with:
```
<div class='mediainfoImgContainer'>
   <img src= './PROPERTY.png' class='mediainfoIcon'> 
</div>
```  
For each enabled mediainfo PROPERTY.  
In addition to this it overwrites the same variables that are on `:root {}` from the css with the values from `config.json` as a style tag in the html and adds a stylesheet import to the default cover.css or a new file located next to the executable.

# Parameters
`-o true` Ovewrite covers  
`-c /path/to/config.json` Change path to config.json    
`-w number` Number of workers to use, default 10 (ryzen 3800x can handle up to 200 workers)  
`-omdb apiKey` Store the OMDB api key  
`-tmdb apiKey` Store TMDB api key
`-v number` Verbose level, from 0 to 3
