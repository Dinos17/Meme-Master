import discord
from discord.ext import commands
import asyncio
import requests
from collections import deque
import os
import logging
import time
import re

# Configure logging
logging.basicConfig(
    level=logging.WARNING,  # Change to WARNING to prevent info-level logs in the console
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler("bot.log"), logging.StreamHandler()]
)

# Token provided by the environment variable
TOKEN = os.getenv("BOT_TOKEN")

# Ensure the token is set
if TOKEN is None:
    raise ValueError("DISCORD_TOKEN environment variable is not set!")

# Initialize the bot with default intents (No PyNaCl needed)
intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)

# Global variables
active_channels = {}  # Stores active channels and their intervals
stopped_channels = set()  # Channels where meme posting is paused
memes_posted = 0  # Counter for memes posted
command_history_list = deque(maxlen=30)  # Stores last 30 commands
recent_memes = []  # Stores recently posted memes
custom_categories = {}  # Stores user-defined meme categories

# Helper function to validate meme categories
def is_valid_category(category):
    valid_categories = ["funny", "animals", "gaming", "wholesome"]
    return category in valid_categories or category in custom_categories

# Helper function to parse time in the format '5 min', '30 sec', etc.
def parse_time(interval):
    match = re.match(r"(\d+)\s*(sec|min|hour|h|m|s)", interval.strip().lower())
    if not match:
        raise ValueError("Invalid time format. Use 'min' for minutes or 'sec' for seconds.")
    
    value, unit = match.groups()
    value = int(value)
    
    if unit in ["min", "m"]:
        return value * 60  # Convert minutes to seconds
    elif unit in ["sec", "s"]:
        return value  # Already in seconds
    elif unit in ["hour", "h"]:
        return value * 3600  # Convert hours to seconds
    else:
        raise ValueError("Invalid time unit.")

# Function to fetch memes from an API with retry mechanism
def get_meme(category=None):
    retries = 3  # Number of retries before failing
    for attempt in range(retries):
        if category and not is_valid_category(category):
            logging.warning(f"Invalid category: {category}")
            return None, None
        url = f"https://meme-api.com/gimme/{category}" if category else "https://meme-api.com/gimme"
        try:
            response = requests.get(url)
            response.raise_for_status()
            data = response.json()
            return data["url"], data["title"]
        except requests.exceptions.RequestException as e:
            logging.error(f"Error fetching meme (attempt {attempt + 1}/{retries}): {e}")
            time.sleep(2)  # Wait for a short time before retrying
    return None, None  # Return None if all attempts fail


# Slash commands

@bot.tree.command(name="addcategory", description="Add a custom meme category.")
async def addcategory(interaction: discord.Interaction, category_name: str):
    """Allows users to add their own meme category."""
    if category_name in custom_categories:
        await interaction.response.send_message(f"Category '{category_name}' already exists!")
    else:
        custom_categories[category_name] = []
        await interaction.response.send_message(f"Custom category '{category_name}' added!")


@bot.tree.command(name="removecategory", description="Remove a custom meme category.")
async def removecategory(interaction: discord.Interaction, category_name: str):
    """Allows users to remove a custom meme category."""
    if category_name in custom_categories:
        del custom_categories[category_name]
        await interaction.response.send_message(f"Custom category '{category_name}' removed!")
    else:
        await interaction.response.send_message(f"Category '{category_name}' does not exist.")


@bot.tree.command(name="viewcategories", description="View all custom meme categories.")
async def viewcategories(interaction: discord.Interaction):
    """View all custom meme categories added by users."""
    if custom_categories:
        categories_list = "\n".join([f"{name}" for name in custom_categories])
        await interaction.response.send_message(f"**Custom Categories**:\n{categories_list}")
    else:
        await interaction.response.send_message("No custom categories available.")


@bot.tree.command(name="memecategory", description="Fetch and post a meme from a custom or pre-defined category.")
async def memecategory(interaction: discord.Interaction, category: str):
    """Fetch and post a meme based on a custom or pre-defined category."""
    meme_url, meme_title = get_meme(category)
    if meme_url:
        await interaction.response.send_message(f"**{meme_title}**\n{meme_url}")
    else:
        await interaction.response.send_message("Sorry, couldn't fetch a meme right now.")


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
    embed.add_field(name="/addcategory", value="Add a custom meme category.", inline=False)
    embed.add_field(name="/removecategory", value="Remove a custom meme category.", inline=False)
    embed.add_field(name="/viewcategories", value="View all custom meme categories.", inline=False)
    embed.add_field(name="/memecategory", value="Fetch a meme from a custom or pre-defined category.", inline=False)
    await interaction.response.send_message(embed=embed)


@bot.tree.command(name="meme", description="Fetch and post a meme instantly.")
async def meme(interaction: discord.Interaction):
    await interaction.response.defer()
    meme_url, meme_title = get_meme()
    if meme_url:
        await interaction.followup.send(f"**{meme_title}**\n{meme_url}")
    else:
        await interaction.followup.send("Sorry, couldn't fetch a meme right now.")


@bot.tree.command(name="setchannel", description="Set the channel for memes to be posted.")
async def setchannel(interaction: discord.Interaction, channel: discord.TextChannel, category: str, interval: str):
    try:
        time_in_seconds = parse_time(interval)
        if not is_valid_category(category):
            await interaction.response.send_message("Invalid category. Please choose from: funny, animals, gaming, wholesome.")
            return
        active_channels[channel.id] = {"channel": channel, "category": category, "interval": time_in_seconds}
        asyncio.create_task(post_meme_to_channel(channel, time_in_seconds, category))
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
        category = active_channels[channel.id]["category"]
        asyncio.create_task(post_meme_to_channel(channel, interval, category))
        await interaction.response.send_message(f"Resumed posting memes in {channel.mention}.")
    else:
        await interaction.response.send_message(f"{channel.mention} is not set up or already active.")


@bot.tree.command(name="stats", description="Show bot statistics.")
async def stats(interaction: discord.Interaction):
    stats_message = f"**📊 Bot Statistics**\n"
    stats_message += "---------------------------\n"
    stats_message += f"**📅 Memes Posted**: {memes_posted}\n"
    stats_message += f"**💬 Active Channels**: {len(active_channels)}\n"
    stats_message += f"**⏸️ Stopped Channels**: {len(stopped_channels)}\n"
    stats_message += f"**🔄 Recent Memes Posted**: {recent_memes[-10:] if recent_memes else 'No memes posted yet'}"
    await interaction.response.send_message(stats_message)


# Start the bot
bot.run(TOKEN)