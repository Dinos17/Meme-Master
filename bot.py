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

# A set to track memes already posted
posted_memes = set()

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
    global meme_channel_id
    meme_channel_id = channel.id
    await interaction.response.send_message(f"Meme channel has been set to {channel.mention}.")

# Slash command to send a meme instantly
@bot.tree.command(name="meme", description="Fetch and post a meme instantly.")
async def meme(interaction: discord.Interaction):
    meme_url, meme_title = get_meme()
    if meme_url:
        await interaction.response.send_message(f"**{meme_title}**\n{meme_url}")
    else:
        await interaction.response.send_message("Sorry, couldn't fetch a meme right now.")

# Slash command to view bot statistics (e.g., number of memes posted)
@bot.tree.command(name="stats", description="View bot statistics.")
async def stats(interaction: discord.Interaction):
    total_memes_posted = len(posted_memes)
    await interaction.response.send_message(f"Total memes posted: {total_memes_posted}")

# Slash command to view the most recent memes posted
@bot.tree.command(name="topmemes", description="View the top (recent) memes posted.")
async def topmemes(interaction: discord.Interaction):
    if posted_memes:
        # Show the most recent 5 memes posted
        recent_memes = list(posted_memes)[-5:]
        await interaction.response.send_message(f"Top 5 memes:\n" + "\n".join(recent_memes))
    else:
        await interaction.response.send_message("No memes have been posted yet.")

# Slash command to display a help message with available commands
@bot.tree.command(name="help", description="Display a list of available commands.")
async def help_command(interaction: discord.Interaction):
    help_text = """
    **Available Commands:**
    - /setchannel [channel]: Set the channel for memes to be posted.
    - /meme: Fetch and post a meme instantly.
    - /stats: View bot statistics (number of memes posted).
    - /topmemes: View the most recent memes posted.
    """
    await interaction.response.send_message(help_text)

# Event triggered when the bot logs in successfully
@bot.event
async def on_ready():
    await bot.tree.sync()  # Force syncing the slash commands with Discord
    print(f'Logged in as {bot.user}')

    # Start the meme posting task in the background
    asyncio.create_task(post_memes())  # This will run the meme posting loop in the background

# Function to post memes every 1 minute
async def post_memes():
    global meme_channel_id, posted_memes
    while True:
        if meme_channel_id:
            channel = bot.get_channel(meme_channel_id)
            if channel:
                meme_url, meme_title = get_meme()
                if meme_url and meme_url not in posted_memes:
                    await channel.send(f"**{meme_title}**\n{meme_url}")
                    posted_memes.add(meme_url)  # Add the meme URL to the set
                    print(f"Sent meme to {channel.name}")  # Debugging line
        await asyncio.sleep(60)  # Wait for 1 minute before posting another meme

# Run the bot using the token
bot.run(TOKEN)
