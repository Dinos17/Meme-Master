# ===== IMPORTS =====
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
import time
import random
import praw
import asyncpraw
import subprocess
from discord.app_commands import checks
from datetime import datetime, timedelta
import aiohttp
import logging

# Set logging level to ERROR to suppress WARNING and INFO messages
logging.basicConfig(level=logging.ERROR)

# ===== CONFIGURATION AND SETUP =====
TOKEN = os.getenv("BOT_TOKEN")  # Use environment variable for TOKEN
CLIENT_ID = os.getenv("REDDIT_CLIENT_ID")  # Use environment variable for client_id
CLIENT_SECRET = os.getenv("REDDIT_SECRET")  # Use environment variable for client_secret

reddit = praw.Reddit(
    client_id=CLIENT_ID,  # Use the loaded client_id
    client_secret=CLIENT_SECRET,  # Use the loaded client_secret
    user_agent="Auto Memer",
)

# Create default intents
intents = discord.Intents.default()  # Create default intents
# You can enable specific intents if needed, e.g., intents.message_content = True

# Create the bot with specific intents
bot = commands.Bot(command_prefix="/", intents=intents)  # Pass intents to the bot

# ===== GLOBAL VARIABLES =====
active_channels = {}
stopped_channels = set()
memes_posted = 0
meme_command_count = 0
command_history_list = deque(maxlen=30)
last_sync_time = None
SYNC_COOLDOWN = 60

# Define your support server channel ID
SUPPORT_CHANNEL_ID = 1333205807000453150  # Replace with your actual channel ID

# Global variable to store last answers
last_answers = []

# Global set to keep track of sent GIFs
sent_gifs = set()

# ===== UTILITY FUNCTIONS =====
def parse_time(time_str):
    time_str = time_str.lower().strip()
    if "min" in time_str:
        return int(time_str.replace("min", "").strip()) * 60
    elif "sec" in time_str:
        return int(time_str.replace("sec", "").strip())
    raise ValueError("Invalid time format. Use 'min' for minutes or 'sec' for seconds.")

def format_time(seconds):
    if seconds < 60:
        return f"{seconds} sec"
    elif seconds < 3600:
        return f"{seconds // 60} min"
    else:
        return f"{seconds // 3600} hours {(seconds % 3600) // 60} min"

async def get_meme(subreddit_name="memes"):
    # Validate subreddit_name to ensure it doesn't contain invalid characters
    if not subreddit_name or " " in subreddit_name or "https://" in subreddit_name:
        return None, "Invalid subreddit name."

    try:
        async with aiohttp.ClientSession() as session:
            headers = {
                "User-Agent": "MemeMaster v1.0 (by /u/Dinos_17)"  # Updated with your Reddit username
            }
            url = f"https://www.reddit.com/r/{subreddit_name}/hot.json?limit=50"
            async with session.get(url, headers=headers) as response:
                print(f"Fetching from: {url} - Status: {response.status}")  # Log the URL and status
                if response.status != 200:
                    return None, f"Failed to fetch memes from r/{subreddit_name}. Status code: {response.status}"

                data = await response.json()
                posts = [post for post in data['data']['children'] if post['data']['url'].endswith(("jpg", "jpeg", "png", "gif"))]

                if not posts:
                    return None, "No suitable memes found."

                post = random.choice(posts)
                return post['data']['url'], post['data']['title']

    except Exception as e:
        print(f"Error fetching meme: {e}")
        return None, None

async def get_joke():
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get("https://v2.jokeapi.dev/joke/Programming,Miscellaneous?type=twopart") as response:
                if response.status == 200:
                    joke_data = await response.json()
                    if joke_data["type"] == "twopart":
                        return joke_data["setup"], joke_data["delivery"]
                    else:
                        return joke_data["joke"], None  # For single-part jokes
                else:
                    print("Failed to fetch joke.")
                    return None, None
    except Exception as e:
        print(f"Error fetching joke: {e}")
        return None, None

# ===== CORE FUNCTIONALITY =====
async def post_meme_to_channel(channel, interval, subreddit_name):
    global memes_posted
    while True:
        if channel.id in stopped_channels:
            break
        meme_url, meme_title = await get_meme(subreddit_name)  # Remove await here
        if meme_url:
            await channel.send(f"**{meme_title}**\n{meme_url}")
            memes_posted += 1

        await asyncio.sleep(interval)

def get_server_count():
    return len(bot.guilds)  # Count the number of servers the bot has joined

