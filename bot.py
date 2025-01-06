import discord
from discord.ext import commands
from discord import app_commands
import requests
import asyncio
import os  # For environment variables

# Get the bot token from environment variables
TOKEN = os.getenv("DISCORD_TOKEN")  # Replace with your bot token for local testing

# Initialize the bot with necessary intents
intents = discord.Intents.default()
intents.message_content = True  # Enable message content intent

bot = commands.Bot(command_prefix="!", intents=intents)

# Variables to manage active channels and posted memes
active_channels = {}  # Dictionary to track {channel_id: is_active}
posted_memes = set()  # To track already posted memes

# Function to fetch a meme
def get_meme():
    url = "https://meme-api.com/gimme"  # Public meme API
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
        return data["url"], data["title"]
    return None, None

# Slash command: Set the channel for memes
@bot.tree.command(name="setchannel", description="Set the channel for memes to be posted.")
async def setchannel(interaction: discord.Interaction, channel: discord.TextChannel):
    if channel.id in active_channels:
        if not active_channels[channel.id]:
            await interaction.response.send_message(
                f"{channel.mention} is already set up for memes but is currently stopped. "
                "To resume posting memes, use `/startmemes`."
            )
        else:
            await interaction.response.send_message(
                f"{channel.mention} is already active for memes."
            )
    else:
        active_channels[channel.id] = False  # Set up channel but keep it stopped
        await interaction.response.send_message(
            f"Meme channel has been set to {channel.mention}. To start posting memes, use `/startmemes`."
        )

# Slash command: Start posting memes
@bot.tree.command(name="startmemes", description="Start posting memes to a specific channel.")
async def startmemes(interaction: discord.Interaction, channel: discord.TextChannel):
    if channel.id in active_channels:
        if active_channels[channel.id]:
            await interaction.response.send_message(
                f"Memes are already active in {channel.mention}."
            )
        else:
            active_channels[channel.id] = True
            await interaction.response.send_message(
                f"Started posting memes in {channel.mention}."
            )
    else:
        await interaction.response.send_message(
            f"{channel.mention} is not set up for memes. Use `/setchannel` first."
        )

# Slash command: Stop posting memes
@bot.tree.command(name="stopmemes", description="Stop posting memes to a specific channel.")
async def stopmemes(interaction: discord.Interaction, channel: discord.TextChannel):
    if channel.id in active_channels:
        if active_channels[channel.id]:
            active_channels[channel.id] = False
            await interaction.response.send_message(
                f"Stopped posting memes in {channel.mention}."
            )
        else:
            await interaction.response.send_message(
                f"Memes are already stopped in {channel.mention}."
            )
    else:
        await interaction.response.send_message(
            f"{channel.mention} is not set up for memes. Use `/setchannel` first."
        )

# Slash command: Post a meme instantly
@bot.tree.command(name="meme", description="Fetch and post a meme instantly.")
async def meme(interaction: discord.Interaction):
    meme_url, meme_title = get_meme()
    if meme_url:
        await interaction.response.send_message(f"**{meme_title}**\n{meme_url}")
    else:
        await interaction.response.send_message("Sorry, couldn't fetch a meme right now.")

# Slash command: Show bot statistics
@bot.tree.command(name="stats", description="View bot statistics.")
async def stats(interaction: discord.Interaction):
    total_memes_posted = len(posted_memes)
    await interaction.response.send_message(f"Total memes posted: {total_memes_posted}")

# Slash command: Show recent memes
@bot.tree.command(name="topmemes", description="View the most recent memes posted.")
async def topmemes(interaction: discord.Interaction):
    if posted_memes:
        recent_memes = list(posted_memes)[-5:]  # Last 5 memes
        await interaction.response.send_message(
            "Top 5 memes:\n" + "\n".join(recent_memes)
        )
    else:
        await interaction.response.send_message("No memes have been posted yet.")

# Slash command: Help command
@bot.tree.command(name="help", description="Display a list of available commands.")
async def help_command(interaction: discord.Interaction):
    help_text = """
    **Available Commands:**
    - /setchannel [channel]: Set the channel for memes to be posted.
    - /startmemes [channel]: Start posting memes to a specific channel.
    - /stopmemes [channel]: Stop posting memes to a specific channel.
    - /meme: Fetch and post a meme instantly.
    - /stats: View bot statistics (number of memes posted).
    - /topmemes: View the most recent memes posted.
    - /help: Display this help message.
    """
    await interaction.response.send_message(help_text)

# Background task: Post memes periodically
async def post_memes():
    while True:
        for channel_id, is_active in active_channels.items():
            if is_active:
                channel = bot.get_channel(channel_id)
                if channel:
                    meme_url, meme_title = get_meme()
                    if meme_url and meme_url not in posted_memes:
                        await channel.send(f"**{meme_title}**\n{meme_url}")
                        posted_memes.add(meme_url)
        await asyncio.sleep(60)  # Wait 1 minute before posting again

# Event: Bot is ready
@bot.event
async def on_ready():
    await bot.tree.sync()  # Sync commands with Discord
    print(f"Logged in as {bot.user}")
    asyncio.create_task(post_memes())  # Start the meme posting task

# Run the bot
bot.run(TOKEN)
