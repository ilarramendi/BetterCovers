# Covers.json

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