# ===== EVENT HANDLERS =====
@bot.event
async def on_ready():
    print(f"Bot is ready as {bot.user.name}")
    server_count = get_server_count()  # Get the server count
    print(f"The bot is in {server_count} servers.")

    # Sync commands on startup
    try:
        global last_sync_time
        current_time = datetime.now()

        # Sync commands only if the cooldown period has passed
        if not last_sync_time or (current_time - last_sync_time).total_seconds() > SYNC_COOLDOWN:
            start_time = time.time()
            synced = await bot.tree.sync(guild=None)  # Sync globally or specify a guild for faster sync
            last_sync_time = current_time
            print(f"Synced {len(synced)} command(s) in {time.time() - start_time:.2f} seconds")
        else:
            print("Skipping command sync due to cooldown")
    except Exception as e:
        print(f"Error syncing commands: {e}")

    await bot.change_presence(status=discord.Status.online)  # Set the bot's status

@bot.event
async def on_message(message):
    if message.author.bot:
        return

    # Keyword-based trigger
    keywords = ["post a meme", "send meme"]
    if any(keyword in message.content.lower() for keyword in keywords):
        meme_url, meme_title = await get_meme("funny")  # Remove await here
        if meme_url:
            await message.channel.send(f"**{meme_title}**\n{meme_url}")
        else:
            await message.channel.send("Sorry, couldn't fetch a meme right now.")

@bot.event
async def on_interaction(interaction: discord.Interaction):
    if interaction.type == discord.InteractionType.application_command:
        command_history_list.append(
            f"/{interaction.data['name']}"
        )  # Add command to history

# ===== SLASH COMMANDS =====
@bot.tree.command(name="help", description="Show a list of all available commands.")
async def help_command(interaction: discord.Interaction):
    def generate_help_embed():
        server_count = len(bot.guilds)  # Count the number of servers the bot has joined
        embed = Embed(title="Help - Available Commands", description=f"- Bot is currently in {server_count} servers", color=discord.Color.blue())

        # Meme Commands
        embed.add_field(
            name="🎭 Meme Commands",
            value=(
                "</meme:1331251925491908791> - Fetch and post a meme with refresh option\n"
                "</meme_search:1333204607261872189> - Search for memes with specific keywords\n"
                "</top_memes:1333204607261872190> - Get top memes from a time period\n"
                "</setchannel:1325134226810736711> - Set a channel for auto-posting memes\n"

                "</stopmemes:1325622113557549127> - Stop posting memes in a channel\n"
                "</startmemes:1328806127496073250> - Resume posting memes in a channel\n"
                "</memes_by_number:1329566549736034336> - Fetch multiple memes at once"

            ),
            inline=False
        )

        # Fun Commands
        embed.add_field(
            name="🎮 Fun Commands",
            value=(
                "</random_joke:1333204607261872192> - Fetch and post a random joke\n"
                "</ping:1333204607261872193> - Check bot's latency\n"
                "</gif:1334852877360828456> - Search and display a random GIF based on a keyword"
            ),
            inline=False
        )

        # Info Commands
        embed.add_field(
            name="ℹ️ Information Commands",
            value=(
                "</serverinfo:1333204607261872194> - Display server information\n"
                "</userinfo:1333204607261872195> - Show information about a user\n"
                "</stats:1326171297440600074> - Show bot statistics\n"
                "</command_history:1331251925491908793> - View command usage history\n"
                "</server_counter:1336443568696463401> - Show how many servers the bot has joined"
            ),
            inline=False
        )

        # Utility Commands
        embed.add_field(
            name="🛠️ Utility Commands",
            value=(
                "</invite:1333204607261872191> - Get bot invite link\n"
                "</report:1333204607261872196> - Report an issue with the bot"
            ),
            inline=False
        )

        embed.set_footer(text="[Optional] parameters, <Required> parameters")
        return embed

    help_embed = generate_help_embed()

    # Create buttons
    close_button = Button(label="Close", style=discord.ButtonStyle.danger)
    invite_button = Button(
        label="Join Support Server",
        style=discord.ButtonStyle.link,
        url="https://discord.gg/QegFaGhmmq"
    )

    async def close_callback(interaction: discord.Interaction):
        await interaction.message.delete()

    close_button.callback = close_callback

    view = View()
    view.add_item(invite_button)
    view.add_item(close_button)

    # Acknowledge the interaction and send the help embed
    await interaction.response.send_message(embed=help_embed, view=view)

