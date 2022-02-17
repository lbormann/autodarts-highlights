import os
import glob
from os import path
from pathlib import Path
import platform
import threading
import json
from datetime import date, datetime
from moviepy.editor import *
import unicodedata
import re

from flask import Flask, request, redirect, url_for, render_template, send_from_directory
app = Flask(__name__)

import cv2
import time
from ONVIFCameraControl import ONVIFCameraControl


VERSION = '0.9.0'
DEBUG = True
RECORD_FORMAT = ".avi"
CLIP_FORMAT = ".mp4"


def slugify(value, allow_unicode=False):
    """
    Taken from https://github.com/django/django/blob/master/django/utils/text.py
    Convert to ASCII if 'allow_unicode' is False. Convert spaces or repeated
    dashes to single dashes. Remove characters that aren't alphanumerics,
    underscores, or hyphens. Convert to lowercase. Also strip leading and
    trailing whitespace, dashes, and underscores.
    """
    value = str(value)
    if allow_unicode:
        value = unicodedata.normalize('NFKC', value)
    else:
        value = unicodedata.normalize('NFKD', value).encode('ascii', 'ignore').decode('ascii')
    value = re.sub(r'[^\w\s-]', '', value.lower())
    return re.sub(r'[-\s]+', '-', value).strip('-_')

def get_timestamp():
    return datetime.now().replace(microsecond=0)

def json_serial(obj):
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    raise TypeError ("Type %s not serializable" % type(obj))



