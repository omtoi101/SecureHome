import os
import subprocess
import threading

from discord_webhook import DiscordEmbed, DiscordWebhook


class WebhookBuilder:
    def __init__(self, url, dir) -> None:
        self.url = url
        self.dir = dir
        self.webhook = DiscordWebhook(
            url=self.url,
            username="Security Cam",
            avatar_url="https://omtoi101.com/resources/security_logo.png",
            rate_limit_retry=True,
        )
        self.embed = DiscordEmbed(title="Security Bot", color="404040")
        self.embed.set_author(
            name="Security Cam",
            url="https://github.com/omtoi101",
            icon_url="https://omtoi101.com/resources/security_logo.png",
        )

    def add_image(self, path) -> DiscordWebhook:
        self.file_webhook = DiscordWebhook(
            url=self.url,
            username="Security Cam",
            avatar_url="https://omtoi101.com/resources/security_logo.png",
            rate_limit_retry=True,
        )
        _, filename = os.path.split(path)
        with open(path, "rb") as f:
            self.file_webhook.add_file(file=f.read(), filename=filename)
        return self.file_webhook

    def convert_avi_to_mp4(self, avi_file_path, output_name):
        command = [
            "ffmpeg",
            "-i",
            avi_file_path,
            "-ac",
            "2",
            "-b:v",
            "2000k",
            "-c:a",
            "aac",
            "-c:v",
            "libx264",
            "-b:a",
            "160k",
            "-vprofile",
            "high",
            "-bf",
            "0",
            "-strict",
            "experimental",
            "-f",
            "mp4",
            output_name,
            "-y",
        ]
        subprocess.run(
            command,
            capture_output=True,
        )

    def add_recording(self, path):
        self.newpath = os.path.join(self.dir, "clipped", "output.mp4")
        self.convert_avi_to_mp4(path, self.newpath)
        self.vid_webhook = DiscordWebhook(
            url=self.url,
            username="Security Cam",
            avatar_url="https://omtoi101.com/resources/security_logo.png",
            rate_limit_retry=True,
        )
        _, self.filename = os.path.split(self.newpath)
        with open(self.newpath, "rb") as f:
            self.vid_webhook.add_file(file=f.read(), filename=self.filename)
        self.ret = self.vid_webhook.execute()
        # self.ret_json = json.dumps(self.ret.json)
        if str(self.ret) != "<Response [200]>":
            self.vid_webhook.remove_files()
            self.vid_webhook.content = "Video file too big, view hard copy."
            self.vid_webhook.execute()

    def intruder(self, img):
        self.webhook.add_embed(self.embed)
        self.embed.set_title("INTRUDER DETECTED")
        self.embed.set_color("FF0000")
        self.response = self.webhook.execute()
        self.add_image(img).execute()

    def u_face(self, img):
        self.webhook.add_embed(self.embed)
        self.embed.set_title("UNKNOWN FACE DETECTED")
        self.embed.set_color("EE4B2B")
        self.response = self.webhook.execute()
        self.add_image(img).execute()

    def logged_in(self, user, img):
        self.webhook.add_embed(self.embed)
        self.embed.set_title(f"{str(user).upper()} LOGGED IN")
        self.embed.set_color("00FF00")
        self.response = self.webhook.execute()
        self.add_image(img).execute()

    def thread(self, action=("login", "intruder", "unknown", "recording"), *args):
        self.__init__(self.url, self.dir)
        if action == "login":
            self.arglist = []
            for arg in args:
                self.arglist.append(arg)
            self.t = threading.Thread(target=self.logged_in, args=self.arglist).start()
        elif action == "intruder":
            self.arglist = []
            for arg in args:
                self.arglist.append(arg)
            self.t = threading.Thread(target=self.intruder, args=self.arglist).start()
        elif action == "unknown":
            self.arglist = []
            for arg in args:
                self.arglist.append(arg)
            self.t = threading.Thread(target=self.u_face, args=self.arglist).start()
        elif action == "recording":
            self.arglist = []
            for arg in args:
                self.arglist.append(arg)
            self.t = threading.Thread(
                target=self.add_recording, args=self.arglist
            ).start()
