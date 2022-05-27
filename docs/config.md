# Config.json

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

## Agent (Automaticaly update library)
| Name           | Description                                        | Values                     |
| -------------- | -------------------------------------------------- | -------------------------- | 
| type           | Media agent to update                              | jellyfin or emby           |
| url            | Full path to media agent                           | http://192.168.1.7:8989    |
| apiKey         | Media agent api key                                | 123456456                  |

## Scraping
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

## Templates
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

