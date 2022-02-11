import os
import threading
import json
from datetime import datetime
from moviepy.editor import VideoFileClip

from flask import Flask
app = Flask(__name__)

import cv2
import time
from ONVIFCameraControl import ONVIFCameraControl



class AutodartsHighlights(threading.Thread):
    def __init__(self, config):   
        self.__config = config

        self.__video_source = config["video-source"]
        self.__video_source_fps = config["video-source-fps"]
        self.__video_source_width = config["video-source-width"]
        self.__video_source_height = config["video-source-height"]
        self.__record_format = ".avi"
        self.__record_path = config["record-path"]

        if not os.path.exists(self.__record_path):
            os.makedirs(self.__record_path)

        self.__onvif_ptz_camera = config["onvif-ptz-camera"]
        if self.__onvif_ptz_camera == True:
            self.__ptz_camera = ONVIFCameraControl((config["onvif-ptz-camera-host"], config["onvif-ptz-camera-port"]), config["onvif-ptz-camera-user"], config["onvif-ptz-camera-password"])
            self.__onvif_ptz_camera_preset_default = config["onvif-ptz-camera-preset-default"]
            self.__onvif_ptz_camera_preset_zoom_triple_20 = config["onvif-ptz-camera-preset-zoom"]
            # print(self.__ptz_camera.get_presets())
        
        self.__highlight_highscore_on = config["highlights-highscore-on"]
        self.__highlight_highfinish_on = config["highlights-highfinish-on"]
        self.__highlight_time_offset_before = config["highlights-time-offset-before"]
        self.__highlight_time_offset_after = config["highlights-time-offset-after"]
        self.__highlight_started_timestamp = None
        self.__highlight_turn_points = 0
        self.__highlight_turn_throw_number = 0

        self.__record_state = False
        self.__record_started_timestamp = None
        self.__record_output = None

        threading.Thread.__init__(self)


    def record(self):
        if self.__record_state == False:
            self.__set_ptz_camera_default()
            self.__record_state = True
            self.__record_started_timestamp = datetime.now()
            self.__record_output = self.__record_path + str(self.__record_started_timestamp).replace(":", "-")
            print('>>> Start recording ' + self.__record_output)

            cap = cv2.VideoCapture(self.__video_source)

            fourcc = cv2.VideoWriter_fourcc(*'XVID')
            out = cv2.VideoWriter(self.__record_output + self.__record_format, fourcc, self.__video_source_fps, (self.__video_source_width, self.__video_source_height))

            while(self.__record_state == True):
                ret, frame = cap.read()
                if ret == True:
                    out.write(frame)
                else:
                    break

            cap.release()
            out.release()
        else:
            print('>>> Already recording')

    def stop_record(self):
        if self.__record_state == True:
            self.__record_state = False
            self.__record_started_timestamp = None
            print('>>> Stop recording ' + self.__record_output)
            self.__record_output = None

    def analyze_turn(self, turn_points): 
        # self.__highlight_turn_points = 0
        # print('Turn ended, points: ' + str(turn_points))  
        return

    def analyze_throw(self, thrower, throw_number, throw_points, points_left):
        throw_number = int(throw_number)
        throw_points = int(throw_points)

        self.__highlight_turn_throw_number = throw_number
        self.__highlight_turn_points += throw_points

        print('>>> TURN-THROW-NUMBER: ' + str(self.__highlight_turn_throw_number))
        print('>>> TURN-TURN-POINTS: ' + str(self.__highlight_turn_points))
        
        if self.__highlight_started_timestamp == None:
            self.__highlight_started_timestamp = datetime.now()
            print('>>> Start possible highlight')

        if self.__highlight_turn_points >= self.__highlight_highscore_on:
            highlight_ended_timestamp = datetime.now()

            print('>>> Boom Highscore-Highlight: ' + str(self.__highlight_turn_points))
            self.__highlight_turn_points = 0

            self.__set_ptz_camera_highlight()
            
            # Proceed video record as long as the clip should be after the highlight
            time.sleep(self.__highlight_time_offset_after + 2)
            self.__record_state = False
            time.sleep(2.0)
            
            # Extract clip
            self.__extract_confirmed_highlight(highlight_ended_timestamp)
            
            # Remove non needed recording
            self.__delete_recording()

            # Start new fresh recording
            self.record()
        else:
            print('>>> Too bad')

        if throw_number == 3:
            self.__highlight_turn_points = 0



    def __set_ptz_camera_default(self):
        if self.__onvif_ptz_camera == True:
            print('>>> Set PTZ-Camera to default')
            self.__ptz_camera.goto_preset(self.__onvif_ptz_camera_preset_default)


    def __set_ptz_camera_highlight(self):
        if self.__onvif_ptz_camera == True:
            print('>>> Set PTZ-Camera to highlight')
            self.__ptz_camera.goto_preset(self.__onvif_ptz_camera_preset_zoom_triple_20)

    def __extract_confirmed_highlight(self, highlight_ended_timestamp):
        
        try:
            if self.__highlight_started_timestamp != None and highlight_ended_timestamp != None:
                highlight_duration = int((highlight_ended_timestamp-self.__highlight_started_timestamp).total_seconds())

                clip = VideoFileClip(self.__record_output + self.__record_format)

                start_highlight_timestamp = int((self.__highlight_started_timestamp-self.__record_started_timestamp).total_seconds())
                start = start_highlight_timestamp - self.__highlight_time_offset_before
                end = start_highlight_timestamp + highlight_duration + self.__highlight_time_offset_after

                subclip = clip.subclip(start, end)
                subclip.write_videofile(self.__record_output + "_highlight.mp4")
            else:
                print('>>> Recording is too short to clip, skip')
        except:
            print('>>> Grabbing clip failed')
        finally:
            self.__highlight_started_timestamp = None

    def __delete_recording(self):
        try:
            os.remove(self.__record_output + self.__record_format)
        except:
            return


@app.route('/leg_started')
def leg_started():
    autodarts_highlights.record()
    return "200"

@app.route('/leg_ended')
def leg_ended():
    autodarts_highlights.stop_record()
    return "200"

@app.route('/throw/<thrower>/<throw_number>/<throw_points>/<points_left>')
def throw(thrower, throw_number, throw_points, points_left):
    autodarts_highlights.analyze_throw(thrower, throw_number, throw_points, points_left)
    return "200"

@app.route('/turn/<turn_points>')
def turn(turn_points):
    autodarts_highlights.analyze_turn(turn_points)
    return "200"



if __name__ == "__main__":
    with open("config.json") as json_data_file:
        config = json.load(json_data_file)


    autodarts_highlights = AutodartsHighlights(config = config)
    autodarts_highlights.start()

    app.run(host = config['host'] , port = config['port'])

    autodarts_highlights.close()
    print("Stop Autodarts-Highlights requested")
    autodarts_highlights.join()
    print("Autodarts-Highlights stopped")