class HighlightClipper(threading.Thread):
    def __init__(self, sounds_path, highlight_file, offset_before, offset_after):
        threading.Thread.__init__(self)
        
        self.__clip_format = CLIP_FORMAT
        self.__sounds_path = sounds_path
        self.__highlight_file = highlight_file
        self.__offset_before = offset_before
        self.__offset_after = offset_after
        self.__is_first_video_clip_of_array = True

    def run(self):
        with open(self.__highlight_file, 'r') as file:
            file_data = json.load(file)

            # Look for video-source that started most late
            latest_start_timestamp = self.__get_video_source_started_most_late(file_data["video-sources"])

            for hl in file_data["highlights"]:
                self.__is_first_video_clip_of_array = True
                self.__generate_highlight_clip(hl, file_data["video-sources"], latest_start_timestamp)

    def __date_time_from_iso_json(self, date_time_iso_json):
        return datetime.strptime(date_time_iso_json, "%Y-%m-%dT%H:%M:%S")

    def __get_video_source_started_most_late(self, vss):
        latest_vs = self.__date_time_from_iso_json(vss[0]['ts-start'])
        for vs in vss:
            c_vs = self.__date_time_from_iso_json(vs['ts-start'])
            if c_vs > latest_vs:
                latest_vs = c_vs
        return latest_vs

    def __find_sound_file(self, value):
        file_to_play = os.path.join(self.__sounds_path, str(value))
        if path.isfile(file_to_play + '.wav'):
            return file_to_play + '.wav'
        elif path.isfile(file_to_play + '.mp3'):
            return file_to_play + '.mp3'
        else:
            return None

    def __generate_highlight_clip(self, highlight, video_sources, latest_start_timestamp):
        
        # Generate array of video-sources, sorted by purpose, to compose one nice clip
        clips = []
        video_sources = sorted(video_sources, key=lambda d: d['purpose'])
        for vs in video_sources:
            clips.append(self.__generate_clip_of_video_source(highlight, vs, latest_start_timestamp))
        final_clip = clips_array([clips])

        # Get relevant vars
        highlight_started_timestamp = self.__date_time_from_iso_json(highlight['ts-start'])
        thrower = highlight['user']
        variant = highlight['variant']
        highlight_type = highlight['type']
        highlight_value = highlight['value']
        clip_file_name = slugify(str(highlight_started_timestamp).replace(":", "-") + "_" + thrower + "_" + variant + "_" + highlight_type + "_" + str(highlight_value))
            
        # Compose clip destination file-path
        clip_file_path = os.path.dirname(os.path.abspath(self.__highlight_file))
        clip_file_path = os.path.join(clip_file_path, clip_file_name + self.__clip_format)

        # .resize(width=480)
        # audio_codec='mp3'
        final_clip.write_videofile(clip_file_path)
        
        
    def __generate_clip_of_video_source(self, highlight, vs, latest_start_timestamp):           
        record_file_name = vs['file-name']
        record_started_timestamp = self.__date_time_from_iso_json(vs['ts-start'])
        diff = int((latest_start_timestamp - record_started_timestamp).total_seconds())

        # synchronize: diff to latest started video-source
        if diff != 0:
            diff = diff - 1.20

        highlight_started_timestamp = self.__date_time_from_iso_json(highlight['ts-start'])
        highlight_ended_timestamp = self.__date_time_from_iso_json(highlight['ts-end'])
        highlight_duration = int((highlight_ended_timestamp-highlight_started_timestamp).total_seconds())

        start_highlight_timestamp = int((highlight_started_timestamp-record_started_timestamp).total_seconds())
        
        start = start_highlight_timestamp - self.__offset_before + diff
        end = start_highlight_timestamp + highlight_duration + self.__offset_after + diff

        # TODO: Remove or repair
        # print('>>> ' + 'Highlight duration: ' + str(highlight_duration))
        # print('>>> ' + vs['name'] + ': Diff: ' + str(diff))
        # print('>>> ' + str(start))
        # print('>>> ' + str(end))

        video_source_name = vs['name']
        video_source_purpose = vs['purpose']
        video_source_invert = vs['invert-image']
        variant = highlight['variant']
        thrower = highlight['user']
        highlight_type = highlight['type']
        highlight_value = highlight['value']

        # try:

        clip = VideoFileClip(record_file_name)

        sounds = []
        if self.__is_first_video_clip_of_array == True:
            self.__is_first_video_clip_of_array = False

            # BACKGROUND-AUDIO
            background_sound_file = self.__find_sound_file('arena\\arena4')
            if background_sound_file != None:
                background_sound = AudioFileClip(background_sound_file)
                background_sound = afx.audio_loop(background_sound, duration = clip.duration)
                sounds.append(background_sound.set_start(start))
            else:
                self.__printv('Warning: background-sound-file not found, skip')

            # CALLER-AUDIO
            if highlight_type == 'Highscore':
                call_sound_file = self.__find_sound_file(highlight_value)
            elif highlight_type == 'Highfinish':
                call_sound_file = self.__find_sound_file('gameshot')

            if call_sound_file != None:
                call_sound = AudioFileClip(call_sound_file).volumex(4.0)
                tss = int((highlight_ended_timestamp-record_started_timestamp).total_seconds())
                go = tss + diff
                sounds.append(call_sound.set_start(go + 1.25))
            else:
                self.__printv('Warning: caller-sound-file not found, skip')


            # HITS-CROWD-AUDIO
            ouh_sound_file = self.__find_sound_file('arena\\Ouh_arena3')
            hit_sound_file = self.__find_sound_file('arena\\dartsboard1')

            if ouh_sound_file != None and hit_sound_file != None:
                ouh_sound = AudioFileClip(ouh_sound_file).volumex(2.0)
                hit_sound = AudioFileClip(hit_sound_file).volumex(4.0)

                # For each thrown dart
                for i, kp in enumerate(highlight['key-points']):
                    ts = self.__date_time_from_iso_json(kp['ts'])
                    tss = int((ts-record_started_timestamp).total_seconds())
                    go = tss + diff
                    
                    # Make deciding dart-reaction more loud
                    if i == (len(highlight['key-points']) - 1):
                        ouh_sound = ouh_sound.volumex(2.0) 

                    # Add dart-hit and crowd-reaction
                    sounds.append(hit_sound.set_start(go + 0.60))
                    sounds.append(ouh_sound.set_start(go + 0.85))
            else:
                self.__printv('Warning: ouh-sound-file or hit-sound-file not found, skip')


            # Add all audio parts to the clip
            clip = clip.set_audio(CompositeAudioClip(sounds))

        # Cut only highlight
        highlight_clip = clip.subclip(start, end)
        
        # Mirror image when needed
        if video_source_invert == True:
            highlight_clip = highlight_clip.fx(vfx.mirror_x)

        # Zoom slowly when video-source is watching player
        if video_source_purpose == 1:
            highlight_clip = highlight_clip.resize(lambda t : 1 + 0.06 * t)

        return highlight_clip
 
        # except:
        #      self.__printv('Clip-Generation failed')

    def __printv(self, msg, only_debug = False):
        if only_debug == False or (only_debug == True and DEBUG == True):
            print('>>> Highlight-clipper: ' + msg)


