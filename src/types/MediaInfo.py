from subprocess import DEVNULL, call, getstatusoutput
from json import loads, dumps
from datetime import datetime, timedelta

from src.functions import log
class MediaInfo:
    def __init__(self):
        self.source = None
        self.languages = []
        self.color = 'SDR'
        self.codec = None
        self.resolution = None
    
    def toJSON(self):
        ret = {}
        for property in ['source', 'languages', 'color', 'codec', 'resolution']:
            ret[property] = getattr(self, property)
        return ret 

    def __str__(self):
        return dumps(self.toJSON(), indent=5, default=str)
    
    def update(self, metadata, defaultAudioLanguage, mediainfoUpdateInterval, ffprobe):
        if (datetime.now() - metadata.updates['mediaInfo']) > timedelta(days=mediainfoUpdateInterval):
            pt = metadata.path.translate({36: '\$'})
            cmd = f'{ffprobe} "{pt}"  -of json -show_entries stream=index,codec_type,codec_name,height,width:stream_tags=language -v quiet'
            cmd2 = f'{ffprobe} "{pt}"  -show_streams -v quiet'
            out = getstatusoutput(cmd)
            out2 = getstatusoutput(cmd2)
            
            # Source
            nm = metadata.path.lower()
            self.source = 'BR' if ('bluray' in nm or 'bdremux' in nm) else 'DVD' if 'dvd' in nm else 'WEBRIP' if 'webrip' in nm else 'WEBDL' if 'web-dl' in nm else None

            if out[0] != 0: return [[], [], [str(metadata.number)]] if metadata.type == 'episode' else log(f"Error getting media info for: {metadata.title}, exit code: {out[0]}\n Command: {cmd}", 3, 1)
            if out2[0] != 0: return [[], [], [str(metadata.number)]] if metadata.type == 'episode' else log(f"Error getting media info for: {metadata.title}, exit code: {out2[0]} \n Command: {cmd2}", 3, 1)
                
            # Get first video track
            video = False
            streams = loads(out[1])['streams']
            for s in streams:
                if s['codec_type'] == 'video':
                    video = s
                    break
            
            if not video: return [[], [], [str(metadata.number)]] if metadata.type == 'episode' else  log(f"Error getting media info, no video tracks found for: {metadata.title}", 3, 1)
            
            # Color space (HDR or SDR)
            self.color = 'HDR' if 'bt2020' in out2[1] else 'SDR'
            
            # Resolution
            self.resolution = 'UHD' if video['width'] >= 3840 else 'QHD' if video['width'] >= 2560 else 'HD' if video['width'] >= 1920 else 'SD'

            # Video codec
            if 'codec_name' in video:
                if video['codec_name'] in ['h264', 'avc']: self.codec = 'AVC'
                elif video['codec_name'] in ['h265', 'hevc']: self.codec = 'HEVC'
                else: log(f"Unsupported video codec: {video['codec_name'].upper()}", 2, 4)
            else: log(f"Video codec not found for: {video['codec_name'].upper()}", 2, 4)
            
            # Audio languages
            for s in streams:
                if s['codec_type'] == 'audio' and 'tags' in s and 'language' in s['tags'] and s['tags']['language'].upper() not in self.languages:
                    self.languages.append(s['tags']['language'].upper())
            if len(self.languages) == 0:
                if defaultAudioLanguage: self.languages = [defaultAudioLanguage]
            
            metadata.updates['mediaInfo'] = datetime.now()
            return [[str(metadata.number)], [], []] if metadata.type == 'episode' else log(f'Successfully updated Media Info for: "{metadata.title}"', 0, 2)
        else: 
            return [[], [str(metadata.number)], []] if metadata.type == 'episode' else log(f'No need to update Media Info for: "{metadata.title}"', 1, 4)