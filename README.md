# AUTODARTS-HIGHLIGHTS

Autodarts-highlights is primary an extension to https://github.com/lbormann/autodarts-caller.
It provides several web-endpoints that are fed by autodarts-caller. Its creates video-clips based on your opinion what it means to be a worthy clip to record. 

Besides your camera-setup for Autodarts, you need another camera that is able to see your board (and/ or yourself) to fetch the full event. I`ve got a ptz-camera here, so it can be zoomed after a highlight occured.

Tested on Windows 11 Pro x64, Python 3.9.7.


## INSTALL INSTRUCTION


### Setup python3

- Download and install python 3.x.x for your specific os.
- Download and install pip


### Get the project

    git clone https://github.com/lbormann/autodarts-highlights.git

Go to download-directory and type:

    pip install -r requirements.txt


### Setup config file

Make a copy of 'config_default.json' and name it 'config.json'. Open it and fill up all entries with your specific values. Below you can find some explaination:

- host (String): In most cases that should be "0.0.0.0"
- port (String): Just choose a port that is not used by other applications, ie. "9095"
- video-source (Int or String): It can be 0 or a network-path to your camera
- video-source-fps (Float): It should represent the frames per second that your camera is able to produce 
- video-source-width (Int): The width for records/clips 
- video-source-height (Int): The height for records/clips 
- record-path (String): Absolute path for recording-files. If the path not exists, the application will create it for you
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

- Make it more easy to use
- Care of possible error situations that may appear during long run 


## LAST WORDS

Make sure your camera is available.
Thanks to Timo for awesome autodarts.io. It will be huge!