@bot.tree.command(name="vote", description="Vote for the bot on top.gg.")
async def vote(interaction: discord.Interaction):
    embed = Embed(
        title="Vote for Me on top.gg!",
        description="If you enjoy using this bot, please take a moment to vote for it on top.gg. Your support helps improve the bot and keep it active!\n\nClick the button below to vote.",
        color=discord.Color.green(),
    )
    vote_button = Button(
        label="Vote for Me",
        style=discord.ButtonStyle.link,
        url="https://top.gg/bot/1325110227225546854/vote",
    )
    view = View()
    view.add_item(vote_button)

    await interaction.response.send_message(embed=embed, view=view)

@bot.tree.command(name="meme", description="Fetch and post a meme from a specific subreddit.")
async def meme(
    interaction: discord.Interaction,
    subreddit: str = "memes"  # Default to r/memes but allow custom subreddits
):
    global meme_command_count  # Access the global counter
    meme_command_count += 1  # Increment the counter only here
    await interaction.response.defer()  # Defer response if meme takes time to fetch

    try:
        meme_url, meme_title = await get_meme(subreddit)  # Remove await here
        if meme_url:
            embed = discord.Embed(
                title=meme_title,
                color=discord.Color.random()
            )
            embed.set_image(url=meme_url)
            embed.set_footer(text=f"From r/{subreddit} | Requested by {interaction.user}")

            # Create buttons
            refresh_button = Button(label="New Meme", style=discord.ButtonStyle.primary, emoji="🔄")
            like_button = Button(label="Like", style=discord.ButtonStyle.success, emoji="👍")

            async def refresh_callback(button_interaction: discord.Interaction):
                global meme_command_count  # Access the global counter
                meme_command_count += 1  # Increment the counter for the new meme
                new_meme_url, new_meme_title = await get_meme(subreddit)  # Remove await here
                if new_meme_url:
                    new_embed = discord.Embed(
                        title=new_meme_title,
                        color=discord.Color.random()
                    )
                    new_embed.set_image(url=new_meme_url)
                    new_embed.set_footer(text=f"From r/{subreddit} | Requested by {interaction.user}")
                    await button_interaction.response.edit_message(embed=new_embed, view=view)
                else:
                    await button_interaction.response.send_message("Couldn't fetch a new meme!", ephemeral=True)

            async def like_callback(button_interaction: discord.Interaction):
                await button_interaction.response.send_message("Thanks for liking the meme! 😊", ephemeral=True)

            refresh_button.callback = refresh_callback
            like_button.callback = like_callback

            view = View()
            view.add_item(refresh_button)
            view.add_item(like_button)

            await interaction.followup.send(embed=embed, view=view)
        else:
            await interaction.followup.send(f"Couldn't fetch a meme from r/{subreddit}. Try another subreddit!", ephemeral=True)
    except Exception as e:
        await interaction.followup.send(f"An error occurred: {str(e)}", ephemeral=True)

