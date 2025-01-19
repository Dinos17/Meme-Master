import discord
from discord.ext import commands
from discord.ui import Button, View
from discord import Embed
from discord import app_commands
import asyncio
import requests
from collections import deque
import os
import sys
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import time
import random
import praw



TOKEN = os.getenv("BOT_TOKEN")

# Initialize the bot with no intents (default intents)
bot = commands.Bot(command_prefix="!", intents=discord.Intents.default())

# Global variables
active_channels = {}  # Stores active channels and their intervals
stopped_channels = set()  # Channels where meme posting is paused
memes_posted = 0  # Counter for memes posted
command_history_list = deque(maxlen=30)  # Stores last 30 commands
recent_memes = []  # Stores recently posted memes

# Watchdog Event Handler
class BotFileChangeHandler(FileSystemEventHandler):
    def on_modified(self, event):
        if event.src_path.endswith('.py'):  # Only restart if a Python file changes
            print(f"File {event.src_path} has been modified. Restarting bot...")
            restart_bot()

def restart_bot():
    """Function to restart the bot."""
    print("Restarting bot...")
    os.execl(sys.executable, sys.executable, *sys.argv)

# Function to start the watchdog
def start_watchdog(path_to_watch='.'):
    event_handler = BotFileChangeHandler()
    observer = Observer()
    observer.schedule(event_handler, path=path_to_watch, recursive=False)
    observer.start()
    print("Watchdog started. Monitoring for file changes...")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()

# Function to fetch memes from an API based on a search term
# Step 1: Update the function definition
def get_meme(subreddit_name="memes"):
    try:
        # Fetch subreddit posts
        subreddit = reddit.subreddit(subreddit_name)  # Change `search_query` to `subreddit_name`
        posts = [post for post in subreddit.hot(limit=50) if not post.stickied and not post.over_18 and post.url.endswith(("jpg", "jpeg", "png", "gif"))]
        
        if not posts:
            return None, "No suitable memes found."
        
        # Select a random post from the list of fetched posts
        post = random.choice(posts)
        return post.url, post.title
        
    except Exception as e:
        print(f"Error fetching meme: {e}")
        return None, None

# Helper function to parse time input (converts "5 min" to seconds)
def parse_time(time_str):
    time_str = time_str.lower().strip()
    if "min" in time_str:
        return int(time_str.replace("min", "").strip()) * 60
    elif "sec" in time_str:
        return int(time_str.replace("sec", "").strip())
    raise ValueError("Invalid time format. Use 'min' for minutes or 'sec' for seconds.")

# Helper function to convert seconds back into human-readable format
def format_time(seconds):
    if seconds < 60:
        return f"{seconds} sec"
    elif seconds < 3600:
        return f"{seconds // 60} min"
    else:
        return f"{seconds // 3600} hours {(seconds % 3600) // 60} min"

# Function to post memes to a channel at intervals, with a search query
async def post_meme_to_channel(channel, interval, subreddit_name):
    global memes_posted, recent_memes
    while True:
        if channel.id in stopped_channels:
            break
        meme_url, meme_title = get_meme(subreddit_name)  # Use `subreddit_name` here
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
    def generate_help_embed():
        embed = Embed(title="Help - Available Commands", color=discord.Color.blue())
        embed.add_field(name="/meme", value="Fetch and post a meme instantly.", inline=False)
        embed.add_field(name="/stats", value="Show bot statistics.", inline=False)
        embed.add_field(name="/setchannel", value="Set a channel for posting memes at intervals.", inline=False)
        embed.add_field(name="/stopmemes", value="Stop posting memes in a channel.", inline=False)
        embed.add_field(name="/startmemes", value="Resume posting memes in a channel.", inline=False)
        embed.add_field(name="/recentmemes", value="Show the last 10 memes posted.", inline=False)
        embed.add_field(name="/command_history", value="View the history of commands used.", inline=False)
        embed.add_field(name="/vote", value="Vote for the bot on top.gg.", inline=False)
        embed.add_field(name="/memes_by_number", value="Fetch a specific number of memes (up to 50).", inline=False)
        return embed

    help_embed = generate_help_embed()
    close_button = Button(label="Close", style=discord.ButtonStyle.danger)
    invite_button = Button(label="Join Our Support Server", style=discord.ButtonStyle.link, url="https://discord.gg/QegFaGhmmq")

    async def close_callback(interaction: discord.Interaction):
        await interaction.message.delete()

    close_button.callback = close_callback

    view = View()
    view.add_item(invite_button)
    view.add_item(close_button)

    await interaction.response.send_message(embed=help_embed, view=view)

