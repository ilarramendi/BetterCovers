from functions import log
from datetime import datetime, timedelta
from subprocess import DEVNULL, call, getstatusoutput
from json import loads, dumps

from functions import log


class MediaInfo:
    source = None
    languages = []
    color = 'SDR'
    codec = None
    resolution = None
    
    def toJSON(self):
        ret = {}
        for property, value in vars(self).items():
            ret[property] = value
        return ret 

    def __str__(self):
        return dumps(self.toJSON(), indent=5, default=str)

    def toTask(self, config):
        tsk = {}
        
        # Add enabled mediainfo properties
        for property, value in vars(self).items():
            if property != 'languages' and value and config[property][value]: tsk[property] = value
        
        # Add first selected language found
        for lg in config['audio'].split(','):
            if lg in self.languages:
                tsk['language'] = lg
                break
        
        # Replaces UHD and HDR for UHD-HDR if enabled
        if 'color' in tsk and 'resolution' in tsk:
            if tsk['color'] == 'HDR' and tsk['resolution'] == 'UHD' and config['color']['UHD-HDR']:
                tsk['color'] = 'UHD-HDR'
                del tsk['resolution']
        
        return tsk
    
    def update(self, metadata, defaultAudioLanguage, mediainfoUpdateInterval):
        if (datetime.now() - metadata.updates['mediaInfo']) > timedelta(days=mediainfoUpdateInterval):
            cmd = 'ffprobe "' + metadata.path.translate({36: '\$'}) + '" -of json -show_entries stream=index,codec_type,codec_name,height,width:stream_tags=language -v quiet'
            cmd2 = 'ffprobe "' + metadata.path.translate({36: '\$'}) + '" -show_streams -v quiet'
            out = getstatusoutput(cmd)
            out2 = getstatusoutput(cmd2)
            
            # Source
            nm = metadata.path.lower()
            metadata.media_info.source = 'BR' if ('bluray' in nm or 'bdremux' in nm) else 'DVD' if 'dvd' in nm else 'WEBRIP' if 'webrip' in nm else 'WEBDL' if 'web-dl' in nm else None

            if out[0] != 0: return log('Error getting media info for: "' + metadata.title + '", exit code: ' + str(out[0]) + '\n Command: ' + cmd, 3, 1)
            if out2[0] != 0: return log('Error getting media info for: "' + metadata.title + '", exit code: ' + str(out2[0]) + '\n Command: ' + cmd2, 3, 1)
                
            # Get first video track
            video = False
            streams = loads(out[1])['streams']
            for s in streams:
                if s['codec_type'] == 'video':
                    video = s
                    break
            
            if not video: return log('Error getting media info, no video tracks found for: ' + metadata.title, 3, 1)
            
            # Color space (HDR or SDR)
            metadata.media_info.color = 'HDR' if 'bt2020' in out2[1] else 'SDR'
            
            # Resolution
            metadata.media_info.resolution = 'UHD' if video['width'] >= 3840 else 'QHD' if video['width'] >= 2560 else 'HD' if video['width'] >= 1920 else 'SD'

            # Video codec
            if 'codec_name' in video:
                if video['codec_name'] in ['h264', 'avc']: metadata.media_info.codec = 'AVC'
                elif video['codec_name'] in ['h265', 'hevc']: metadata.media_info.codec = 'HEVC'
                else: log('Unsupported video codec: ' + video['codec_name'].upper(), 2, 4)
            else: log('Video codec not found for: ' + metadata.title, 2, 4)
            
            # Audio languages
            for s in streams:
                if s['codec_type'] == 'audio' and 'tags' in s and 'language' in s['tags'] and s['tags']['language'].upper() not in metadata.media_info.languages:
                    metadata.media_info.languages.append(s['tags']['language'].upper())
            if len(metadata.media_info.languages) == 0:
                if defaultAudioLanguage: metadata.media_info.languages = [defaultAudioLanguage]
                log('No audio lenguage found for: ' + metadata.title, 2, 4)
            
            metadata.updates['mediaInfo'] = datetime.now()
        else: return log('No need to update Media Info for: ' + metadata.title, 1, 3)
