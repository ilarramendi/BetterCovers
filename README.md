
# Better Covers
_**This is still a WIP!**_

Script intended to automaticaly generate cover images for Emby/Plex/Jellyfinn library embeded with RT, IMDB, MTS and TMDB scores and media info.  
It generates an html file with the cover and then makes a png from that file with `cutycapt`, in the future the idea would be to fully integrate this with clients to have the reactive html displayed instead of an image.

# Example

![MOVIES/SHOWS](https://user-images.githubusercontent.com/30437204/113346328-166b0300-930a-11eb-9b68-cfd9c462cace.png)
![SEASONS](https://user-images.githubusercontent.com/30437204/113346273-00f5d900-930a-11eb-828a-052861f8fd5c.png)
![EPISODES](https://user-images.githubusercontent.com/30437204/113343343-15d06d80-9306-11eb-8f83-df947e4c44e8.png)

Cover images are saved as poster.jpg inside the folder of the media.  
Most important things can be customized in the [config](#config) file, and it can be fully customized modifying `cover.html` and `cover.css`  
After executing the script you have to refresh the library on Emby/Plex/Jellyfin for this to take effect!

# Dependencies
When compiled only has 2 external dependencies: `mediainfo` and `cutycapt`  
You can install them with: `sudo apt install -y cutycapt mediainfo`

This script also needs a X server running to execute, if you are not using a graphical display its posible to use a lighweight server like xvfb:  
`xvfb-run -a ./BetterCovers '/movies/*'`

# Downloading
To download the latest executable (LINUX) of the script run:  
```wget https://github.com/ilarramendi/Cover-Ratings/releases/download/v0.4-linux/BetterCovers; chmod +x CoverRatings```  

In addition to the executable you need to download the default configuration file `config.json` to do this you can run:  
```wget https://raw.githubusercontent.com/ilarramendi/Cover-Ratings/main/config.json```

Alternatively you can download the whole project and run `python3 BetterCovers.py`.

# Api key
At the moment the scripts needs 2 api keys to work, sorry about that :(  
To get the metadata / cover images it uses [TMDB](https://www.themoviedb.org/), to get a key you have to create an account.

And to get missing metadata and ratings from IMDB, RT and MTS it uses [OMDBApi](http://www.omdbapi.com/) to get a free api key visit [this](http://www.omdbapi.com/apikey.aspx) link.  
It can probably work without the OMDB api key but will only have ratings from TMDB

To use the api keys and save it for future use you can execute the script like this:  
 ```./CoverRatings '/Movies/*' -tmdb TMDBApiKey -omdb OMDBApiKey```  
This only needs to be run once with the api keys, as they will be stored inside ```config.json```

# Supported media folder names
 ```/media/Media Name (year)```  
 ```/media/Media Name year```  
 ```/media/Media.Name.year```  
 ```/media/Media_Name year```  
  ```/media/Media Name (year) [tags]```  
 The year is not needed but its recommended to find the correct media
 
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

# Planned features
- [ ] Executable for windows
- [ ] Option to save images on Emby metadata folder to improve menu loading time (if metadata is on faster drive)
- [ ] Different themes (suggestions are apreciate)
- [ ] Improve to run as a service and make script to create service on linux
- [ ] Add to PyPi?
- [ ] Plugin for most common media servers
- [ ] Use existing cover
- [x] Episodes support, get cover from internet or extract with ffmpeg (ffmpeg extraction still missing)

# Customization
The idea of this script is to be fully customizable, for this purpouse you can change the values on each section of the config.json file, edit the Ratings/MediaInfo images or even create your own css/html files!

# Config.json
WIP

# Replacing Images
Images can be placed inside a folder called `media` next to the executable/script, file names are:  
`UHD.png, HD.png, SD.png, HDR.png, UHD-HDR.png, SDR.png, HEVC.png, AVC.png, RT.png, TMDB.png, IMDB.png, MTS.png`  
If a file is not found it uses the one stored inside the executable


# Custom html/css  
This is way you can fully customize covers how you like.  
Its recommended editing the scss file and compiling it to css!  
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
In addition to this it overwrites the same variables that are on `:root {}` from the css with the values from `config.json` as a style tag in the html and add a stylesheet import to the default cover.css or a new file located next to the executable

# Parameters
`-o` Ovewrite covers  
`-w number` Number of threads to use, default 4  
`-omdb apiKey` Store the OMDB api key  
`-tmdb apiKey` Store TMDB api key  

# Credits
This project was inspired by [Rating Poster Database](https://ratingposterdb.com/)!
