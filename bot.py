import discord
from discord.ui import Select, View
from discord.ext import commands
import asyncio
import requests
from datetime import datetime, timedelta
import random
import os

# Get the bot token from environment variables
TOKEN = os.getenv("BOT_TOKEN")  # Store the token securely in environment variable

# Initialize the bot with necessary intents
intents = discord.Intents.default()
intents.message_content = True  # Enable message content intent

bot = commands.Bot(command_prefix="!", intents=intents)

# Variable to hold the channel IDs where memes will be sent
active_channels = {}
stopped_channels = set()  # To track channels where memes are stopped
memes_posted = 0  # Counter for memes posted
command_history_list = []  # List to store history of bot commands
MAX_COMMAND_HISTORY = 30  # Maximum number of commands to store in the history
recent_memes = []  # This will store all the recent memes

# Variable to track tasks
channel_tasks = {}

def get_meme():
    url = "https://meme-api.com/gimme"  # Public meme API
    try:
        response = requests.get(url)
        response.raise_for_status()  # Raise HTTPError for bad responses
        if response.status_code == 200:
            data = response.json()
            meme_url = data["url"]
            meme_title = data["title"]
            return meme_url, meme_title
    except requests.exceptions.RequestException as e:
        print(f"Error fetching meme: {e}")
        return None, None  # Return None if there's an issue

# Updated function to fetch recent memes (treated as trending)
def get_trending_memes():
    url = "https://meme-api.com/gimme/5"  # Fetch 5 memes at once
    try:
        response = requests.get(url)
        response.raise_for_status()
        if response.status_code == 200:
            data = response.json()
            return data["memes"]  # Assuming the API returns a "memes" list
    except requests.exceptions.RequestException as e:
        print(f"Error fetching trending memes: {e}")
        return None

# Helper function to fetch weekly memes
def get_weekly_memes():
    # For now, we'll just return the recent memes from the list as an example
    return recent_memes[-7:]  # Show the last 7 memes

# Helper function to track commands (implementing a basic command logging system)
def log_command(command: str):
    command_history_list.append(command)

# Function to rate dankness (implement your rating logic here)
def rate_dankness(meme_url):
    # Use a random number between 1 and 10 for a dynamic rating
    return random.randint(1, 10)  # Random dankness rating between 1 and 10

async def post_meme_to_channel_at_midnight(channel, interval):
    global memes_posted, recent_memes
    while True:
        meme_url, meme_title = get_meme()
        if meme_url:
            recent_memes.append({"url": meme_url, "title": meme_title})
            await channel.send(f"**{meme_title}**\n{meme_url}")
            memes_posted += 1
        await asyncio.sleep(interval)

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
            interval = parse_time(time)  # Parse the time input (in seconds)
            active_channels[channel.id] = {"channel": channel, "interval": interval}  # Store channel and interval
            await interaction.response.send_message(f"Meme channel has been set to {channel.mention} with an interval of {interval} seconds.")
            
            # Start posting memes immediately
            task = asyncio.create_task(post_meme_to_channel(channel, interval))  # Create and start meme posting task
            print(f"Started meme posting task for {channel.mention} with interval {interval} seconds.")  # Debugging line
            channel_tasks[channel.id] = task  # Store task for future cancellation

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
        # Cancel the task that is posting memes for this channel
        if channel.id in channel_tasks:
            channel_tasks[channel.id].cancel()  # Cancel the task
            del channel_tasks[channel.id]  # Remove the task from the tracking dictionary
        await interaction.response.send_message(f"Stopped posting memes in {channel.mention}. To resume posting, use /startmemes.")
    else:
        await interaction.response.send_message(f"{channel.mention} is not set up to post memes.")

@bot.tree.command(name="stats", description="Display specific bot usage statistics.")
async def stats(interaction: discord.Interaction):
    # Create a dropdown menu with options
    select = Select(
        placeholder="Select a statistic to view...",
        min_values=1,
        max_values=1,
        options=[
            discord.SelectOption(label="Total Memes Posted", value="total memes posted"),
            discord.SelectOption(label="Total Commands Used", value="total commands used"),
            discord.SelectOption(label="Active Meme Channels", value="active meme channels"),
            discord.SelectOption(label="Stopped Meme Channels", value="stopped meme channels"),
            discord.SelectOption(label="Stats Log", value="stats log")  # New option to show all stats
        ]
    )

    # Create a View to hold the select menu
    view = View()
    view.add_item(select)

    # Define the callback when a user selects an option
    async def select_callback(interaction: discord.Interaction):
        info = select.values[0].lower()

        if info == "total memes posted":
            response = f"🖼️ **Total Memes Posted**: {memes_posted}"
        elif info == "total commands used":
            response = f"📜 **Total Commands Used**: {len(command_history_list)}"
        elif info == "active meme channels":
            response = f"📡 **Active Meme Channels**: {len(active_channels)}"
        elif info == "stopped meme channels":
            response = f"⏸️ **Stopped Meme Channels**: {len(stopped_channels)}"
        elif info == "stats log":
            response = (
                f"**Bot Usage Statistics**\n"
                f"🖼️ **Total Memes Posted**: {memes_posted}\n"
                f"📜 **Total Commands Used**: {len(command_history_list)}\n"
                f"📡 **Active Meme Channels**: {len(active_channels)}\n"
                f"⏸️ **Stopped Meme Channels**: {len(stopped_channels)}"
            )

        await interaction.response.edit_message(content=response, view=None)

    # Attach the callback to the select menu
    select.callback = select_callback

    # Send the initial message with the select menu
    await interaction.response.send_message("Please select a statistic to view:", view=view)

