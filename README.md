# Cover Ratings
**This is still a WIP!**

Script intended to automaticaly generate cover images for Emby, Plex, Jellyfinn, etc. library with RottenTomatoes, IMDB and Metascore scores.

**Update: It works with series now too!**

# Example (Emby)
![example](https://user-images.githubusercontent.com/30437204/111736686-17595a80-885d-11eb-9884-bfba192114d8.png)

Cover images are saved as cover.jpg inside the folder of the media.

After executing the script you have to update the library metadata on emby/plex for this to take effect!

Bottom line width, text height, img height, text color and border color can be customized!

# Api key
To get the metadata / cover images this script uses [omdbapi](http://www.omdbapi.com/) to get a free api key visit [this](http://www.omdbapi.com/apikey.aspx) link.

To use the api key and save it for future use you can execute the script like this:  
 ```python3 CoverRatings.py '/Movies/*' apiKey```  
This only needs to be run once with the api key, as it will be stored inside ```config.json```

# Supported media folder names are:
Recommended: ```/media/Movie Name (year)``` or ```/media/Movie Name year```  
Ok: ```/media/Movie Name```

# Usage
If movie library looks like this:

```
/Movies
  ├── Movie1 (year)
  │      └── Movie1.mkv
  ├── Movie2 (year)
  │      └── Movie2.mp4 
  └──  ...

```
use: ```python3 CoverRatings.py '/Movies/*'```

If tv library looks like this:
```
/Tv
  ├── Series1 (year)
  │      └── Season 1
  ├── Series2 (year)
  │      └── Season 1
  └──  ...
```
use: ```python3 CoverRatings.py '/Tv/*'```
