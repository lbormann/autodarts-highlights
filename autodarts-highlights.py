import os
import glob
from os import path
import random
import uuid
import platform
import threading
import json
from datetime import date, datetime
from moviepy.editor import *
import unicodedata
import re
import cv2
from ONVIFCameraControl import ONVIFCameraControl
from flask import Flask, request, redirect, url_for, render_template, send_from_directory
app = Flask(__name__)
import logging
log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)



VERSION = '0.9.0'
DEBUG = True
RECORD_FORMAT = ".avi"
CLIP_FORMAT = ".mp4"
HIGHLIGHTS_FILE_NAME = "highlights.json"
SOUNDS_FOLDER_BACKGROUND = "background"
SOUNDS_FOLDER_HIT = "hit"
SOUNDS_FOLDER_CROWD = "crowd"
SOUNDS_FOLDER_CALLER = "caller"




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
    return datetime.now()

def get_date_time_from_iso_json(date_time_iso_json):
    return datetime.strptime(date_time_iso_json, "%Y-%m-%dT%H:%M:%S.%f")

def json_serial(obj):
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    raise TypeError ("Type %s not serializable" % type(obj))

def get_clip_file_name(highlight_json):
    highlight_started_timestamp = get_date_time_from_iso_json(highlight_json['ts-start'])
    thrower = highlight_json['user']
    variant = highlight_json['variant']
    highlight_type = highlight_json['type']
    highlight_value = highlight_json['value']
    return slugify(str(highlight_started_timestamp).replace(":", "-") + "_" + thrower + "_" + variant + "_" + highlight_type + "_" + str(highlight_value))

def get_available_sounds(p):
    # TODO: remove constant wav, mp3
    sounds = []
    for file in os.listdir(p):
        if file.endswith(".wav") or file.endswith(".mp3") or file.endswith(".aiff"):
            sounds.append(os.path.join(p, file))
    return sounds

def get_available_dirs(p):
    return [d for d in os.listdir(p) if os.path.isdir(os.path.join(p, d))]

def get_sounds_background(sounds_path):
    return get_available_sounds(os.path.join(sounds_path, SOUNDS_FOLDER_BACKGROUND))
    
def get_caller(sounds_path):
    return get_available_dirs(os.path.join(sounds_path, SOUNDS_FOLDER_CALLER))

def get_sounds_hit(sounds_path):
    return get_available_sounds(os.path.join(sounds_path, SOUNDS_FOLDER_HIT))

def get_sounds_crowd(sounds_path):
    return get_available_sounds(os.path.join(sounds_path, SOUNDS_FOLDER_CROWD))

def normalize_random_choice(li):
    if li == []:
        return None
    else:
        random.choice(li)

def get_random_clip_vars(
                  z_min, z_max,
                  bg_list, bg_volume_min, bg_volume_max, bg_speed_min, bg_speed_max,
                  cl_list, cl_volume_min, cl_volume_max, cl_delay_after_highlight_min, cl_delay_after_highlight_max,
                  h_list, h_volume_min, h_volume_max,
                  cr_list, cr_volume_min, cr_volume_max, cr_delay_after_hit_min, cr_delay_after_hit_max, cr_last_dart_volume_min, cr_last_dart_volume_max):
    
    zoom = random.uniform(z_min, z_max)
    bg_file = normalize_random_choice(bg_list)
    bg_volume = random.uniform(bg_volume_min, bg_volume_max)
    bg_speed = random.uniform(bg_speed_min, bg_speed_max)
    cl_folder = normalize_random_choice(cl_list)
    cl_volume = random.uniform(cl_volume_min, cl_volume_max)
    cl_delay_after_highlight = random.uniform(cl_delay_after_highlight_min, cl_delay_after_highlight_max)
    h_file = normalize_random_choice(h_list)
    h_volume = random.uniform(h_volume_min, h_volume_max)
    cr_file = normalize_random_choice(cr_list)
    cr_volume = random.uniform(cr_volume_min, cr_volume_max)
    cr_delay_after_hit = random.uniform(cr_delay_after_hit_min, cr_delay_after_hit_max)
    cr_last_dart_volume = random.uniform(cr_last_dart_volume_min, cr_last_dart_volume_max)

    random_clip_vars = {
        "video-source": {
            "zoom": zoom
        },
        "background": {
            "file": bg_file,
            "volume": bg_volume,
            "speed": bg_speed
        },
        "caller": {
            "folder": cl_folder,
            "volume": cl_volume,
            "delay-after-highlight": cl_delay_after_highlight
        },
        "hit": {
            "file": h_file,
            "volume": h_volume
        },
        "crowd": {
            "file": cr_file,
            "volume": cr_volume,
            "delay-after-hit": cr_delay_after_hit,
            "last-dart-volume": cr_last_dart_volume
        }
    }
    return random_clip_vars