@bot.tree.command(name="meme_search", description="Search for memes with specific keywords.")
async def meme_search(interaction: discord.Interaction, keyword: str):
    try:
        # First, acknowledge the interaction
        await interaction.response.defer()

        # Search in multiple meme subreddits
        subreddits = ["memes", "dankmemes", "funny"]
        found_memes = []

        for subreddit_name in subreddits:
            subreddit = reddit.subreddit(subreddit_name)
            search_results = subreddit.search(keyword, limit=5)  # Use the keyword for searching

            for post in search_results:
                if post.url.endswith(("jpg", "jpeg", "png", "gif")):
                    found_memes.append({
                        "title": post.title,
                        "url": post.url,
                        "subreddit": subreddit_name,
                        "score": post.score
                    })

        if found_memes:
            # Sort by score
            found_memes.sort(key=lambda x: x["score"], reverse=True)
            current_index = 0

            # Create embed for first meme
            embed = discord.Embed(
                title=found_memes[current_index]["title"],
                color=discord.Color.random()
            )
            embed.set_image(url=found_memes[current_index]["url"])
            embed.set_footer(
                text=f"Meme {current_index + 1}/{len(found_memes)} | "
                f"From r/{found_memes[current_index]['subreddit']} | "
                f"Score: {found_memes[current_index]['score']}"
            )

            # Create navigation buttons
            previous_button = Button(
                label="Previous",
                style=discord.ButtonStyle.primary,
                emoji="⬅️",
                disabled=True
            )
            next_button = Button(
                label="Next",
                style=discord.ButtonStyle.primary,
                emoji="➡️",
                disabled=len(found_memes) <= 1
            )

            async def previous_callback(button_interaction: discord.Interaction):
                nonlocal current_index
                current_index -= 1
                await update_meme(button_interaction)

            async def next_callback(button_interaction: discord.Interaction):
                nonlocal current_index
                current_index += 1
                await update_meme(button_interaction)

            async def update_meme(button_interaction: discord.Interaction):
                # Update embed with new meme
                new_embed = discord.Embed(
                    title=found_memes[current_index]["title"],
                    color=discord.Color.random()
                )
                new_embed.set_image(url=found_memes[current_index]["url"])
                new_embed.set_footer(
                    text=f"Meme {current_index + 1}/{len(found_memes)} | "
                    f"From r/{found_memes[current_index]['subreddit']} | "
                    f"Score: {found_memes[current_index]['score']}"
                )

                # Update button states
                previous_button.disabled = current_index == 0
                next_button.disabled = current_index == len(found_memes) - 1

                await button_interaction.response.edit_message(
                    embed=new_embed,
                    view=view
                )

            previous_button.callback = previous_callback
            next_button.callback = next_callback

            view = View()
            view.add_item(previous_button)
            view.add_item(next_button)

            await interaction.followup.send(
                f"Found {len(found_memes)} memes matching '{keyword}':",
                embed=embed,
                view=view
            )
        else:
            await interaction.followup.send(f"No memes found matching '{keyword}'.")

    except Exception as e:
        # If the interaction hasn't been acknowledged yet, acknowledge it with an error message
        if not interaction.response.is_done():
            await interaction.response.send_message(
                f"An error occurred: {str(e)}",
                ephemeral=True
            )
        # If it has been acknowledged, use followup
        else:
            await interaction.followup.send(
                f"An error occurred: {str(e)}",
                ephemeral=True
            )

@bot.tree.command(name="top_memes", description="Get top memes from the last day/week/month/year.")
async def top_memes(
    interaction: discord.Interaction,
    timeframe: str = "day",  # day, week, month, year
    count: int = 5  # How many memes to fetch
):
    valid_timeframes = ["day", "week", "month", "year"]
    if timeframe not in valid_timeframes:
        await interaction.response.send_message(
            "Invalid timeframe! Please use: day, week, month, or year.",
            ephemeral=True
        )
        return

    if count < 1 or count > 10:
        await interaction.response.send_message(
            "Please request between 1 and 10 memes.",
            ephemeral=True
        )
        return

    await interaction.response.defer()

    try:
        subreddit = reddit.subreddit("memes")
        top_posts = subreddit.top(time_filter=timeframe, limit=count)

        embeds = []
        for post in top_posts:
            if post.url.endswith(("jpg", "jpeg", "png", "gif")):
                embed = discord.Embed(
                    title=post.title,
                    color=discord.Color.random()
                )
                embed.set_image(url=post.url)
                embed.add_field(name="Score", value=f"👍 {post.score:,}", inline=True)
                embed.add_field(name="Comments", value=f"💬 {post.num_comments:,}", inline=True)
                embed.set_footer(text=f"Top meme from the last {timeframe}")
                embeds.append(embed)

        if embeds:
            await interaction.followup.send(
                f"Top {len(embeds)} memes from the last {timeframe}:",
                embeds=embeds
            )
        else:
            await interaction.followup.send("Couldn't find any suitable memes.", ephemeral=True)

    except Exception as e:
        await interaction.followup.send(f"An error occurred: {str(e)}", ephemeral=True)

@bot.tree.command(name="memes_by_number", description="Fetch a specific number of memes (max 20).")
async def memes_by_number(interaction: discord.Interaction, count: int):
    if count < 1 or count > 20:
        await interaction.response.send_message(
            "Please provide a number between 1 and 20."
        )
        return

    try:
        # Access the 'memes' subreddit
        subreddit = reddit.subreddit("memes")

        # Fetch 'count' number of posts from the subreddit
        posts = subreddit.new(limit=count)

        # Prepare a list of memes with necessary information
        memes = []
        for post in posts:
            memes.append(
                {
                    "title": post.title,
                    "url": post.url,
                    "ups": post.ups,
                    "author": post.author.name if post.author else "Unknown",
                    "postLink": f"https://www.reddit.com{post.permalink}",
                    "subreddit": post.subreddit.display_name,
                }
            )

        if not memes:
            await interaction.response.send_message(
                "Couldn't fetch memes at the moment. Please try again later."
            )
            return

        # Create embeds for each meme to display them nicely
        embeds = []
        for meme in memes:
            embed = discord.Embed(
                title=meme["title"],
                url=meme["postLink"],
                description=f"Subreddit: {meme['subreddit']}",
                color=discord.Color.green(),
            )
            embed.set_image(url=meme["url"])
            embed.set_footer(text=f"👍 {meme['ups']} | Author: {meme['author']}")
            embeds.append(embed)

        # Send the embed messages with memes to Discord, limiting to 10 embeds per message
        for i in range(0, len(embeds), 10):
            # Ensure only one response is sent for the interaction
            if i == 0:
                await interaction.response.send_message(
                    f"Here are your memes {i + 1}-{min(i + 10, len(embeds))}:",
                    embeds=embeds[i:i + 10]
                )
            else:
                await interaction.followup.send(
                    f"Here are your memes {i + 1}-{min(i + 10, len(embeds))}:",
                    embeds=embeds[i:i + 10]
                )
    except asyncpraw.exceptions.PRAWException as e:
        print(f"Error fetching memes: {e}")
        await interaction.followup.send(
            "There was an error fetching memes. Please try again later."
        )