@bot.tree.command(name="sync", description="Manually sync bot commands.")
async def sync(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)  # Defer the response to avoid timeout

    try:
        # Create initial embed
        progress_embed = Embed(title="🔄 Sync in progress...", color=discord.Color.blue())
        progress_embed.add_field(name="Guild Sync", value="0%", inline=False)
        progress_embed.add_field(name="Global Sync", value="0%", inline=False)
        progress_embed.set_footer(text="Please wait while the bot syncs.")
        progress_message = await interaction.followup.send(embed=progress_embed)

        # Simulated custom progress steps for updating embed fields
        progress_steps = [0, 12, 27, 29, 38, 40, 45, 56, 64, 71, 74, 78, 83, 86, 89, 92, 95, 99, 100]
        total_steps = len(progress_steps)
        step_delay = 2  # Increased delay in seconds for each progress update to make it slower

        # Sync guild-specific commands and update progress after syncing
        guild_synced = await bot.tree.sync(guild=interaction.guild)
        guild_synced_count = len(guild_synced)

        # Update embed with progress for guild sync
        for step in range(total_steps):
            progress_embed.set_field_at(0, name="Guild Sync", value=f"{progress_steps[step]}%", inline=False)
            await progress_message.edit(embed=progress_embed)
            await asyncio.sleep(step_delay)

        # Sync global commands and update progress after syncing
        global_synced = await bot.tree.sync()
        global_synced_count = len(global_synced)

        # Update embed with progress for global sync
        for step in range(total_steps):
            progress_embed.set_field_at(1, name="Global Sync", value=f"{progress_steps[step]}%", inline=False)
            await progress_message.edit(embed=progress_embed)
            await asyncio.sleep(step_delay)

        # Final sync message after both steps are completed
        await interaction.followup.send(
            f"✅ The bot has been successfully refreshed for **{interaction.guild.name}**!\n\n"
            f"**Server-Specific Commands Synced:** {guild_synced_count}.\n"
            f"**Global Commands Synced:** {global_synced_count}."
        )

        # Final 100% progress message
        progress_embed.set_field_at(0, name="Guild Sync", value="100%", inline=False)
        progress_embed.set_field_at(1, name="Global Sync", value="100%", inline=False)
        await progress_message.edit(embed=progress_embed)

    except Exception as e:
        # Handle and display any errors that occur during the sync process
        await interaction.followup.send(f"❌ An error occurred while refreshing the bot: {e}")

@bot.tree.command(name="vote", description="Vote for the bot on top.gg.")
async def vote(interaction: discord.Interaction):
    embed = Embed(
        title="Vote for Me on top.gg!",
        description="If you enjoy using this bot, please take a moment to vote for it on top.gg. Your support helps improve the bot and keep it active!\n\nClick the button below to vote.",
        color=discord.Color.green()
    )
    vote_button = Button(label="Vote for Me", style=discord.ButtonStyle.link, url="https://top.gg/bot/1325110227225546854/vote")
    view = View()
    view.add_item(vote_button)

    await interaction.response.send_message(embed=embed, view=view)

# Command: /meme - Fetch and post a meme instantly.
@bot.tree.command(name="meme", description="Fetch and post a meme instantly from a specified subreddit.")
async def meme(interaction: discord.Interaction, subreddit_name: str):
    global memes_posted
    await interaction.response.defer()

    # Use `subreddit_name` to fetch the meme from the correct subreddit
    meme_url, meme_title = get_meme(subreddit_name)  # Ensure `subreddit_name` is passed here

    if meme_url:
        memes_posted += 1
        await interaction.followup.send(f"**{meme_title}**\n{meme_url}")
    else:
        await interaction.followup.send("Sorry, couldn't fetch a meme right now.")

# Function to fetch a joke from an API
def get_joke():
    url = "https://official-joke-api.appspot.com/random_joke"
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        return data["setup"], data["punchline"]
    except requests.exceptions.RequestException as e:
        print(f"Error fetching joke: {e}")
        return None, None

# /joke command to fetch and post a random joke
@bot.tree.command(name="joke", description="Fetch and post a random joke.")
async def joke(interaction: discord.Interaction):
    setup, punchline = get_joke()
    if setup and punchline:
        await interaction.response.send_message(f"**{setup}**\n*{punchline}*")
    else:
        await interaction.response.send_message("Sorry, couldn't fetch a joke right now.")

@bot.tree.command(name="memes_by_number", description="Fetch a specific number of memes (max 50).")
async def memes_by_number(interaction: discord.Interaction, count: int):
    if count < 1 or count > 50:
        await interaction.response.send_message("Please provide a number between 1 and 50.")
        return

    try:
        response = requests.get("https://meme-api.com/gimme/50")  # Fetch 50 memes
        response.raise_for_status()
        data = response.json()
        memes = data.get("memes", [])[:count]  # Get only the requested number of memes

        if not memes:
            await interaction.response.send_message("Couldn't fetch memes at the moment. Please try again later.")
            return

        embeds = []
        for meme in memes:
            embed = Embed(
                title=meme["title"],
                url=meme["postLink"],
                description=f"Subreddit: {meme['subreddit']}",
                color=discord.Color.green(),
            )
            embed.set_image(url=meme["url"])
            embed.set_footer(text=f"👍 {meme['ups']} | Author: {meme['author']}")
            embeds.append(embed)

        await interaction.response.send_message(f"Here are your {count} memes:", embeds=embeds)
    except requests.exceptions.RequestException as e:
        print(f"Error fetching memes: {e}")
        await interaction.response.send_message("There was an error fetching memes. Please try again later.")