class HighlightClipper(threading.Thread):
    def __init__(self, 
    highlight_file, 
    sounds_path, 
    offset_before, 
    offset_after, 
    clip_id = None, 
    custom_value = None,
    clip_vars = None
    ):

        threading.Thread.__init__(self)
        
        self.__clip_format = CLIP_FORMAT
        self.__sounds_path = sounds_path
        self.__highlight_file = highlight_file
        self.__offset_before = offset_before
        self.__offset_after = offset_after
        self.__is_first_video_clip_of_array = True
        self.__clip_id = clip_id
        self.__clip_vars = clip_vars
        self.__custom_value = custom_value

    def run(self):

        # Process single, specific highlight
        highlight_to_process = None
        if self.__clip_id != None and self.__custom_value != None:
            with open(self.__highlight_file) as file:
                file_data = json.load(file)

                # Find the corresponding highlight
                for hl in file_data["highlights"]:
                    if (get_clip_file_name(hl) + CLIP_FORMAT) == self.__clip_id:
                        hl['value'] = int(self.__custom_value)
                        highlight_to_process = hl
                        break

            with open(self.__highlight_file, 'w') as f:
                json.dump(file_data, f, indent = 4, default = json_serial)


        with open(self.__highlight_file, 'r') as file:
            file_data = json.load(file)

            # Look for video-source that started most late
            latest_start_timestamp = self.__get_video_source_started_most_late(file_data["video-sources"])

            # Process single, specific highlight
            if highlight_to_process != None:
                self.__is_first_video_clip_of_array = True
                self.__generate_highlight_clip(highlight_to_process, file_data["video-sources"], latest_start_timestamp)

            # Process all highlights of recording
            else:
                printv(str(len(file_data["highlights"])) + ' HIGHLIGHTS TO PROCESS')
                for hl in file_data["highlights"]:
                    self.__is_first_video_clip_of_array = True
                    self.__generate_highlight_clip(hl, file_data["video-sources"], latest_start_timestamp)

    def __get_video_source_started_most_late(self, vss):
        latest_vs = get_date_time_from_iso_json(vss[0]['ts-start'])
        for vs in vss:
            c_vs = get_date_time_from_iso_json(vs['ts-start'])
            if c_vs > latest_vs:
                latest_vs = c_vs
        return latest_vs

    def __find_caller_sound(self, caller_folder, filename):
        joins = [self.__sounds_path, SOUNDS_FOLDER_CALLER, str(caller_folder), str(filename)]
        file_to_play = os.path.join(*joins)
        # TODO: Remove constants
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

        clip_file_name = get_clip_file_name(highlight)
            
        # Compose clip destination file-path
        clip_file_path = os.path.dirname(os.path.abspath(self.__highlight_file))
        clip_file_path = os.path.join(clip_file_path, clip_file_name + self.__clip_format)

        # .resize(width=480)
        # audio_codec='mp3'
        final_clip.write_videofile(clip_file_path)
        
        
    def __generate_clip_of_video_source(self, highlight, vs, latest_start_timestamp):           
        record_file_name = vs['file-name']
        record_started_timestamp = get_date_time_from_iso_json(vs['ts-start'])

        # synchronize: diff to latest started video-source
        diff = (latest_start_timestamp - record_started_timestamp).total_seconds()
        delay = vs['delay']

        highlight_started_timestamp = get_date_time_from_iso_json(highlight['ts-start'])
        highlight_ended_timestamp = get_date_time_from_iso_json(highlight['ts-end'])
        highlight_duration = (highlight_ended_timestamp - highlight_started_timestamp).total_seconds()

        start_highlight_timestamp = (highlight_started_timestamp - record_started_timestamp).total_seconds()
        
        start = start_highlight_timestamp - self.__offset_before - diff + delay
        end = start_highlight_timestamp + highlight_duration + self.__offset_after + delay

        # TODO: Remove or repair
        print('>>> ' + 'Highlight duration: ' + str(highlight_duration))
        print('>>> ' + vs['name'] + ': Diff: ' + str(diff))
        print('>>> ' + str(start))
        print('>>> ' + str(end))

        video_source_purpose = vs['purpose']
        highlight_type = highlight['type']
        highlight_value = highlight['value']

        v = self.__clip_vars
        if self.__clip_vars == None:
            v = get_random_clip_vars(z_min = 0.03, 
                                    z_max = 0.09,
                                    bg_list = get_sounds_background(self.__sounds_path), 
                                    bg_volume_min = 0.5, 
                                    bg_volume_max = 0.5, 
                                    bg_speed_min = 0.8, 
                                    bg_speed_max = 1.2,
                                    cl_list = get_caller(self.__sounds_path), 
                                    cl_volume_min = 2.0, 
                                    cl_volume_max = 4.0, 
                                    cl_delay_after_highlight_min = 0.5, 
                                    cl_delay_after_highlight_max = 0.9,
                                    h_list = get_sounds_hit(self.__sounds_path), 
                                    h_volume_min = 4.0, 
                                    h_volume_max = 5.0,
                                    cr_list = get_sounds_crowd(self.__sounds_path), 
                                    cr_volume_min = 1.5, 
                                    cr_volume_max = 2.2, 
                                    cr_delay_after_hit_min = 0.6, 
                                    cr_delay_after_hit_max = 1.3, 
                                    cr_last_dart_volume_min = 1.1,
                                    cr_last_dart_volume_max = 1.3)


        # try:

        clip = VideoFileClip(record_file_name)

        sounds = []
        if self.__is_first_video_clip_of_array == True:
            self.__is_first_video_clip_of_array = False

            # BACKGROUND-AUDIO
            bg = v['background']
            background_sound_file = bg['file']
            if background_sound_file != None:
                background_sound = AudioFileClip(background_sound_file)
                background_sound = afx.audio_loop(background_sound, duration = clip.duration)
                sounds.append(background_sound.set_start(start))
            else:
                self.__printv('Warning: background-sound-file not found, skip')


            # HITS-CROWD-AUDIO
            cr = v['crowd']
            h = v['hit']
            ouh_sound_file = cr['file']
            hit_sound_file = h['file']

            if ouh_sound_file != None and hit_sound_file != None:
                ouh_sound = AudioFileClip(ouh_sound_file).volumex(cr['volume'])
                hit_sound = AudioFileClip(hit_sound_file).volumex(h['volume'])

                # For each thrown dart
                for i, kp in enumerate(highlight['key-points']):
                    ts = get_date_time_from_iso_json(kp['ts'])
                    # + self.__offset_before - diff - delay
                    tss = (ts - record_started_timestamp).total_seconds() + delay

                    # Make deciding dart-reaction more loud
                    if i == (len(highlight['key-points']) - 1):
                        ouh_sound = ouh_sound.volumex(cr['last-dart-volume']) 

                    # Add dart-hit and crowd-reaction
                    sounds.append(hit_sound.set_start(tss))
                    sounds.append(ouh_sound.set_start(tss + cr['delay-after-hit']))
            else:
                self.__printv('Warning: ouh-sound-file or hit-sound-file not found, skip')


            # CALLER-AUDIO
            cl = v['caller']
            if highlight_type == 'Highscore':
                call_sound_file = self.__find_caller_sound(cl['folder'], highlight_value)
            elif highlight_type == 'Highfinish':
                call_sound_file = self.__find_caller_sound(cl['folder'], 'gameshot')

            if call_sound_file != None:
                call_sound = AudioFileClip(call_sound_file).volumex(cl['volume'])
                tss = int((highlight_ended_timestamp - record_started_timestamp).total_seconds() + self.__offset_before)
                tss = tss + cl['delay-after-highlight']

                sounds.append(call_sound.set_start(tss))
            else:
                self.__printv('Warning: caller-sound-file not found, skip')


            if sounds != []:
                # Add all audio parts to the clip
                clip = clip.set_audio(CompositeAudioClip(sounds))

        # Cut only highlight
        highlight_clip = clip.subclip(start, end)
    

        # Zoom slowly when video-source is watching player
        if video_source_purpose == 1:
            zoom = v['video-source']['zoom']
            highlight_clip = highlight_clip.resize(lambda t : 1 + zoom * t)

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

        # fourcc = cv2.VideoWriter_fourcc(*'XVID')
        fourcc = cv2.VideoWriter_fourcc('M','J','P','G')

        self.__record_path = os.path.join(self.__record_path, slugify(self.__config['video-name']) + self.__config['record-format']) 
        out = cv2.VideoWriter(self.__record_path, fourcc, fps, (w, h))

        self.__printv('Recording started - ' + 'W: ' + str(w) + ' H: ' + str(h) + ' FPS: ' + str(fps) + ' - Record-path: ' + self.__record_path)
        
        ret, frame = cap.read()
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
            "delay": self.__config['delay'],
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
            self.start_stop_recording(only_start = True)


    def get_record_path(self):
        return self.__config['record-path']

    def list_recordings(self):
        recordings = []

        if self.__record_state == False:
            records = os.listdir(self.__config['record-path'])
            records.sort()
            records.reverse()

            for name in records:
                full_path_recording = os.path.join(self.__config['record-path'], name)
                if os.path.isdir(full_path_recording):

                    # If there is no structure-json skip this recording
                    highlights_structure_path = os.path.join(full_path_recording, HIGHLIGHTS_FILE_NAME)
                    if path.exists(highlights_structure_path) == False:
                        continue

                    # Generate possible names for highlight-clip-filenames
                    clips_possible = []
                    with open(highlights_structure_path, 'r') as file:
                        highlights = json.load(file)
                        highlights_raw = highlights["highlights"]

                        for h in highlights_raw:
                            clips_possible.append((get_clip_file_name(h), h))
                        
                        clips_possible.sort()
                        clips_possible.reverse()

                    # Check which clips are already generated > create array of clips
                    clips = []
                    for (c, h) in clips_possible:
                        clip_file_name = os.path.join(full_path_recording, c + CLIP_FORMAT)
        
                        clip = {
                            "exists": path.exists(clip_file_name),
                            "file": os.path.basename(clip_file_name),
                            "value": h['value'],
                            "type": h['type'],  
                            "user": h['user'],  
                            "variant": h['variant']
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
 

    def start_stop_recording(self, only_start = False):
        if only_start == True:
            self.__record_state = True
        else:
            self.__record_state = not self.__record_state
        self.__record()

    def generate_clip_manual(self, record_id, clip_id, custom_value):
        path_joins = [self.__config['record-path'], record_id, HIGHLIGHTS_FILE_NAME]
        structure_file_path = os.path.join(*path_joins)

        highlight_clipper = HighlightClipper(structure_file_path, 
                                            self.__config['sounds-path'], 
                                            self.__config['highlights-time-offset-before'], 
                                            self.__config['highlights-time-offset-after'],
                                            clip_id = clip_id, 
                                            custom_value = custom_value)
        highlight_clipper.start()

    def get_recording_state(self):
        return self.__record_state

    def __record(self):
        if self.__record_state == False:
            for vsi in self.__vsis:
                vsi.stop_recording()
                vsi.join()

            self.__vsis = []
            self.__generate_open_highlights_of_recordings()

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

        highlights_path = os.path.join(self.__record_path, HIGHLIGHTS_FILE_NAME)
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

        # for vsi in self.__vsis:
        #     vsi.move_ptz_camera()

    def __generate_open_highlights_of_recording(self, hlf):
        highlight_clipper = HighlightClipper(hlf, 
                                            self.__config['sounds-path'], 
                                            self.__config['highlights-time-offset-before'], 
                                            self.__config['highlights-time-offset-after'])
        highlight_clipper.start()

    def __generate_open_highlights_of_recordings(self):
        for hlf in self.__highlight_files:
            self.__generate_open_highlights_of_recording(hlf)
        self.__highlight_files.clear()

    def __printv(self, msg, only_debug = False):
        if only_debug == False or (only_debug == True and DEBUG == True):
            print('>>> Autodarts-Highlights: ' + msg)






@app.route('/leg_started')
def leg_started():
    # autodarts_highlights.start_stop_recording(only_start = True)
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
        form = request.form
        record_id = form.get("record_id")
        clip_id = form.get("clip_id")
        custom_value = form.get("custom_value")

        if record_id != None and record_id != "" and clip_id != None and clip_id != "":
            autodarts_highlights.generate_clip_manual(record_id, clip_id, custom_value)
        else:
            autodarts_highlights.start_stop_recording()

        return redirect(request.referrer)
        
    is_recording = autodarts_highlights.get_recording_state()
    recordings = autodarts_highlights.list_recordings()

    return render_template('index.html', recording = is_recording, recordings = recordings, unique = str(uuid.uuid1()))

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