@bot.tree.command(name="invite", description="Get the invite link to add the bot to your server.")
async def invite(interaction: discord.Interaction):
    bot_invite_link = f"https://discord.com/oauth2/authorize?client_id={bot.user.id}&permissions=8&scope=bot%20applications.commands"

    # Create embed
    embed = discord.Embed(
        title="🤖 Invite Me to Your Server!",
        description="Click the button below to add me to your server and start enjoying memes and jokes!",
        color=discord.Color.blue()
    )
    embed.add_field(
        name="Features",
        value="• Auto-posting memes\n• Random jokes\n• Easy to use commands\n• And much more!",
        inline=False
    )
    embed.set_footer(text=f"Requested by {interaction.user}")

    # Create buttons
    invite_button = Button(
        label="Add to Server", 
        style=discord.ButtonStyle.link,
        url=bot_invite_link,
        emoji="➕"
    )
    support_button = Button(
        label="Support Server",
        style=discord.ButtonStyle.link,
        url="https://discord.gg/QegFaGhmmq",
        emoji="❓"
    )

    # Create view and add buttons
    view = View()
    view.add_item(invite_button)
    view.add_item(support_button)

    # Send the message (not ephemeral)
    await interaction.response.send_message(embed=embed, view=view)

@bot.tree.command(name="setchannel", description="Set the channel for memes to be posted.")
async def setchannel(interaction: discord.Interaction, channel: discord.TextChannel, search_query: str, interval: str):
    try:
        # Ensure the channel is a valid TextChannel
        if not isinstance(channel, discord.TextChannel):
            await interaction.response.send_message("Invalid channel specified. Please mention a valid text channel.", ephemeral=True)
            return

        search_query = search_query.strip().lower()
        time_in_seconds = parse_time(interval)

        # Log the channel and parameters
        print(f"Setting channel: {channel.id}, Search Query: '{search_query}', Interval: {time_in_seconds} seconds")

        active_channels[channel.id] = {
            "channel": channel,
            "search_query": search_query,
            "interval": time_in_seconds
        }

        # Start posting memes in the specified channel
        asyncio.create_task(post_meme_to_channel(channel, time_in_seconds, search_query))

        await interaction.response.send_message(f"Set {channel.mention} as a meme channel with search query '{search_query}' and an interval of {interval}.")
    except ValueError:
        await interaction.response.send_message("Invalid time format. Use 'min' for minutes or 'sec' for seconds.")

@bot.tree.command(name="stopmemes", description="Stop posting memes in a channel.")
async def stopmemes(interaction: discord.Interaction, channel: discord.TextChannel):
    if channel.id in active_channels:
        stopped_channels.add(channel.id)
        await interaction.response.send_message(
            f"Stopped posting memes in {channel.mention}."
        )
    else:
        await interaction.response.send_message(
            f"{channel.mention} is not set up for meme posting."
        )

@bot.tree.command(name="startmemes", description="Resume posting memes in a channel.")
async def startmemes(
    interaction: discord.Interaction, 
    channel: discord.TextChannel, 
    subreddit_name: str, 
    interval: str  # Added interval parameter
):
    if channel.id in active_channels and channel.id in stopped_channels:
        stopped_channels.remove(channel.id)
        interval = active_channels[channel.id]["interval"]
        # Pass subreddit_name to the post_meme_to_channel function
        asyncio.create_task(post_meme_to_channel(channel, interval, subreddit_name))
        await interaction.response.send_message(
            f"Resumed posting memes from {subreddit_name} in {channel.mention}."
        )
    else:
        await interaction.response.send_message(
            f"{channel.mention} is not set up or already active."
        )