class VideoSource(threading.Thread):
    def __init__(self, config):
        threading.Thread.__init__(self)
        
        self.__config = config
        self.__record_started_timestamp = None
        self.__record_state = True
        self.__record_path =  self.__config['record-path']

        if "onvif-ptz-camera" in self.__config and self.__config["onvif-ptz-camera"] == True:
            self.__ptz_camera = ONVIFCameraControl((self.__config["onvif-ptz-camera-host"], self.__config["onvif-ptz-camera-port"]), self.__config["onvif-ptz-camera-user"], self.__config["onvif-ptz-camera-password"])
            # print(self.__ptz_camera.get_presets())
            self.move_ptz_camera()


    def run(self):
        cap = cv2.VideoCapture(self.__config['video-source'])

        w = int(cap.get(3))
        h = int(cap.get(4))
        fps = cap.get(cv2.CAP_PROP_FPS)

        if fps < 0.1 or fps > 60.0:
            fps = 30.0

        fourcc = cv2.VideoWriter_fourcc(*'XVID')
        # fourcc = cv2.VideoWriter_fourcc('M','J','P','G')

        self.__record_path = os.path.join(self.__record_path, slugify(self.__config['video-name']) + self.__config['record-format']) 
        out = cv2.VideoWriter(self.__record_path, fourcc, fps, (w, h))

        self.__printv('Recording started - ' + 'W: ' + str(w) + ' H: ' + str(h) + ' FPS: ' + str(fps) + ' - Record-path: ' + self.__record_path)
        self.__record_started_timestamp = get_timestamp()

        while self.__record_state == True:
            ret, frame = cap.read()
            if ret == True:
                out.write(frame)
            else:
                self.__printv('Can not read frame')
                break

        self.__printv('Recording stopped - ' + 'W: ' + str(w) + ' H: ' + str(h) + ' FPS: ' + str(fps) + ' - Record-path: ' + self.__record_path)

        cap.release()
        out.release()


    def stop_recording(self):
        self.__record_state = False

    def get_data(self):
        return {
            "name": self.__config['video-name'], 
            "purpose": self.__config['purpose'],
            "invert-image": self.__config['invert-image'],
            "ts-start": self.__record_started_timestamp,
            "file-name": self.__record_path
            }

    def move_ptz_camera(self):
        if "onvif-ptz-camera" in self.__config and self.__config['onvif-ptz-camera'] == True:
            self.__printv('Move PTZ-Camera')   
            self.__ptz_camera.goto_preset(self.__config['onvif-ptz-camera-preset'])

    def __printv(self, msg, only_debug = False):
        if only_debug == False or (only_debug == True and DEBUG == True):
            print('>>> Video-source (' + str(self.__config['video-name']) + '): ' + msg)


