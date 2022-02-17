# AUTODARTS-HIGHLIGHTS

Autodarts-highlights is primary an extension to https://github.com/lbormann/autodarts-caller.
It provides several web-endpoints that are fed by autodarts-caller. Its creates video-highlight-clips based on your opinion what it means to be a worthy clip to generate. 

Besides your camera-setup for Autodarts, you need at least one more camera that is able to see your board (and/ or yourself) to fetch the full event. 

Tested on Windows 11 Pro x64, Python 3.9.7, Sunba Illuminati (camera-0), One Plus 7 Pro with App CamON Live (camera-1)


## INSTALL INSTRUCTION


### Setup python3

- Download and install python 3.x.x for your specific os.
- Download and install pip
- Download and install https://imagemagick.org/script/download.php


### Get the project

    git clone https://github.com/lbormann/autodarts-highlights.git

Go to download-directory and type:

    pip install -r requirements.txt


### Setup config file

Make a copy of 'config_default.json' and name it 'config.json'. Open it and fill up all entries with your specific values. Below you can find some explaination:

- host (String): In most cases that should be "0.0.0.0"
- port (String): Just choose a port that is not used by other applications, ie. "9095"
- video-source (Int or String): It can be 0 or a network-path to your camera

- record-path (String): Absolute path for recordings and clips. If the path not exists, the application will create it for you
- highlights-highscore-on (Int): Score-value that is a Highscore in your opinion 
- highlights-highfinish-on (Int): Score-value that is a Highfinish in your opinion 
- highlights-time-offset-before (Int): Represents the time in seconds that should be recorded before a highlight starts
- highlights-time-offset-after (Int): Represents the time in seconds that should be recorded after a highlight occured
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



## Setup autoboot [linux] (optional)

    crontab -e

At the end of the file add:

    @reboot cd <absolute-path-to>/autodarts-highlights && python autodarts-highlights.py 

Save and close the file. Reboot your system.


## BUGS

It may be buggy. I've just coded it for fast fun with autodarts.io. You can give me feedback in Discord > wusaaa


## TODOs

- X create simple html: start-record, stop-record
- X create folder for every record-run with all camera-record-outputs
- X Dont stop every record on highlight, just produce a list of 3-throws timestamps, and save them to a json file
- X add caller sounds
- X add crowd before first dart (loud to silent), every dart "Ouh", in the end mix caller in
- X change clip-file name to: timestamp_thrower_variant_type_value
- X change default constant clip-path to record-path to know where the clips come from easily
- Let the user re-generate a highlight-clip
    - let the user change latence when its not sync (for every dart)
    - Let the user change turn-value when its wrong
    - Let the user delete (hide/show) a highlight-clip
- maybe combine AC with AH to one application?
- parallize highlight-clip-generation instead of each recording one-by-one
- Add latence to config
-X Add mirror to config (video-sources)
- Improve Readme
- Handle multiple video-source (for now 2 are working for "correct" clips)
- extend AD-Caller for busted, variant etc.
-X add DEBUG, add printv for each Class
- Remove ptz-functionality, at least from config
- replace image-background with wm-stage
- add scoreboard
- make every clip-generation unique
- Extends html to watch clips (top: newest, down. latest)
- Extends json-structure to see 9-darters
- Make it more easy to use
- Care of possible error situations that may appear during long run 
    - what happens when one camera is activated but not reachable
    - what happens when clip generation fails
    - what happens when recording was deleted during clip-generation


## LAST WORDS

Make sure your camera is available.
Thanks to Timo for awesome autodarts.io. It will be huge!
