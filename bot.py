import discord
from discord.ext import commands
import asyncio
import requests
from collections import deque
import os
import sys
import time
import subprocess
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

# Token provided by the user
TOKEN = os.getenv("BOT_TOKEN")

# Initialize the bot with default intents
intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)

# Global variables
active_channels = {}  # Stores active channels and their intervals
stopped_channels = set()  # Channels where meme posting is paused
memes_posted = 0  # Counter for memes posted
command_history_list = deque(maxlen=30)  # Stores last 30 commands
recent_memes = []  # Stores recently posted memes

# Function to fetch memes from an API
def get_meme():
    url = "https://meme-api.com/gimme"
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        return data["url"], data["title"]
    except requests.exceptions.RequestException as e:
        print(f"Error fetching meme: {e}")
        return None, None

# Helper function to parse time input
def parse_time(time_str):
    time_str = time_str.lower().strip()
    if "min" in time_str:
        return int(time_str.replace("min", "").strip()) * 60
    elif "sec" in time_str:
        return int(time_str.replace("sec", "").strip())
    raise ValueError("Invalid time format. Use 'min' for minutes or 'sec' for seconds.")

# Function to post memes to a channel at intervals
async def post_meme_to_channel(channel, interval):
    global memes_posted, recent_memes
    while True:
        if channel.id in stopped_channels:
            break
        meme_url, meme_title = get_meme()
        if meme_url:
            recent_memes.append({"url": meme_url, "title": meme_title})
            if len(recent_memes) > 10:
                recent_memes.pop(0)
            await channel.send(f"**{meme_title}**\n{meme_url}")
            memes_posted += 1
        await asyncio.sleep(interval)

# Slash commands
@bot.tree.command(name="help", description="Show a list of all available commands.")
async def help_command(interaction: discord.Interaction):
    embed = discord.Embed(title="Help - Bot Commands", color=discord.Color.blue())
    embed.add_field(name="/meme", value="Fetch and post a meme instantly.", inline=False)
    embed.add_field(name="/setchannel", value="Set the channel for memes to be posted.", inline=False)
    embed.add_field(name="/stopmemes", value="Stop posting memes in a channel.", inline=False)
    embed.add_field(name="/startmemes", value="Resume posting memes in a channel.", inline=False)
    embed.add_field(name="/stats", value="Show bot statistics.", inline=False)
    embed.add_field(name="/recentmemes", value="Show the last 10 memes posted.", inline=False)
    embed.add_field(name="/command_history", value="View the history of commands used.", inline=False)
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="meme", description="Fetch and post a meme instantly.")
async def meme(interaction: discord.Interaction):
    await interaction.response.defer()  # Defer the response to give the bot time to fetch the meme
    
    meme_url, meme_title = get_meme()
    if meme_url:
        await interaction.followup.send(f"**{meme_title}**\n{meme_url}")
    else:
        await interaction.followup.send("Sorry, couldn't fetch a meme right now.")

@bot.tree.command(name="setchannel", description="Set the channel for memes to be posted.")
async def setchannel(interaction: discord.Interaction, channel: discord.TextChannel, category: str, interval: str):
    try:
        time_in_seconds = parse_time(interval)
        # Storing the channel along with category and interval
        active_channels[channel.id] = {"channel": channel, "category": category, "interval": time_in_seconds}
        asyncio.create_task(post_meme_to_channel(channel, time_in_seconds))
        await interaction.response.send_message(f"Set {channel.mention} as a meme channel with category '{category}' and an interval of {interval}.")
    except ValueError:
        await interaction.response.send_message("Invalid time format. Use 'min' for minutes or 'sec' for seconds.")

@bot.tree.command(name="stopmemes", description="Stop posting memes in a channel.")
async def stopmemes(interaction: discord.Interaction, channel: discord.TextChannel):
    if channel.id in active_channels:
        stopped_channels.add(channel.id)
        await interaction.response.send_message(f"Stopped posting memes in {channel.mention}.")
    else:
        await interaction.response.send_message(f"{channel.mention} is not set up for meme posting.")

@bot.tree.command(name="startmemes", description="Resume posting memes in a channel.")
async def startmemes(interaction: discord.Interaction, channel: discord.TextChannel):
    if channel.id in active_channels and channel.id in stopped_channels:
        stopped_channels.remove(channel.id)
        interval = active_channels[channel.id]["interval"]
        asyncio.create_task(post_meme_to_channel(channel, interval))
        await interaction.response.send_message(f"Resumed posting memes in {channel.mention}.")
    else:
        await interaction.response.send_message(f"{channel.mention} is not set up or already active.")

@bot.tree.command(name="stats", description="Show bot statistics.")
async def stats(interaction: discord.Interaction):
    stats_message = f"**Bot Stats:**\n"
    stats_message += f"Memes Posted: {memes_posted}\n"
    stats_message += f"Active Channels: {len(active_channels)}\n"
    stats_message += f"Stopped Channels: {len(stopped_channels)}"
    await interaction.response.send_message(stats_message)

@bot.tree.command(name="recentmemes", description="Show the last 10 memes posted.")
async def recentmemes(interaction: discord.Interaction):
    if recent_memes:
        embed = discord.Embed(title="Recent Memes", color=discord.Color.green())
        for meme in recent_memes:
            embed.add_field(name=meme["title"], value=meme["url"], inline=False)
        await interaction.response.send_message(embed=embed)
    else:
        await interaction.response.send_message("No memes have been posted yet.")

@bot.tree.command(name="command_history", description="View the history of commands used.")
async def command_history(interaction: discord.Interaction):
    if command_history_list:
        history_message = "**Command History:**\n" + "\n".join(command_history_list)
        await interaction.response.send_message(history_message)
    else:
        await interaction.response.send_message("No commands have been used yet.")

# Event listener to track command usage
@bot.event
async def on_interaction(interaction: discord.Interaction):
    if interaction.type == discord.InteractionType.application_command:
        command_history_list.append(f"/{interaction.data['name']}")  # Add command to history

# Event to sync commands and handle updates
@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f"Bot is ready as {bot.user}!")

# Watchdog to monitor file changes
class WatchdogHandler(FileSystemEventHandler):
    def on_modified(self, event):
        if event.src_path.endswith('.py'):
            print(f"Code changed: {event.src_path}. Restarting the bot...")
            self.restart_bot()

    def restart_bot(self):
        # Command to stop the old bot process and start a new one
        os.system("pkill -f 'python bot.py'")  # Replace 'bot.py' with your bot filename
        subprocess.Popen([sys.executable, 'bot.py'])  # Restart the bot process

# Start the bot and monitor code changes
def run_bot_with_watchdog():
    # Start watchdog
    observer = Observer()
    event_handler = WatchdogHandler()
    observer.schedule(event_handler, path=os.path.dirname(os.path.abspath(__file__)), recursive=True)
    observer.start()

    try:
        bot.run(TOKEN)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()

if __name__ == "__main__":
    run_bot_with_watchdog()