class AutodartsHighlights(threading.Thread):
    def __init__(self, config):  
        threading.Thread.__init__(self) 
        
        self.__config = config        
        self.__record_format = RECORD_FORMAT
        self.__vsis = []
        self.__record_path = None
        self.__record_state = False
        self.__highlight_files = set([])
        self.__turn_points = 0
        self.__tt1 = None
        self.__tt2 = None
        self.__tt3 = None
        self.__tv1 = None
        self.__tv2 = None
        self.__tv3 = None

        if self.__config['start-record-on-app-start'] == True:
            self.start_stop_recording()


    def get_record_path(self):
        return self.__config['record-path']

    def list_recordings(self):
        recordings = []

        records = os.listdir(self.__config['record-path'])
        records.sort()
        records.reverse()
        # self.__printv(os.path.join(self.__config['record-path'], clip), only_debug = True)

        for name in records:
            full_path_recording = os.path.join(self.__config['record-path'], name)
            if os.path.isdir(full_path_recording):

                clip_files = glob.glob(full_path_recording + "/*" + CLIP_FORMAT)   
                clip_files.sort(key = os.path.getmtime)
                clip_files.reverse()

                clips = []
                for c in clip_files:
                    print(c)
                    clip = {
                        "file": os.path.basename(c)
                    }
                    clips.append(clip)

                recording = {
                    "path": os.path.basename(full_path_recording),
                    "clips": clips
                }
                recordings.append(recording)

        return recordings

    def analyze_turn(self, turn_points): 
        # self.__reset_highlight_vars()
        # print('Turn ended, points: ' + str(turn_points))
        return

    def analyze_throw(self, thrower, throw_number, throw_points, points_left, busted, variant):
        throw_timestamp = get_timestamp()

        if self.__record_state == True:

            if busted == "False":
                throw_number = int(throw_number)
                throw_points = int(throw_points)
                points_left = int(points_left)

                self.__turn_points += throw_points

                if throw_number == 1:
                    self.__tt1 = throw_timestamp
                    self.__tv1 = throw_points
                elif throw_number == 2:
                    self.__tt2 = throw_timestamp
                    self.__tv2 = throw_points
                elif throw_number == 3:
                    self.__tt3 = throw_timestamp
                    self.__tv3 = throw_points

                self.__printv('Timestamp: ' + str(throw_timestamp), only_debug = True)
                self.__printv('Throw-number: ' + str(throw_number), only_debug = True)
                self.__printv('Turn-points: ' + str(self.__turn_points), only_debug = True)
                self.__printv('Points-left: ' + str(points_left), only_debug = True)   

                highlight_occured = self.__check_for_highlight_highfinish(variant, thrower, throw_number, points_left)
                if highlight_occured == False:
                    self.__check_for_highlight_highscore(variant, thrower, throw_number)
            
            if throw_number == 3 or busted == "True":
                self.__reset_highlight_vars()
        else:
            self.__printv('RECORDING IS CURRENTLY STOPPED. PLEASE START IT TO TRACK HIGHLIGHTS')
 

    def start_stop_recording(self):
        self.__record_state = not self.__record_state
        self.__record()

    def get_recording_state(self):
        return self.__record_state

    def __record(self):
        if self.__record_state == False:
            for vsi in self.__vsis:
                vsi.stop_recording()
                vsi.join()

            self.__vsis = []
            self.__generate_highlight_clips()

        else:   
            if self.__vsis != []:
                for vsi in self.__vsis:
                    vsi.stop_recording()
                    vsi.join()
                self.__vsis = []


            record_file_timestamp = get_timestamp()


            self.__record_path = os.path.join(self.__config['record-path'], str(record_file_timestamp).replace(":", "-"))
            if not os.path.exists(self.__record_path):
                try:
                    os.makedirs(self.__record_path)
                except:
                    self.__printv('Could not create record-path. Make sure the application has write permission')
                    return

            for vs in self.__config["video-sources"]:
                if vs['activate'] == True:
                    vs['record-path'] = self.__record_path
                    vs['record-format'] = self.__record_format
                    vsi = VideoSource(vs)
                    vsi.start()
                    self.__vsis.append(vsi)

    def __check_for_highlight_highfinish(self, variant, thrower, throw_number, points_left):
        if points_left == 0 and self.__turn_points >= self.__config["highlights-highfinish-on"]:
            self.__process_highlight(variant, thrower, "Highfinish")
            return True
        else:
            return False

    def __check_for_highlight_highscore(self, variant, thrower, throw_number):
        if throw_number == 3 and self.__turn_points >= self.__config["highlights-highscore-on"]:
            self.__process_highlight(variant, thrower, "Highscore")

    def __generate_key_point(self, x, tvx, ttx):
        tx = {
                "index": x,
                "value": tvx,
                "ts": ttx
            }
        return tx

    def __generate_key_points(self):
        key_points = []
        if self.__tv1 != None:
            key_points.append(self.__generate_key_point(1, self.__tv1, self.__tt1))
        if self.__tv2 != None:   
            key_points.append(self.__generate_key_point(2, self.__tv2, self.__tt2))
        if self.__tv3 != None:   
            key_points.append(self.__generate_key_point(3, self.__tv3, self.__tt3))
        return key_points

    def __get_ts_start_end(self, key_points):
        if len(key_points) == 3:
            return (self.__tt1, self.__tt3)
        if len(key_points) == 2:
            return (self.__tt1, self.__tt2)
        if len(key_points) == 1:
            return (self.__tt1, self.__tt1)

    def __reset_highlight_vars(self):
        self.__turn_points = 0
        self.__tt1 = None
        self.__tt2 = None
        self.__tt3 = None
        self.__tv1 = None
        self.__tv2 = None
        self.__tv3 = None

    def __process_highlight(self, variant, thrower, highlight_type):
        self.__printv('Boom ' + highlight_type + ': ' + thrower + ' - ' + str(self.__turn_points))

        key_points = self.__generate_key_points()
        (ts_start, ts_end) = self.__get_ts_start_end(key_points)

        new_highlight = {
            "type": highlight_type,
            "ts-start": ts_start,
            "ts-end": ts_end,
            "user": thrower,
            "value": self.__turn_points,
            "variant": variant,
            "average": 0.0,
            "manual": False,
            "key-points": key_points
        }

        highlights_path = os.path.join(self.__record_path, "highlights.json")
        if not os.path.exists(highlights_path):
            video_source_data = []
            for vsi in self.__vsis:
                video_source_data.append(vsi.get_data())

            first_data = {"video-sources": video_source_data, "highlights": [new_highlight]}

            with open(highlights_path, 'w') as outfile:
                json.dump(first_data, outfile, indent = 4, default=json_serial)
        else:
            with open(highlights_path, 'r+') as file:
                file_data = json.load(file)
                file_data["highlights"].append(new_highlight)
                file.seek(0)
                json.dump(file_data, file, indent = 4, default=json_serial)

        self.__highlight_files.add(highlights_path)

        for vsi in self.__vsis:
            vsi.move_ptz_camera()

    def __generate_highlight_clip(self, hlf):
        highlight_clipper = HighlightClipper(self.__config['clip-generation-sounds-path'], 
                                            hlf, 
                                            self.__config['highlights-time-offset-before'], 
                                            self.__config['highlights-time-offset-after'])
        highlight_clipper.start()

    def __generate_highlight_clips(self):
        for hlf in self.__highlight_files:
            self.__generate_highlight_clip(hlf)
        self.__highlight_files.clear()

    def __printv(self, msg, only_debug = False):
        if only_debug == False or (only_debug == True and DEBUG == True):
            print('>>> Autodarts-Highlights: ' + msg)






