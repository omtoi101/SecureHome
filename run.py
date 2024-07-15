import json, threading, os

from dependencies.Runner import Runner

cd = os.path.dirname(__file__)
with open(os.path.join(cd, "config.json"), "r") as conf_file:
    config = json.load(conf_file)

webserver = config["settings"]["webserver"]
bot = config["settings"]["discord_bot"]
debug = config["settings"]["debug"]

runner = Runner(cd, debug)

if webserver:
    threading.Thread(target=runner.exec, args=[fr'python "{cd}\server.py"', "web"]).start()

if bot:
    threading.Thread(target=runner.exec, args=[fr'python "{cd}\bot.py"', "bot"]).start()

threading.Thread(target=runner.exec, args=[fr'python "{cd}\main.py"', "sec"]).start()


