# Cover Ratings
**This is still a WIP!**

Script intended to automaticaly generate cover images for Emby/Plex/Jellyfinn library embeded with RT, IMDB, MTS and TMDB scores and media info.  
It generates an html file with the cover and then makes a png from that file with `cutycapt`, in the future the idea would be to fully integrate this with clients to have the reactive html displayed instead of an image.

# Example
![example](https://user-images.githubusercontent.com/30437204/112571443-cac6cf80-8dc6-11eb-8975-ef5f6e956a02.png) 

Cover images are saved as poster.jpg inside the folder of the media.  
Most important things can be customized in the [config](#config) file, and it can be fully customized modifying `cover.html` and `cover.css`  
After executing the script you have to update the library metadata on Emby/Plex/Jellyfin for this to take effect!

# Dependencies
When compiled should only have 2 external dependencies: `mediainfo` and `cutycapt`  
You can install them with: `sudo apt install cutycapt mediainfo`

This script also needs a X server running to execute, if you are not using a graphical display its posible to use a lighweight server like xvfb:  
`xvfb-run --server-args="-screen 1, 1024x768x24" ./BetterCovers '/movies/*'`

# Downloading
To download the latest executable of the script run: WIP  
<!-- ```wget https://github.com/ilarramendi/Cover-Ratings/releases/download/0.3.5/CoverRatings; chmod +x CoverRatings```  -->

Also you can download the whole project and run the python script.

# Api key
At the moment the scripts needs 2 api keys to work, sorry about that :(  
To get the metadata / cover images it uses [TMDB](https://www.themoviedb.org/).  
And to get missing metadata and ratings from IMDB, RT and MTS it uses [omdbapi](http://www.omdbapi.com/) to get a free api key visit [this](http://www.omdbapi.com/apikey.aspx) link.

To use the api keys and save it for future use you can execute the script like this:  
 ```./CoverRatings '/Movies/*' -tmdb TMDBApiKey -omdb OMDBApiKey```  
This only needs to be run once with the api keys, as they will be stored inside ```config.json```

# Supported media folder names are:
Recommended: ```/media/Movie Name (year)```, ```/media/Movie Name year``` or ```/media/Movie.Name.year```
OK: ```/media/Movie Name```

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

# Customization
The idea of this script is to be fully customizable, for this purpouse you can change the values on each section of the config.json file, edit the Ratings/MediaInfo images or even create your own css/html files!

# Config.json

# Replacing Images
Images can be placed inside a folder called `media` next to the executable/script, needed file names are:  
`UHD.png, HD.png, SD.png, HDR.png, SDR.png, HEVC.png, AVC.png, RT.png, TMDB.png, IMDB.png, MTS.png`  
Names are self explanatory.

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
In addition to this it overwrites the same variables that are on `:root {}` from the css with the values from `config.json` as a style tag in the html.

# Parameters
`-o` Ovewrite covers  
`-w number` Number of threads to use, default 4  
`-omdb apiKey` Store the OMDB api key  
`-tmdb apiKey` Store TMDB api key  
