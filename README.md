# AUTODARTS-HIGHLIGHTS

!!! CURRENTLY NOT UNDER ACTIVE DEVELOPMENT AND MAY BE NON-FUNCTIONAL !!!

Autodarts-highlights is primary an extension to https://github.com/lbormann/autodarts-caller.
It provides two web-endpoints that are fed by autodarts-caller. Its creates video-highlight-clips based on your opinion what it means to be a worthy clip. 

Besides your camera-setup for https://autodarts.io, you need at least one more camera that is able to see your board (and/ or yourself) to fetch the full event. 
If you use multiple cameras (at least two), make sure your cameras have similar or equal configuration; use same resolution to prevent black bars in clips. use same fps to prevent delays that needs to be re-synced. Dont use super high quality (> 1920x1080, > 8000 kbps) - it prevents you from annoying calibration and disk-space usage.

Tested on Windows 11 Pro x64, Python 3.9.7, Sunba Illuminati, One Plus 7 Pro with App CamON Live


## INSTALL INSTRUCTION


### Setup python3

- Download and install python 3.x.x for your specific os.
- Download and install pip

### Get the project

    git clone https://github.com/lbormann/autodarts-highlights.git
    https://github.com/cisco/openh264/releases
    Download ffmpeg for your specific os.
    Download h264 for your specific os and put this dll-file in autodarts-highlights main-folder.

Go to download-directory and type:

    pip install -r requirements.txt


### Setup config file

Make a copy of 'config_default.json' and name it 'config.json'. Open it and fill up all entries with your specific values. Below you can find some explaination:

BASICS:

- host (String): In most cases that should be "0.0.0.0"
- port (String): Just choose a port that is not used by other applications, ie. "9095"
- record-path (String): Absolute path for recordings and clips. If the path not exists, the application will create it for you
- sounds-path (String): Absolute path
- highlights-highscore-on (Int): Score-value that is a Highscore in your opinion 
- highlights-highfinish-on (Int): Score-value that is a Highfinish in your opinion 
- highlights-time-offset-before (Int): Represents the time in seconds that should be recorded before a highlight starts
- highlights-time-offset-after (Int): Represents the time in seconds that should be recorded after a highlight occured
- telegram-upload (Boolean): Telegram-Upload activated?
- telegram-bot-token (String): Access-token to your telegram-bot (Message with telegram-botfarther to create a new bot)
- telegram-bot-password (String): Password for bot access for users (only once needed)
- telegram-automatic-upload (Boolean): Upload every highlight-clip automatically?

VIDEO-SOURCES:

- id (String): It can be 0 or a network-path to your camera

- onvif-ptz-camera (Boolean): If you got onvif controllable ptz-camera, you can activate it here
- onvif-ptz-camera-host (String): onvif host-address of your camera
- onvif-ptz-camera-port (Int): onvif port of your camera
- onvif-ptz-camera-user (String): onvif username to access your camera
- onvif-ptz-camera-password (String): onvif password to access your camera
- onvif-ptz-camera-preset-default (Int): default-park-preset for recording
- onvif-ptz-camera-preset-zoom (Int): zoom-preset-number for zooming after a highlight occured


## RUN IT

Simple run command example:

    python autodarts-highlights.py

INFO: Make sure that it runs before a match at https://autodarts.io starts


## Setup autoboot [linux] (optional)

    crontab -e

At the end of the file add:

    @reboot cd <absolute-path-to>/autodarts-highlights && python autodarts-highlights.py 

Save and close the file. Reboot your system.


## BUGS

It may be buggy. I've just coded it for fast fun with https://autodarts.io. You can give me feedback in Discord > wusaaa


## TODOs

### Done
- Extends html to watch clips (top: newest, down. latest)
- create simple html: start-record, stop-record
- create folder for every record-run with all camera-record-outputs
- Dont stop every record on highlight, just produce a list of 3-throws timestamps, and save them to a json file
- add caller sounds
- add crowd before first dart (loud to silent), every dart "Ouh", in the end mix caller in
- change clip-file name to: timestamp_thrower_variant_type_value
- change default constant clip-path to record-path to know where the clips come from easily
- make every clip-generation unique
- Let the user re-generate a highlight-clip
    - let the user change the thrower name
    - let the user change latence when its not sync (delay for video-sources)
    - Let the user change turn-value when its wrong
    - Let the user delete (hide/show) a highlight-clip
- Force browser to reload videos
- delete recordings without highlights automatically
- Add mirror to config (video-sources)
- extend AD-Caller for busted, variant etc.
- add DEBUG, add printv for each Class
- Remove ptz-functionality, at least from config
- bring in telegram bot - upload every highlight via button
- One record per leg (automatic recording)
- care of turned ended to prevent false addition of throw values
- Check for clip, out of duration, on clip-generation
- Care of highlight on record-start/-end
- only react to supported games modes
- Remove redudant code

### In queue
- Write events to logfile
- Anchor to video when generate was clicked
- parallize highlight-clip-generation instead of each recording one-by-one
- Handle multiple video-source (for now 2 are working for "correct" clips - side by side)
- improve mobile version
    - maximize video player
- Care of possible error situations that may appear during long run 
    - what happens when one camera is activated but not reachable
    - what happens when clip generation fails
    - what happens when recording was deleted during clip-generation
    - test under linux, .avi - different format?
    - what happens when no config file rdy?
    - Does calibration work in different browsers?


## LAST WORDS

Make sure your camera is available.
Thanks to Timo for awesome https://autodarts.io. It will be huge!
