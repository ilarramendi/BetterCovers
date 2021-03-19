
# Cover Ratings
**This is still a WIP!**

Lightweight script intended to automaticaly generate cover images for Emby, Plex, Jellyfinn, etc. MOVIES library with RottenTomatoes, IMDB and Metascore ratings.

Cover images are saved as cover.jpg inside the same folder as the video file.

After executing the script you have to update the library metadata on emby/plex for this to take effect!

Bottom line width, text height, img height, text color and border color can be customized!

# Api key
To get the metadata / cover images this script uses [omdbapi](http://www.omdbapi.com/) to get a free api key visit [this](http://www.omdbapi.com/apikey.aspx) link.

To use the api key and save it for future use you can execute the script like this:  
 ```python3 CoverRatings.py '/Movies/*/*' apiKey```  
This only needs to be run once with the api key, as it will be stored inside ```config.json```

Alternatively you can create ```config.json``` located next to the script and save the api key like: ```{"apiKey": "value"}```
<br><br><br>
**Movie folder names should be like: ```Movie Name (year)``` !!!**  
# Usage
If movie library looks like this

```
/Movies
  ├── Movie1 (year)
  │      └── Movie1.mkv
  ├── Movie2 (year)
  │      └── Movie2.mp4 
  └──  ...
```
```python3 CoverRatings.py '/Movies/*/*'```

# Example
![Example](https://user-images.githubusercontent.com/30437204/111710427-70f36200-8828-11eb-9744-aafbcb71ea27.png)
