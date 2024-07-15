# SecureHome
![terminal photo](https://github.com/omtoi101/SecureHome/blob/main/imgs_for_git/terminal.png)
### AI powered home security camera, with facial recognition, text to speach and push notifications through discord!



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
### Step 3 create discord server, bot and webhook
!! You can ignore this step if you don't intend to use the discord feature !!
#### Webhook:
1. Create a discord server for your security system
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
### DONE!!
Now to run the program all you have to do is execute the runner script as such:
```bash
python run.py
```