@bot.tree.command(name="stats", description="Show bot statistics.")
async def stats(interaction: discord.Interaction):
    def generate_stats_embed():
        embed = Embed(title="Bot Statistics", color=discord.Color.green())
        embed.add_field(name="Memes Posted", value=str(memes_posted), inline=True)
        embed.add_field(name="Meme Commands Used", value=str(meme_command_count), inline=True)
        embed.add_field(
            name="Active Channels", value=str(len(active_channels)), inline=True
        )
        embed.add_field(
            name="Stopped Channels", value=str(len(stopped_channels)), inline=True
        )

        if active_channels:
            sample_channel = list(active_channels.values())[0]
            interval = sample_channel["interval"]
            formatted_interval = format_time(interval)
            embed.add_field(
                name="Sample Interval", value=formatted_interval, inline=False
            )

        avatar_url = (
            bot.user.avatar.url if bot.user.avatar else bot.user.default_avatar.url
        )
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

@bot.tree.command(name="command_history", description="View the history of commands used.")
async def command_history(interaction: discord.Interaction):
    if not command_history_list:
        await interaction.response.send_message("No commands have been used yet.")
        return

    embed = discord.Embed(
        title="Command History",
        description="Here are the last 30 commands used:",
        color=discord.Color.green()
    )

    # Group commands and count their occurrences
    command_counts = {}
    for cmd in command_history_list:
        command_counts[cmd] = command_counts.get(cmd, 0) + 1

    # Format the command history
    history_text = "\n".join(f"**{cmd}**: {count} times" for cmd, count in command_counts.items())

    # Add the command history to the embed
    if history_text:
        embed.add_field(name="Commands Used", value=history_text, inline=False)
    else:
        embed.add_field(name="Commands Used", value="No commands used yet.", inline=False)

    # Add a footer for additional information
    embed.set_footer(text=f"Requested by {interaction.user.name}", icon_url=interaction.user.avatar.url)

    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="random_joke", description="Fetch and post a random joke. Optionally specify a channel.")
async def random_joke(
    interaction: discord.Interaction, 
    channel: discord.TextChannel = None
):
    # Check if user has permission to send messages in the specified channel
    target_channel = channel or interaction.channel

    if not target_channel.permissions_for(interaction.user).send_messages:
        await interaction.response.send_message(
            f"You don't have permission to send messages in {target_channel.mention}",
            ephemeral=True
        )
        return

    setup, punchline = await get_joke()

    if setup and punchline:
        # Create embed
        embed = discord.Embed(
            title="😄 Random Joke",
            color=discord.Color.blue()
        )
        embed.add_field(name="Setup", value=setup, inline=False)
        embed.add_field(name="Punchline", value="||" + punchline + "||", inline=False)
        embed.set_footer(text=f"Requested by {interaction.user}")

        # Create buttons
        new_joke_button = Button(label="New Joke", style=discord.ButtonStyle.primary, emoji="🎲")

        async def new_joke_callback(button_interaction: discord.Interaction):
            new_setup, new_punchline = await get_joke()
            if new_setup and new_punchline:
                new_embed = discord.Embed(
                    title="😄 Random Joke",
                    color=discord.Color.blue()
                )
                new_embed.add_field(name="Setup", value=new_setup, inline=False)
                new_embed.add_field(name="Punchline", value="||" + new_punchline + "||", inline=False)
                new_embed.set_footer(text=f"Requested by {interaction.user}")
                await button_interaction.response.edit_message(embed=new_embed, view=view)
            else:
                await button_interaction.response.send_message("Sorry, couldn't fetch a new joke right now.", ephemeral=True)

        new_joke_button.callback = new_joke_callback

        view = View()
        view.add_item(new_joke_button)

        # Send to specified channel
        if channel:
            await interaction.response.send_message(
                f"Joke sent to {channel.mention}!", 
                ephemeral=True
            )
            await channel.send(embed=embed, view=view)
        else:
            await interaction.response.send_message(embed=embed, view=view)
    else:
        await interaction.response.send_message("Sorry, couldn't fetch a joke right now.", ephemeral=True)

