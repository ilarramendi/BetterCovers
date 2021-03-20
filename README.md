# Cover Ratings
**This is still a WIP!**

Script intended to automaticaly generate cover images for Emby/Plex/Jellyfinn library with RottenTomatoes, IMDB and Metascore scores.

**Update: It works with series now too!**  
**Update: Added executable for easyer use!**  
**Update: Added parameters for alignment and change color, also it should work with jellyfin now!**  
**Update: Added suport for media info tags!!**

# Example (Emby)
Without MediaInfo:     With MediaInfo:  
![example](https://user-images.githubusercontent.com/30437204/111854875-673d2d80-8900-11eb-877c-c6866767705a.png) 
![mediaInfo](https://user-images.githubusercontent.com/30437204/111854713-6e177080-88ff-11eb-9f05-29b8f69e1da7.png)  

Cover images are saved as poster.jpg inside the folder of the media.  
Scores alignment can be customized with [parameters](#aditional-parameters).  
After executing the script you have to update the library metadata on Emby/Plex/Jellyfin for this to take effect!

# Downloading
To download the latest executable of the script run:  
``` wget https://github.com/ilarramendi/Cover-Ratings/releases/download/0.3/CoverRatings; chmod +x CoverRatings```  
Also you can download the whole project and run the python script.


# Api key
To get the metadata / cover images this script uses [omdbapi](http://www.omdbapi.com/) to get a free api key visit [this](http://www.omdbapi.com/apikey.aspx) link.

To use the api key and save it for future use you can execute the script like this:  
 ```./CoverRatings '/Movies/*' -a apiKey```  
This only needs to be run once with the api key, as it will be stored inside ```config.json```

# Supported media folder names are:
Recommended: ```/media/Movie Name (year)``` or ```/media/Movie Name year```  
Working: ```/media/Movie Name```

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
***Use:*** ```./CoverRatings '/media/*'```

# Aditional Parameters
Parameters can be used without any particular order  
```-i``` Adds 4K and HDR logo to images (only works with movies ATM)  
```-vt``` Align scores on top  
```-hl``` Align scores to the left   
```-hr``` Align scores to the right  
```-b '#ff0000ff'``` Change background color (color can be a hex with 6 digits to set transparency, '#0000' for disabled)  
```-t '#000000ac'``` Change text color (color can be a hex with 6 digits to set transparency)  
```-s 3``` Set space between image and text  
```-a abc456``` Set and save the api key
```-o``` Overwrite existing covers

# Customization Examples
Bottom Center (default):    Top Right:          Top Center:  
![bottom-center](https://user-images.githubusercontent.com/30437204/111842780-bf633800-88de-11eb-9de3-4f10bf4a7c50.png) 
![top-right](https://user-images.githubusercontent.com/30437204/111842790-c427ec00-88de-11eb-9b4d-28ccbb221686.png) 
![top-center](https://user-images.githubusercontent.com/30437204/111842806-cab66380-88de-11eb-9184-a85ab43837ff.png)  
Bottom Left:         Bottom Right:  
![bottom-left](https://user-images.githubusercontent.com/30437204/111842814-cd18bd80-88de-11eb-9731-16d1f30dafa0.png) 
![bottom-right](https://user-images.githubusercontent.com/30437204/111842847-de61ca00-88de-11eb-9a74-1a70dd939645.png)  
