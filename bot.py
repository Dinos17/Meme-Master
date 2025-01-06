import discord
from discord.ext import commands
import asyncio
import requests
import os

# Get the bot token from environment variables
TOKEN = os.getenv("DISCORD_TOKEN")  # Store the token securely

# Initialize the bot with necessary intents
intents = discord.Intents.default()
intents.message_content = True  # Enable message content intent

bot = commands.Bot(command_prefix="!", intents=intents)

# Variable to hold the channel IDs where memes will be sent
active_channels = set()
stopped_channels = set()  # To track channels where memes are stopped

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

# Slash command to set the meme channel
@bot.tree.command(name="setchannel", description="Set the channel for memes to be posted.")
async def setchannel(interaction: discord.Interaction, channel: discord.TextChannel):
    if channel.id in active_channels:
        if channel.id in stopped_channels:
            await interaction.response.send_message(f"{channel.mention} is already set up for memes but has been stopped. To resume posting, use /startmemes.")
        else:
            await interaction.response.send_message(f"{channel.mention} is already set up for memes.")
    else:
        active_channels.add(channel.id)
        await interaction.response.send_message(f"Meme channel has been set to {channel.mention}.")

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

# Event triggered when the bot logs in successfully
@bot.event
async def on_ready():
    await bot.tree.sync()  # Force syncing the slash commands with Discord
    print(f'Logged in as {bot.user}')

    # Start the meme posting task in the background
    asyncio.create_task(post_memes())  # This will run the meme posting loop in the background

# Function to post memes every 1 minute
async def post_memes():
    global active_channels, stopped_channels
    while True:
        for channel_id in active_channels:
            if channel_id not in stopped_channels:
                channel = bot.get_channel(channel_id)
                if channel:
                    meme_url, meme_title = get_meme()
                    if meme_url:
                        await channel.send(f"**{meme_title}**\n{meme_url}")
                    print(f"Sent meme to {channel.name}")  # Debugging line
        await asyncio.sleep(60)  # Wait for 1 minute before posting another meme

# Run the bot using the token
bot.run(TOKEN)
