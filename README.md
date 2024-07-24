# SecureHome
![terminal photo](https://github.com/omtoi101/SecureHome/blob/main/media_for_git/terminal.png)
### AI powered home security camera, with facial recognition, text to speech and push notifications through Discord!

#### !! Working on Windows, Linux testing coming soon, Apple currently not working (maybe in the future) !!
![example gif](https://github.com/omtoi101/SecureHome/blob/main/media_for_git/example.gif)
### -----------------------------------------
### Next Update
* Allow IP cams as a source instead of just hard wired webcams
* Crash notifications through push notifications
### -----------------------------------------

## Features
* Motion detection
* Body/human detection
* Facial recognition
* Text to speech (for notifying intruders or whoever is at the door)
* Discord notifications (webhook)
* Discord remote management (bot)
* Automatic video recording
* Web server with live video feed (LAN only unless forwarded)
* Logging of everything that takes place
### Other
* No port forwarding
* Easy customization
* Simple to use and understand terminal UI
* Error logging for all segments of the script (logs folder)

## Requirements
* OBS (for virtual webcam)
* FFMPEG (for video handling)
* Pip packages (requirements.txt)
### Other
* Discord server

## Installation
### Step 1 Prerequisites
* Download OBS from [here](https://obsproject.com/)
* Download FFMPEG from [here](https://www.ffmpeg.org/download.html) (or use choco, apt, pip, etc)
### Step 2 python requirements
Install the required library's using:
```bash
pip install -r requirements.txt
```
### Step 3 create Discord server, bot and webhook
!! You can ignore this step if you don't intend to use the Discord features !!
#### Webhook:
1. Create a Discord server for your security system
2. Go to the settings panel for your server
3. Under the APPS header click on integrations
4. On the integrations page click webhooks then new webhook
5. Copy the webhook URL and paste it into your .env file under the URL option
#### Bot:
1. Go to the Discord developer portal website [here](https://discord.com/developers/applications)
2. Click new application and pick a name for it
3. In the application page go to bot
4. click reset token to get a new token for it
5. paste the token into your .env file under the TOKEN option
6. Back on the developer portal bot page under privileged gateway intents
7. Enable the 3 intents (presence, server members, message content) and save
6. Now click onto the OAuth2 section
7. In the OAuth2 URL generator section click the box for bot
8. In the next drop down click the box for administrator (or choose your own perms for the bot)
9. Copy the generated invite code and paste it in your browser, go through the steps to invite the bot to the server we just made
#### ALMOST DONE!!

### Step 4 configuring your cameras
!! See Customization below for more info on how to manage the config.json file !!

!! the default camera is usually cam 0 but it can vary depending on how many webcams/virtual cams you have run previously !!
* There is no fool proof way to do this but i've included the file camtest.py to assist you
1. Run the camtest.py script
```bash
python camtest.py
```
2. It will list out the currently running camera sources on your computer/server e.g. [0, 1, 3]
3. Edit the main option under camera in the config.json file with the first open camera
4. To run the program all you have to do is execute the runner script as such:
```bash
python run.py
```
If the SECURITY SYSTEM exits with an error such as:
```cpp
cv2.error: OpenCV(4.10.0) ...color.cpp:196: error: (-215:Assertion failed) !_src.empty() in function 'cv::cvtColor'
```

Or similar then either that camera source doesn't exist or you have the wrong source.

5. Once your script is running without error re-run the camtest.py to find the new virtual camera the script has created
6. If [0, 1, 3] was the original output this should look like [0, 1, 2, 3]
7. Enter the new camera source in the v_cam option under camera in the config.json file
8. Now if you navigate to the web server IP while the script is runnning you should see your camera feed with the AI detections

!! If the camera feed that appears on the webserver isnt the correct one keep trying different sources for step 2 and 3 and re running the script until the right source is found !!
### DONE!!!


### Customization
![config photo](https://github.com/omtoi101/SecureHome/blob/main/media_for_git/config.png)

The config.json file allows you to customize the functionality of the security system in many ways.
#### Settings
* motion_detection: Enable/disable if the camera picks up on motion
* speech: Enable/disable the speaking feature
* webserver: Enable/disable the webserver from running
* discord_notifications: Enable/disable the Discord webhook notifications
* discord_bot: Enable/disable the Discord bot for managing the faces in the database
* debug: Enables/disables errors showing up in the terminal (they will still always get logged)
#### Camera
* main: The main camera port number
* v_cam: The virtual camera port number
* body_inc: How many frames of a body being on screen it takes to recognize it
* face_inc: How many frames of a face being on screen it takes to recognize it
* motion_inc: How many frames of motion being on screen it takes to recognize it
* undetected_time: How many frames it of no detection being on screen takes for the camera to reset
* fallback_fps: The fps of the camera if it cant automatically detect the real fps




