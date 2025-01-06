import discord
from discord.ext import commands
from discord import app_commands
import requests
import os

# Get the bot token from environment variables
TOKEN = os.getenv("DISCORD_TOKEN")  # Replace with your bot token if needed

# Initialize the bot with necessary intents
intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)

# Dictionary to track channel statuses
channel_status = {}  # {channel_id: is_active}

# Function to fetch a meme from the internet
def get_meme():
    url = "https://meme-api.com/gimme"
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
        meme_url = data["url"]
        meme_title = data["title"]
        return meme_url, meme_title
    return None, None

# Slash command to set the channel for memes
@bot.tree.command(name="setchannel", description="Set the channel for memes.")
async def setchannel(interaction: discord.Interaction, channel: discord.TextChannel):
    channel_id = channel.id
    if channel_id in channel_status:
        if not channel_status[channel_id]:
            await interaction.response.send_message(
                f"{channel.mention} is already set up for memes but is currently stopped. "
                f"To resume posting memes, use `/startmemes`."
            )
        else:
            await interaction.response.send_message(
                f"{channel.mention} is already set up and active for memes."
            )
    else:
        channel_status[channel_id] = False  # Initially set to stopped
        await interaction.response.send_message(
            f"Meme channel has been set to {channel.mention}. To start posting memes, use `/startmemes`."
        )

# Slash command to start posting memes
@bot.tree.command(name="startmemes", description="Start posting memes to a specific channel.")
async def startmemes(interaction: discord.Interaction, channel: discord.TextChannel):
    channel_id = channel.id
    if channel_id in channel_status:
        if channel_status[channel_id]:
            await interaction.response.send_message(
                f"Memes are already active in {channel.mention}."
            )
        else:
            channel_status[channel_id] = True
            meme_url, meme_title = get_meme()
            if meme_url:
                await channel.send(f"**{meme_title}**\n{meme_url}")
                await interaction.response.send_message(
                    f"Started posting memes in {channel.mention}."
                )
            else:
                await interaction.response.send_message(
                    f"Failed to fetch a meme. Please try again later."
                )
    else:
        await interaction.response.send_message(
            f"{channel.mention} is not set up for memes. Use `/setchannel` first."
        )

# Slash command to stop posting memes
@bot.tree.command(name="stopmemes", description="Stop posting memes in a specific channel.")
async def stopmemes(interaction: discord.Interaction, channel: discord.TextChannel):
    channel_id = channel.id
    if channel_id in channel_status:
        if not channel_status[channel_id]:
            await interaction.response.send_message(
                f"Memes are already stopped in {channel.mention}."
            )
        else:
            channel_status[channel_id] = False
            await interaction.response.send_message(
                f"Stopped posting memes in {channel.mention}."
            )
    else:
        await interaction.response.send_message(
            f"{channel.mention} is not set up for memes. Use `/setchannel` first."
        )

# Event triggered when the bot logs in successfully
@bot.event
async def on_ready():
    await bot.tree.sync()  # Sync slash commands
    print(f'Logged in as {bot.user}')

# Run the bot
bot.run(TOKEN)
