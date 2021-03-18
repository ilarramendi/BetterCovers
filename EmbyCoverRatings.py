from glob import glob
import re
import requests
from time import sleep
from PIL import Image, ImageFont, ImageDraw
from os import path
import json
import sys

brHeight = 40
imHeight = 30
txHeight = 26
rectangleColor = (25, 25, 25, int(255 * 0.8))
textColor = '#fcfcfc'
extensions = ['mp4', 'mkv']


if len(sys.argv) ==  3:
    with open('./config.json', 'w') as js: json.dump({'apiKey': sys.argv[2]}, js)
    apiKey = sys.argv[2]
else:
    with open('./config.json', 'r') as js: apiKey = json.load(js)['apiKey']

def downloadImage(url, path, retry):
    response = requests.get(url)
    i = 0
    while response.status_code != 200 and i < retry:
        sleep(1)
        response = requests.get(url)
        i += 1

    if response.status_code == 200:
        file = open(path, 'wb')
        file.write(response.content)
        file.close()
        return True
    else: 
        logText('Failed to download: ' + url, error = True)
        return False

files = []
for ex in extensions:
    files += glob(sys.argv[1] + '.' + ex)

i = 1
for file in files: 
    if not path.exists(file.rpartition('/')[0] + '/cover.jpg'):
        name, year = re.findall('\/([^\/]+)\((\d+)\)', file)[0]
        info = {}
        if name[-1] == ' ': name = name[:-1]
        
        response = requests.get('http://www.omdbapi.com/?apikey=' + apiKey + '&t=' + name.replace(' ', '+'))
        res = response.json()
        if response.status_code != 200 or 'Error' in res: print('No movies found: ' + name)
        else:
            if abs(int(year) - int(re.findall('\d{4}' ,res['Year'])[0])) > 1: print('Wrong movie found: ' + name + ' (' + year + ') | ' + res['Title'] + ' (' + res['Year'] + ')')
            else:  
                if 'Metascore' in res: info['mts'] = res['Metascore']
                if 'imdbRating' in res: info['imdb'] = res['imdbRating']
                for rt in res['Ratings']:
                    if rt['Source'] == 'Rotten Tomatoes':
                        info['rt'] = rt['Value']
                        break

                info2 = {}
                for inf in info:
                    if info[inf] != 'N/A': info2[inf] = info[inf]

                if len(info2) > 0 and 'Poster' in res and downloadImage(res['Poster'], 'cover.jpg', 3):
                    img = Image.open("cover.jpg").convert("RGBA")
                    overlay = Image.new('RGBA', img.size, (0,0,0,0))
                    ImageDraw.Draw(overlay).rectangle(((0, img.size[1] - brHeight), (img.size[0], img.size[1])), fill=rectangleColor)
                    img = Image.alpha_composite(img, overlay).convert("RGB") # Remove alpha for saving in jpg format.

                    font = ImageFont.truetype("Roboto-Medium.ttf", txHeight)
                    le = 300 // len(info2)
                    x = 0
                    space = 15 // len(info2)
                    draw = ImageDraw.Draw(img)
                    for rt in info2:
                        im = Image.open(rt + ".png")
                        tsize = draw.textsize(info2[rt], font)[0]
                        sp  = (le - im.size[0] - tsize - space) // 2
                        img.paste(im, (x + sp, img.size[1] - imHeight - (brHeight - imHeight) // 2), im)
                        draw.text((x + sp + im.size[0] + space, img.size[1] - txHeight - (brHeight - txHeight) // 2 - 1) , info2[rt], textColor, font=font)
                        x += le

                    img.save(file.rpartition('/')[0] + '/cover.jpg')
                    print('\033[92m' + 'Cover image saved for: ' + res['Title'] + '\033[0m')
                else: print('No ratings found or poster missing for movie: ' + res['Title'])
    