@bot.tree.command(name="ping", description="Check the bot's latency.")
async def ping(interaction: discord.Interaction):
    latency = round(bot.latency * 1000)  # Convert to milliseconds
    embed = discord.Embed(
        title="🏓 Pong!",
        description=f"Bot Latency: `{latency}ms`",
        color=discord.Color.green() if latency < 200 else discord.Color.red()
    )
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="serverinfo", description="Display information about the server.")
async def serverinfo(interaction: discord.Interaction):
    guild = interaction.guild

    embed = discord.Embed(
        title=f"📊 {guild.name} Server Information",
        color=discord.Color.blue()
    )

    # Check if the owner is available
    owner_mention = guild.owner.mention if guild.owner else "Unknown"
    embed.add_field(name="Owner", value=owner_mention, inline=True)
    embed.add_field(name="Created On", value=guild.created_at.strftime("%B %d, %Y"), inline=True)
    embed.add_field(name="Server ID", value=guild.id, inline=True)

    # Member stats
    total_members = len(guild.members)
    humans = len([m for m in guild.members if not m.bot])
    bots = total_members - humans
    embed.add_field(name="Total Members", value=total_members, inline=True)
    embed.add_field(name="Humans", value=humans, inline=True)
    embed.add_field(name="Bots", value=bots, inline=True)

    # Channel stats
    text_channels = len(guild.text_channels)
    voice_channels = len(guild.voice_channels)
    categories = len(guild.categories)
    embed.add_field(name="Text Channels", value=text_channels, inline=True)
    embed.add_field(name="Voice Channels", value=voice_channels, inline=True)
    embed.add_field(name="Categories", value=categories, inline=True)

    if guild.icon:
        embed.set_thumbnail(url=guild.icon.url)

    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="userinfo", description="Display information about a user.")
async def userinfo(interaction: discord.Interaction, user: discord.Member = None):
    user = user or interaction.user

    embed = discord.Embed(
        title=f"👤 User Information for {user.name}",
        color=user.color if user.color != discord.Color.default() else discord.Color.blue()
    )

    embed.add_field(name="User ID", value=user.id, inline=True)
    embed.add_field(name="Nickname", value=user.nick or "None", inline=True)
    embed.add_field(name="Bot", value="Yes" if user.bot else "No", inline=True)

    embed.add_field(name="Account Created", value=user.created_at.strftime("%B %d, %Y"), inline=True)
    embed.add_field(name="Joined Server", value=user.joined_at.strftime("%B %d, %Y"), inline=True)

    roles = [role.mention for role in user.roles if role.name != "@everyone"]
    embed.add_field(name=f"Roles [{len(roles)}]", value=" ".join(roles) if roles else "None", inline=False)

    embed.set_thumbnail(url=user.display_avatar.url)

    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="report", description="Report an issue with the bot.")
async def report(interaction: discord.Interaction, issue: str):
    # Check if the command is used in a guild context
    if interaction.guild is None:
        await interaction.response.send_message(
            "This command cannot be used in direct messages. Please use it in a server.",
            ephemeral=True
        )
        return

    # Create embed for the report
    embed = discord.Embed(
        title="🐛 Bug Report",
        description=issue,
        color=discord.Color.red(),
        timestamp=datetime.now()
    )
    embed.add_field(name="Reported by", value=f"{interaction.user.mention} ({interaction.user.id})")
    embed.add_field(name="Server", value=f"{interaction.guild.name} ({interaction.guild.id})")

    # Get the support channel
    support_channel = bot.get_channel(SUPPORT_CHANNEL_ID)

    if support_channel:
        # Send the report to the support channel
        report_message = await support_channel.send(embed=embed)

        # Create buttons for staff to interact with
        acknowledge_button = Button(label="Acknowledge", style=discord.ButtonStyle.success)
        resolve_button = Button(label="Resolve", style=discord.ButtonStyle.primary)

        async def acknowledge_callback(button_interaction: discord.Interaction):
            await button_interaction.response.send_message("Report acknowledged.", ephemeral=True)
            await report_message.add_reaction("✅")  # Add a checkmark reaction to the report message

        async def resolve_callback(button_interaction: discord.Interaction):
            await button_interaction.response.send_message("Report resolved.", ephemeral=True)
            await report_message.add_reaction("🔒")  # Add a lock reaction to indicate resolution

        acknowledge_button.callback = acknowledge_callback
        resolve_button.callback = resolve_callback

        view = View()
        view.add_item(acknowledge_button)
        view.add_item(resolve_button)

        # Edit the report message to include the buttons
        await report_message.edit(view=view)

        # Send confirmation to the user
        await interaction.response.send_message(
            "Thank you for your report! Our team will look into it.",
            ephemeral=True
        )
    else:
        await interaction.response.send_message(
            "There was an error sending your report. Please try again later.",
            ephemeral=True
        )

