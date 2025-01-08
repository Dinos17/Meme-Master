import discord
from discord.ext import commands
import asyncio
import requests
import os

# Get the bot token from environment variables
TOKEN =  ("BOT_TOKEN")  # Store the token securely

# Initialize the bot with necessary intents
intents = discord.Intents.default()
intents.message_content = True  # Enable message content intent

bot = commands.Bot(command_prefix="!", intents=intents)

# Variable to hold the channel IDs where memes will be sent
active_channels = {}
stopped_channels = set()  # To track channels where memes are stopped
memes_posted = 0  # Counter for memes posted
recent_memes = []  # List to store recent memes

# Function to fetch a meme from the internet
def get_meme():
    url = "https://meme-api.com/gimme"  # Public meme API
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
        meme_url = data["url"]  # Meme image URL
        meme_title = data["title"]  # Meme title or description
        return meme_url, meme_title  # Return both the URL and the title
    return None, None  # Return None if there's an issue

# Slash command to set the meme channel with interval
@bot.tree.command(name="setchannel", description="Set the channel for memes to be posted and set the interval.")
async def setchannel(interaction: discord.Interaction, channel: discord.TextChannel, time: str):
    if channel.id in active_channels:
        if channel.id in stopped_channels:
            await interaction.response.send_message(f"{channel.mention} is already set up for memes but has been stopped. To resume posting, use /startmemes.")
        else:
            await interaction.response.send_message(f"{channel.mention} is already set up for memes.")
    else:
        try:
            interval = parse_time(time)
            active_channels[channel.id] = {"channel": channel, "interval": interval}
            await interaction.response.send_message(f"Meme channel has been set to {channel.mention} with an interval of {interval} seconds.")
            # Start posting memes immediately
            asyncio.create_task(post_memes())
        except ValueError:
            await interaction.response.send_message("Invalid time format. Please use 'min' for minutes or 'sec' for seconds.")

# Helper function to parse time input
def parse_time(time_str):
    time_str = time_str.lower().strip()
    if 'min' in time_str:
        minutes = int(time_str.replace("min", "").strip())
        return minutes * 60  # Convert minutes to seconds
    elif 'sec' in time_str:
        seconds = int(time_str.replace("sec", "").strip())
        return seconds  # Already in seconds
    else:
        raise ValueError("Invalid time format")

# Slash command to stop posting memes to a specific channel
@bot.tree.command(name="stopmemes", description="Stop posting memes to a specific channel.")
async def stopmemes(interaction: discord.Interaction, channel: discord.TextChannel):
    if channel.id in active_channels:
        stopped_channels.add(channel.id)
        await interaction.response.send_message(f"Stopped posting memes in {channel.mention}. To resume posting, use /startmemes.")
    else:
        await interaction.response.send_message(f"{channel.mention} is not set up to post memes.")

# Slash command to start posting memes to a specific channel
@bot.tree.command(name="startmemes", description="Start posting memes to a specific channel.")
async def startmemes(interaction: discord.Interaction, channel: discord.TextChannel):
    if channel.id in active_channels:
        if channel.id in stopped_channels:
            stopped_channels.remove(channel.id)
            await interaction.response.send_message(f"Started posting memes in {channel.mention}.")
        else:
            await interaction.response.send_message(f"Memes are already being posted in {channel.mention}.")
    else:
        await interaction.response.send_message(f"{channel.mention} is not set up to post memes.")

# Slash command to send a meme instantly
@bot.tree.command(name="meme", description="Fetch and post a meme instantly.")
async def meme(interaction: discord.Interaction):
    meme_url, meme_title = get_meme()
    if meme_url:
        await interaction.response.send_message(f"**{meme_title}**\n{meme_url}")
    else:
        await interaction.response.send_message("Sorry, couldn't fetch a meme right now.")

# Slash command to check if the bot is online (ping)
@bot.tree.command(name="ping", description="Check if the bot is online.")
async def ping(interaction: discord.Interaction):
    await interaction.response.send_message("Pong! The bot is online and responsive.")

# Slash command to show help message
@bot.tree.command(name="help", description="Show available bot commands.")
async def help(interaction: discord.Interaction):
    help_message = """
    **Available Commands:**
    - /setchannel [channel] time:[interval] – Set the channel for memes to be posted and define the interval for posting (in minutes or seconds).
    - /meme – Fetch and post a meme instantly.
    - /stopmemes [channel] – Stop posting memes to a specific channel.
    - /startmemes [channel] – Start posting memes to a specific channel.
    - /stats – View bot statistics (number of memes posted).
    - /topmemes – View the most recent memes posted.
    - /ping – Check if the bot is online.
    """
    await interaction.response.send_message(help_message)

# Event triggered when the bot logs in successfully
@bot.event
async def on_ready():
    await bot.tree.sync()  # Force syncing the slash commands with Discord
    print(f'Logged in as {bot.user}')

# Function to post memes at the set intervals
async def post_memes():
    global active_channels, stopped_channels, memes_posted, recent_memes
    tasks = []
    for channel_id, data in active_channels.items():
        if channel_id not in stopped_channels:
            task = asyncio.create_task(post_meme_for_channel(data))
            tasks.append(task)
    await asyncio.gather(*tasks)

# Helper function to handle posting memes to individual channels
async def post_meme_for_channel(data):
    global memes_posted  # Declare memes_posted as global to modify it
    channel = data["channel"]
    interval = data["interval"]
    while True:
        meme_url, meme_title = get_meme()
        if meme_url:
            await channel.send(f"**{meme_title}**\n{meme_url}")
            memes_posted += 1  # Update the global memes_posted counter
            recent_memes.append({"title": meme_title, "url": meme_url})
            if len(recent_memes) > 10:  # Keep the list size manageable
                recent_memes.pop(0)
        await asyncio.sleep(interval)

# Slash command to show bot stats
@bot.tree.command(name="stats", description="View bot statistics (number of memes posted).")
async def stats(interaction: discord.Interaction):
    await interaction.response.send_message(f"Memes posted: {memes_posted}")

# Slash command to show the most recent memes
@bot.tree.command(name="topmemes", description="View the most recent memes posted.")
async def topmemes(interaction: discord.Interaction):
    if recent_memes:
        message = "Most recent memes:\n"
        for meme in recent_memes[:5]:  # Show the 5 most recent memes
            message += f"{meme['title']} - {meme['url']}\n"
        await interaction.response.send_message(message)
    else:
        await interaction.response.send_message("No memes posted yet.")

# Run the bot using the token
bot.run(TOKEN)