@app.route('/leg_started')
def leg_started():
    autodarts_highlights.start_stop_recording()
    return "200"

@app.route('/leg_ended')
def leg_ended():
    # autodarts_highlights.start_stop_recording()
    return "200"

@app.route('/throw/<thrower>/<throw_number>/<throw_points>/<points_left>/<busted>/<variant>')
def throw(thrower, throw_number, throw_points, points_left, busted, variant):
    autodarts_highlights.analyze_throw(thrower, throw_number, throw_points, points_left, busted, variant)
    return "200"

@app.route('/turn/<turn_points>')
def turn(turn_points):
    autodarts_highlights.analyze_turn(turn_points)
    return "200"

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        autodarts_highlights.start_stop_recording()
        return redirect(request.referrer)
        
    is_recording = autodarts_highlights.get_recording_state()
    recordings = autodarts_highlights.list_recordings()

    return render_template('index.html', recording = is_recording, recordings = recordings)

@app.route('/clips/<record_id>/<clip_id>', methods=['GET'])
def clips(record_id, clip_id):
    return send_from_directory(os.path.join(autodarts_highlights.get_record_path(), record_id), clip_id)
   
    



if __name__ == "__main__":
    with open("config.json") as json_data_file:
        config = json.load(json_data_file)

    osType = platform.system()
    osName = os.name
    osRelease = platform.release()
    print('\r\n')
    print('##########################################')
    print('       WELCOME TO AUTODARTS-HIGHLIGHTS')
    print('##########################################')
    print('VERSION: ' + VERSION)
    print('RUNNING OS: ' + osType + ' | ' + osName + ' | ' + osRelease)
    print('\r\n')

    autodarts_highlights = AutodartsHighlights(config = config)
    autodarts_highlights.start()

    app.run(host = config['host'] , port = config['port'])

    autodarts_highlights.close()
    print("Stop Autodarts-Highlights requested")
    autodarts_highlights.join()
    print("Autodarts-Highlights stopped")