@bot.tree.command(name="8ball", description="🎱 Ask a question and receive an answer from the magic 8-ball.")
async def eight_ball(interaction: discord.Interaction, question: str):
    affirmative_answers = [
        "It is certain",
        "It is decidedly so",
        "Without a doubt",
        "Yes definitely",
        "You may rely on it",
        "As I see it, yes",
        "Most likely",
        "Outlook good",
        "Yes",
        "Signs point to yes"
    ]

    non_committal_answers = [
        "Reply hazy, try again",
        "Ask again later",
        "Better not tell you now",
        "Cannot predict now",
        "Concentrate and ask again"
    ]

    negative_answers = [
        "Don't count on it",
        "My reply is no",
        "My sources say no",
        "Outlook not so good",
        "Very doubtful"
    ]

    # Randomly choose a category and then a response from that category
    category_choice = random.choices(
        ["affirmative", "non_committal", "negative"],
        weights=[0.5, 0.3, 0.2],  # Adjust weights as needed
        k=1
    )[0]

    if category_choice == "affirmative":
        answer = random.choice(affirmative_answers)
    elif category_choice == "non_committal":
        answer = random.choice(non_committal_answers)
    else:
        answer = random.choice(negative_answers)

    # Store the answer in the history
    last_answers.append(answer)
    if len(last_answers) > 5:  # Limit to the last 5 answers
        last_answers.pop(0)

    # Create an embed for the response
    embed = discord.Embed(
        title="🎱 Magic 8-Ball",
        description=f"**Question:** {question}\n**Answer:** {answer}",
        color=discord.Color.random()  # Random color for a more vibrant look
    )
    embed.set_footer(text="Type your next question in the chat!")
    embed.set_thumbnail(url="https://example.com/magic8ball.png")  # Add a thumbnail image (replace with a valid URL)

    # Create a button for showing last answers
    history_button = Button(label="Show Last Answers", style=discord.ButtonStyle.secondary)

    async def history_callback(button_interaction: discord.Interaction):
        # Display the last answers
        if last_answers:
            history_message = "\n".join(f"- {ans}" for ans in last_answers)
            await button_interaction.response.send_message(f"Last answers:\n{history_message}", ephemeral=True)
        else:
            await button_interaction.response.send_message("No previous answers available.", ephemeral=True)

    history_button.callback = history_callback

    view = View()
    view.add_item(history_button)

    await interaction.response.send_message(embed=embed, view=view)

@bot.tree.command(name="gif", description="Search and display a random GIF based on a specified keyword.")
async def gif(interaction: discord.Interaction, keyword: str):
    await interaction.response.defer()  # Acknowledge the interaction

    async with aiohttp.ClientSession() as session:
        try:
            # Removed print statement for fetching GIFs
            async with session.get(f"https://api.giphy.com/v1/gifs/search?api_key=upEsZXwiOekDKkRmMwCRpKUHSLz3OXzu&q={keyword}&limit=5&offset=0&rating=g&lang=en") as response:
                response.raise_for_status()  # Raise an error for bad responses
                data = await response.json()

                if data['data']:
                    available_gifs = [gif for gif in data['data'] if gif['images']['original']['url'] not in sent_gifs]

                    if available_gifs:
                        selected_gif = random.choice(available_gifs)
                        gif_url = selected_gif['images']['original']['url']  # Get the selected GIF URL
                        sent_gifs.add(gif_url)  # Add the GIF URL to the sent list
                        await interaction.followup.send(gif_url)
                    else:
                        await interaction.followup.send("All available GIFs have already been sent for this keyword.")
                else:
                    await interaction.followup.send("No GIFs found for that keyword.")
        except aiohttp.ClientError as e:
            await interaction.followup.send(f"An error occurred while fetching GIFs: {str(e)}")
        except Exception as e:
            await interaction.followup.send(f"An unexpected error occurred: {str(e)}")

@bot.tree.command(name="server_counter", description="Show how many servers the bot has joined.")
async def server_counter(interaction: discord.Interaction):
    server_count = len(bot.guilds)  # Count the number of servers the bot has joined
    await interaction.response.send_message(f"The bot is currently in {server_count} servers.")

# ===== MAIN EXECUTION =====
def run_bot():
    try:
        bot.run(TOKEN)
    except Exception as e:
        print(f"Error occurred: {e}")
        sys.exit(1)

if __name__ == "__main__":
    run_bot()
