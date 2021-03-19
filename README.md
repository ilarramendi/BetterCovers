# Cover Ratings
**This is still a WIP!**

Script intended to automaticaly generate cover images for Emby/Plex/Jellyfinn/etc library with RottenTomatoes, IMDB and Metascore scores.

**Update: It works with series now too!**  
**Update: Added executable for easyer use!**  
**Update: Added parameters for alignment and change color, also it should work with jellyfin now!**

# Example (Emby)
![example](https://user-images.githubusercontent.com/30437204/111736686-17595a80-885d-11eb-9884-bfba192114d8.png)

Cover images are saved as poster.jpg inside the folder of the media.  
Scores alignment can be customized with [parameters](#aditional-parameters).  
After executing the script you have to update the library metadata on Emby/Plex/Jellyfin for this to take effect!

# Api key
To get the metadata / cover images this script uses [omdbapi](http://www.omdbapi.com/) to get a free api key visit [this](http://www.omdbapi.com/apikey.aspx) link.

To use the api key and save it for future use you can execute the script like this:  
 ```./CoverRatings '/Movies/*' -a apiKey```  
This only needs to be run once with the api key, as it will be stored inside ```config.json```

# Supported media folder names are:
Recommended: ```/media/Movie Name (year)``` or ```/media/Movie Name year```  
Working: ```/media/Movie Name```

# Downloading
To download the latest copy of the script run:  
``` wget https://github.com/ilarramendi/Cover-Ratings/releases/download/0.2/CoverRatings; chmod +x CoverRatings```  
Also you can download the whole project and run the executable or the python script.


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
use: ```./CoverRatings '/media/*'```

# Aditional Parameters
Parameters can be used without any particular order  
```-vt``` Align scores on top  
```-hl``` Align scores to the left   
```-hr``` Align scores to the right  
```-b '#ff0000ff'``` Change background color (color can be a hex with 6 digits to set transparency)  
```-t '#000000ac'``` Change text color (color can be a hex with 6 digits to set transparency)  
```-s 3``` Set space between image and text  
```-a abc456``` Set and save the api key