# Slash command to send a meme instantly
@bot.tree.command(name="meme", description="Fetch and post a meme instantly.")
async def meme(interaction: discord.Interaction):
    meme_url, meme_title = get_meme()
    if meme_url:
        await interaction.response.send_message(f"**{meme_title}**\n{meme_url}")
    else:
        await interaction.response.send_message("Sorry, couldn't fetch a meme right now.")

# Command to view a history of bot commands used
@bot.tree.command(name="command_history", description="View a history of the last 30 bot commands used.")
async def command_history(interaction: discord.Interaction):
    # Display only the last 30 commands from the history
    history = "\n".join(command_history_list[-MAX_COMMAND_HISTORY:])
    if not history:
        history = "No commands used yet."
    
    # Send the command history in an embed (or plain message)
    embed = discord.Embed(
        title="Command History",
        description=history,
        color=discord.Color.green()
    )
    await interaction.response.send_message(embed=embed)



# Slash command to show trending memes
@bot.tree.command(name="trending_meme", description="Show trending memes.")
async def trending_meme(interaction: discord.Interaction):
    trending_memes = get_trending_memes()  # Fetch memes treated as trending
    if trending_memes:
        message = "Trending memes:\n"
        for meme in trending_memes:
            meme_title = meme["title"]
            meme_url = meme["url"]
            message += f"**{meme_title}**\n{meme_url}\n"
        await interaction.response.send_message(message)
    else:
        await interaction.response.send_message("No trending memes available.")

# New command to rate the dankness of a meme
@bot.tree.command(name="dankmeter", description="Rate the dankness of a meme.")
async def dankmeter(interaction: discord.Interaction, meme_url: str):
    dankness_rating = rate_dankness(meme_url)
    await interaction.response.send_message(f"The dankness of the meme is: {dankness_rating}/10")

# Slash command to check if the bot is online (ping)
@bot.tree.command(name="ping", description="Check if the bot is online.")
async def ping(interaction: discord.Interaction):
    await interaction.response.send_message("Pong! The bot is online and responsive.")

@bot.tree.command(name="help", description="Show available bot commands.")
async def help(interaction: discord.Interaction):
    embed = discord.Embed(
        title="Bot Commands",
        description="Here are the available commands you can use:",
        color=discord.Color.blue()
    )
    
    embed.add_field(
        name="🔧 /setchannel",
        value="Set the channel for memes to be posted and set the interval.",
        inline=False
    )
    embed.add_field(
        name="🎯 /meme",
        value="Fetch and send a single meme immediately.",
        inline=False
    )
    embed.add_field(
        name="⏸️ /stopmemes",
        value="Stop automatic meme posting.",
        inline=False
    )
    embed.add_field(
        name="▶️ /startmemes",
        value="Start automatic meme posting.",
        inline=False
    )
    embed.add_field(
        name="📊 /stats",
        value="Display bot usage statistics.",
        inline=False
    )
    embed.add_field(
        name="🏓 /ping",
        value="Test the bot's responsiveness.",
        inline=False
    )
    embed.add_field(
        name="⏳ /command_history",
        value="View a history of bot commands used.",
        inline=False
    )
    embed.add_field(
        name="👀 /trending memes",
        value="Show trending memes.",
        inline=False
    )
    embed.add_field(
        name="💀 /dankmeter",
        value="Rate the dankness of a meme.",
        inline=False
    )
    
    await interaction.response.send_message(embed=embed)

@bot.event
async def on_interaction(interaction: discord.Interaction):
    if interaction.type == discord.InteractionType.application_command:
        # Log the command to the history list
        command_history_list.append(f"/{interaction.data['name']} used by {interaction.user.name}")
        # Comment or remove this line to stop printing to console
        # print(f"Command /{interaction.data['name']} used by {interaction.user.name}")  # For debugging


# Event to sync commands
@bot.event
async def on_ready():
    # Sync the commands to make sure they're updated with Discord
    await bot.tree.sync()
    print(f"Bot is ready and commands are synced!")

# Function to post memes at the set intervals
async def post_memes():
    global active_channels, stopped_channels, memes_posted, recent_memes
    tasks = []
    for channel_id, data in active_channels.items():
        if channel_id not in stopped_channels:
            interval = data["interval"]
            channel = data["channel"]
            # Create and track the task for posting memes
            task = asyncio.create_task(post_meme_to_channel(channel, interval))
            channel_tasks[channel_id] = task  # Store the task for future cancellation
            tasks.append(task)
    await asyncio.gather(*tasks)

async def post_meme_to_channel(channel, interval):
    global memes_posted, recent_memes  # Make sure to use the global recent_memes list
    while True:
        if channel.id in stopped_channels:
            break  # Stop posting if the channel is marked as stopped
        
        meme_url, meme_title = get_meme()  # Fetch a meme
        if meme_url:
            recent_memes.append({"url": meme_url, "title": meme_title})  # Add meme to history
            await channel.send(f"**{meme_title}**\n{meme_url}")  # Send meme to channel
            memes_posted += 1
        
        await asyncio.sleep(interval)  # Wait for the next interval before posting another meme

# Run the bot
bot.run(TOKEN)
