import discord
from discord.ext import commands
from discord import app_commands
import requests
import asyncio
import os  # For environment variables

# Get the bot token from environment variables
TOKEN = os.getenv("DISCORD_TOKEN")  # Store the token securely

# Initialize the bot
intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)

# Variable to hold the channel ID where memes will be sent
meme_channel_id = None

# Function to fetch a meme from the internet
def get_meme():
    url = "https://meme-api.com/gimme"  # Public meme API
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
        return data["url"]  # Meme image URL
    return None

# Slash command to set the meme channel
@bot.tree.command(name="setchannel", description="Set the channel for memes to be posted.")
async def setchannel(interaction: discord.Interaction, channel: discord.TextChannel):
    global meme_channel_id
    meme_channel_id = channel.id
    await interaction.response.send_message(f"Meme channel has been set to {channel.mention}.")

# Event triggered when the bot logs in successfully
@bot.event
async def on_ready():
    await bot.tree.sync()  # Force syncing the slash commands with Discord
    print(f'Logged in as {bot.user}')

    # Start the meme posting task in the background
    asyncio.create_task(post_memes())  # This will run the meme posting loop in the background

# Function to post memes every 1 minute
async def post_memes():
    global meme_channel_id
    while True:
        if meme_channel_id:
            channel = bot.get_channel(meme_channel_id)
            if channel:
                meme_url = get_meme()
                if meme_url:
                    await channel.send(meme_url)
                    print(f"Sent meme to {channel.name}")  # Debugging line
        await asyncio.sleep(60)  # Wait for 1 minute before posting another meme

# Run the bot using the token
bot.run(TOKEN)
