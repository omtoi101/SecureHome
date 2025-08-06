import asyncio
import glob
import json
import logging
import os
import random
import sys
import traceback

import colorama
import discord
import requests
from discord.ext import commands

from dependencies.Facedet import FaceDet

colorama.init()

logger = logging.getLogger("logger")
fh = logging.FileHandler(os.path.join(os.path.dirname(__file__), "logs", "d_bot.log"))
logger.addHandler(fh)


def exc_handler(exctype, value, tb):
    logger.exception("".join(traceback.format_exception(exctype, value, tb)))


sys.excepthook = exc_handler

with open(os.path.join(os.path.dirname(__file__), "config.json"), "r") as conf_file:
    config = json.load(conf_file)

# Get Discord bot token and other info from config.json
bot_token = config.get("discord", {}).get("bot_token", "")

TOKEN = bot_token
facedet = FaceDet(os.path.dirname(__file__))
images_path = os.path.join(os.path.dirname(__file__), "images")
bot = commands.Bot(command_prefix=".", intents=discord.Intents.all())
bot.remove_command("help")


@bot.event
async def on_ready():
    print(f"Bot started sucessfully as {bot.user}.")
    await bot.change_presence(
        activity=discord.Activity(
            type=discord.ActivityType.watching,
            name=random.choice(
                ["Your camera 📷", "Your house 🏠", "Everything 🤖"]
            ),
        )
    )


@bot.event
async def on_message(message):
    username = str(message.author.name)
    user_message = str(message.content)
    channel = str(message.channel.name)
    print(f"{username}: {user_message} ({channel})")
    await bot.process_commands(message)


@bot.command()
async def addface(ctx, name):
    f_types = (
        os.path.join(images_path, "*.jpg"),
        os.path.join(images_path, "*.png"),
    )
    faces = []
    for files in f_types:
        faces.extend(glob.glob(files))
    for i, face in enumerate(faces):
        _, face = os.path.split(face)
        faces[i] = face
    for i, face in enumerate(faces):
        face = face.split(".")[0]
        faces[i] = face
    if name in faces:
        await ctx.send(f"**{name}** is already in the database.")
    else:
        if len(ctx.message.attachments) > 0:
            attachment = ctx.message.attachments[0]
            if (
                attachment.filename.endswith(".jpg")
                or attachment.filename.endswith(".jpeg")
                or attachment.filename.endswith(".png")
            ):
                img_data = requests.get(attachment.url).content
                temp_path = os.path.join(os.getenv("TEMP"), f"ud_{name}.jpg")
                with open(temp_path, "wb") as handler:
                    handler.write(img_data)
                detector = facedet.findface(temp_path, name)
                if detector:
                    await ctx.send(
                        f"**{name}** added to database.",
                        file=discord.File(detector[2]),
                    )
                    os.remove(detector[2])
                else:
                    await ctx.send(
                        "**No face detected in image**, please try again in good lighting with your face in the centre of the screen."
                    )

        else:
            await ctx.send("No **image** attached to command.")


@bot.command()
async def delface(ctx, name):
    f_types = (
        os.path.join(images_path, "*.jpg"),
        os.path.join(images_path, "*.png"),
    )
    faces = []
    for files in f_types:
        faces.extend(glob.glob(files))
    for i, face in enumerate(faces):
        _, face = os.path.split(face)
        faces[i] = face
    for i, face in enumerate(faces):
        face = face.split(".")[0]
        faces[i] = face
    if name in faces:
        os.remove(os.path.join(os.path.dirname(__file__), "images", f"{name}.jpg"))
        await ctx.send(f"**{name}** removed from database.")
    else:
        await ctx.send(f"**{name}** is not in the database.")


@bot.command()
async def listfaces(ctx):
    f_types = (
        os.path.join(images_path, "*.jpg"),
        os.path.join(images_path, "*.png"),
    )
    faces = []
    for files in f_types:
        faces.extend(glob.glob(files))
    for i, face in enumerate(faces):
        _, face = os.path.split(face)
        faces[i] = face
    message = ""
    for face in faces:
        face = face.split(".")[0]
        message += f"{face}, "
    message = message[:-2]
    images = []
    for image in faces:
        image_path = os.path.join(os.path.dirname(__file__), "images", image)
        image = discord.File(image_path)
        images.append(image)
    try:
        if len(faces) > 1:
            await ctx.send(message + " (in order)", files=images)
        else:
            await ctx.send(message, files=images)
    except discord.HTTPException:
        await ctx.send(message)


@bot.command()
async def help(ctx):
    await ctx.send(
        "**listfaces**, **delface** (name), **addface** (name) [attachment]"
    )


async def main():
    try:
        await bot.start(TOKEN)
    except discord.errors.LoginFailure:
        logging.error("Invalid bot token. Please check your token and try again.")


asyncio.run(main())