# Step 3: Modify the /setchannel command
@bot.tree.command(name="setchannel", description="Set the channel for memes to be posted.")
async def setchannel(interaction: discord.Interaction, channel: discord.TextChannel, subreddit_name: str, interval: str):
    try:
        # Convert subreddit_name to lowercase to ensure case-insensitivity
        subreddit_name = subreddit_name.strip().lower()

        time_in_seconds = parse_time(interval)
        active_channels[channel.id] = {"channel": channel, "subreddit_name": subreddit_name, "interval": time_in_seconds}
        asyncio.create_task(post_meme_to_channel(channel, time_in_seconds, subreddit_name))  # Pass `subreddit_name`
        await interaction.response.send_message(f"Set {channel.mention} as a meme channel with subreddit '{subreddit_name}' and an interval of {interval}.")
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
    def generate_stats_embed():
        embed = Embed(title="Bot Statistics", color=discord.Color.green())
        embed.add_field(name="Memes Posted", value=str(memes_posted), inline=True)
        embed.add_field(name="Active Channels", value=str(len(active_channels)), inline=True)
        embed.add_field(name="Stopped Channels", value=str(len(stopped_channels)), inline=True)

        if active_channels:
            sample_channel = list(active_channels.values())[0]
            interval = sample_channel['interval']
            formatted_interval = format_time(interval)
            embed.add_field(name="Sample Interval", value=formatted_interval, inline=False)

        avatar_url = bot.user.avatar.url if bot.user.avatar else bot.user.default_avatar.url
        embed.set_thumbnail(url=avatar_url)
        return embed

    initial_embed = generate_stats_embed()

    refresh_button = Button(label="Refresh Stats", style=discord.ButtonStyle.primary)

    async def refresh_callback(interaction: discord.Interaction):
        updated_embed = generate_stats_embed()
        await interaction.response.edit_message(embed=updated_embed, view=view)

    refresh_button.callback = refresh_callback

    view = View()
    view.add_item(refresh_button)

    await interaction.response.send_message(embed=initial_embed, view=view)

@bot.tree.command(name="recentmemes", description="Show the last 10 memes posted.")
async def recentmemes(interaction: discord.Interaction):
    if recent_memes:
        embed = discord.Embed(title="Recent Memes", color=discord.Color.green())
        for meme in recent_memes:
            embed.add_field(name=meme["title"], value=meme["url"], inline=False)
        await interaction.response.send_message(embed=embed)
    else:
        await interaction.response.send_message("No memes have been posted yet.")

# Command to view the history of commands used
# Command to view the history of commands used
@bot.tree.command(name="command_history", description="View the history of commands used.")
async def command_history(interaction: discord.Interaction):
    # Creating an embed to show the command history
    embed = discord.Embed(title="Command History", color=discord.Color.blue())

    # If there are commands in the history, list them
    if command_history_list:
        # Add each command to the embed
        for command in command_history_list:
            embed.add_field(name="Command", value=f"/{command}", inline=False)
    else:
        # If no commands are in history
        embed.add_field(name="No History", value="No commands have been used yet.", inline=False)

    # Create a "Clear History" button to clear the history
    clear_button = Button(label="Clear History", style=discord.ButtonStyle.danger)

    # Create a refresh button to refresh the embed
    refresh_button = Button(label="Refresh", style=discord.ButtonStyle.primary)

    # Callback function to clear the history
    async def clear_history_callback(interaction: discord.Interaction):
        command_history_list.clear()  # Clear the command history
        await interaction.response.send_message("Command history has been cleared.", ephemeral=True)
        # Refresh the embed after clearing
        await interaction.message.edit(embed=embed)

    # Callback function for the refresh button
    async def refresh_callback(interaction: discord.Interaction):
        # Refresh the embed
        await interaction.response.edit_message(embed=embed)

    clear_button.callback = clear_history_callback
    refresh_button.callback = refresh_callback

    # Add the buttons to the view
    view = View()
    view.add_item(clear_button)
    view.add_item(refresh_button)

    # Send the embed with buttons as a response
    await interaction.response.send_message(embed=embed, view=view)

# Event listener to track command usage
@bot.event
async def on_interaction(interaction: discord.Interaction):
    if interaction.type == discord.InteractionType.application_command:
        command_history_list.append(f"/{interaction.data['name']}")  # Add command to history

# Event to sync commands and handle updates
@bot.event
async def on_ready():
    await bot.tree.sync()  # Sync commands when the bot is ready
    print(f"Bot is ready as {bot.user}")
    await bot.change_presence(status=discord.Status.online)  # Set the bot's status

# Run the bot with the watchdog
def run_bot():
    try:
        # Start the bot directly without the watchdog for testing
        bot.run(TOKEN)
    except Exception as e:
        print(f"Error occurred: {e}")
        sys.exit(1)

# Run the bot using the token
run_bot()