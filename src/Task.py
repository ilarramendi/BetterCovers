from datetime import datetime
import json
from hashlib import md5
from os.path import join, exists
from subprocess import call, getstatusoutput
from time import time
from exif import Image as exifImage


from functions import log

class Task:
    def __init__(self, image, type, title, template, useExistingImage):
        self.image = image
        self.type = type
        self.title = title
        self.template = template
        self.use_existing_image = useExistingImage
        self.out = []
        self.media_info = {}
        self.ratings = {}
        self.certifications = []
        self.production_companies = []
        self.age_rating = None
        self.hash = ''
    
    def toString(self, removeOut):
        stri = "{\n"
        for property, value in vars(self).items():
            if not removeOut or property != "out":
                try:
                    stri += "\t" + str(property) + ": " + json.dumps(value, indent=5, default=str).replace("\n", "\n\t") + ",\n"
                except:
                    stri += "\t" + str(property) + ": " + str(value) + ",\n"
        stri += '}\n'
        return stri

    def __str__(self):
        return self.toString(False)

    def getHash(self):
        self.hash = md5(self.toString(True).encode('utf8')).hexdigest() # TODO check this since toString changed in task
        return self.hash
    
    def process(self, thread, workDirectory, wkhtmltoimage):
        st = time()
        # TODO image generation
        try:
            with open(join(workDirectory, 'media', 'templates', self.template + '.html')) as html:
                HTML = html.read()
        except:
            log('Error opening: ' + join(workDirectory, 'media', 'templates', self.template + '.html'), 3, 1)
            return False
        
        for rt in self.ratings:
            stri = '<div class="ratingContainer ' + rt + '"><img src="' + join('..', 'media', 'ratings', self.ratings[rt]['icon']) + '.png" class="ratingIcon"/><label class="ratingText">' + self.ratings[rt]['value'] + '</label></div>'
            HTML = HTML.replace('<!--' + rt + '-->', stri)
        for mi in self.media_info:
            stri = '<div class="mediaInfoImgContainer ' + mi + '"><img src="' + join('..', 'media/mediainfo', self.media_info[mi] + '.png') + '" class="mediainfoIcon"></div>'
            HTML = HTML.replace('<!--' + mi + '-->', stri)
        
        pcs = ''
        for pc in self.production_companies:
            pcs += "<div class='pcWrapper producionCompany-" + str(pc['id']) +  "'><img src='" + pc['logo'] + "' class='producionCompany'/></div>\n\t\t\t\t"
        HTML = HTML.replace('<!--PRODUCTIONCOMPANIES-->', pcs)
        
        # TODO change this to be like the others
        cert = ''
        for cr in self.certifications:
            cert += '<img src= "' + join('..', 'media', 'ratings', cr + '.png') + '" class="certification"/>'
        HTML = HTML.replace('<!--CERTIFICATIONS-->', cert)
        
        if self.age_rating: # Grabs age ratings svg file
            with open(join(workDirectory, 'media', 'ageRatings', self.age_rating + '.svg'), 'r') as svg:
                HTML = HTML.replace('<!--AGERATING-->', svg.read())
        
        HTML = HTML.replace('$IMGSRC', self.image) # TODO fix for image generation here
        HTML = HTML.replace('<!--TITLE-->', self.title)

        # Write new html file to disk
        with open(join(workDirectory, 'threads', thread + '.html'), 'w') as out:
            out.write(HTML)

        # Generate image
        i = 0
        command = wkhtmltoimage + ' --cache-dir "' + join(workDirectory, 'cache') + '" --enable-local-file-access  "file://' + join(workDirectory, 'threads', thread + '.html') + '" "' + join(workDirectory, 'threads', thread + '.jpg') + '"'
        out = getstatusoutput(command)
        if out[0] == 0:
            imgSrc = join(workDirectory, 'threads', thread + '.jpg')

            # Tag image
            with open(imgSrc, 'rb') as image: img = exifImage(image)
            img["software"] = "BetterCovers:" + self.hash
            img['datetime_original'] = datetime.now().strftime("%m/%d/%Y %H:%M:%S")
            with open(imgSrc, 'wb') as image: image.write(img.get_file())

            # Copy to final location
            for fl in self.out:
                cm = call(['cp', '-f', imgSrc, fl])
                if cm != 0:
                    log('Error moving to: ' + fl, 3, 1)
                    return False  
            log('Succesfully generated ' + ('cover' if self.type != 'backdrop' else 'backdrop') + ' image for: ' + self.title + ' in ' + str(round(time() - st)) + 's', 0, 1)
            return True 
        else: 
            log('Error with wkhtmltoimage for: ' + self.title + '\n' + out[1], 3, 1)
            return False
        
        log('Error generating image for: ' + self.title, 3, 1)
        return False

    @staticmethod
    def getFileHash(file):
        try:
            with open(file, 'rb') as image:
                img = exifImage(image)
                if img.has_exif and 'software' in img.list_all() and 'BetterCovers:' in img['software']:
                    return img['software'].split(':')[1]
        except: pass
        
        return ''

    @staticmethod
    def generateTask(type, metadata, overwrite, config, templates):
        img = metadata.path  # Extract images from media file TODO fix image extraction
        if not(type in ['episode', 'backdrop'] and config['extractImage']):
            imgType = 'covers' if type != 'backdrop' else 'backdrops' 

            if len(metadata.images[imgType]) == 0: 
                log('Missing ' + imgType[:-1] + ' image for: ' + metadata.title, 3, 3)
                return []
            else: img = metadata.images[imgType][0]['src'] # TODO add some option to choose this (probably web ui)
        
        tsk = Task(img, type, metadata.title, metadata.getTemplate(templates, type == 'backdrop'), config['useExistingImage'])
        # Adds configured mediainfo properties to task
        tsk.media_info = metadata.media_info.toTask(config['mediaInfo'])

        # Adds configured ratings to the task 
        for rt in metadata.ratings:
            if config['ratings'][rt]: 
                rating = metadata.ratings[rt]
                tsk.ratings[rt] = {'value': rating['value'], 'icon': rating['icon']} # TODO calculate icon instead of store
                if config['usePercentage']:
                    tsk.ratings[rt] = str(int(float(tsk.ratings[rt]) * 10)) + '%'
        
        # Adds configured certifications
        for cr in metadata.certifications:
            if config['certifications'][cr]: tsk.certifications.append(cr)

        # Adds age rating if enabled
        if config['ageRatings'][metadata.ageRating]: tsk.age_rating = metadata.age_rating
        
        # Adds enabled production companies
        for pc in metadata.production_companies:
            if config['productionCompaniesBlacklist']:
                if pc['id'] not in config['productionCompanies']: tsk.production_companies.append(pc)
            elif pc['id'] in config['productionCompanies']: tsk.production_companies.append(pc)
        
        # TODO Check this
        path = metadata.path if metadata.type in ['season', 'tv'] else metadata.path.rpartition('/')[0]
        name = metadata.path.rpartition('/')[2] if metadata.type in ['season', 'tv'] else metadata.path.rpartition('/')[2].rpartition('.')[0]
        for pt in [join(path, pt) for pt in config['output'].replace('$NAME', name).split(';')]:
            # Add paths to for images to generate if file dosnt exist, overwrite or automatic and hash different
            if not exists(pt) or overwrite: tsk.out.append(pt)
            elif tsk.getHash() != Task.getFileHash(pt): tsk.out.append(pt)
            else: log('No need to update image in: "' + pt + '"', 1, 3)

        return [tsk]