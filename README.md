# Discord Meme Bot ![Discord Meme Bot](https://img.shields.io/badge/Discord-Bot-blue?style=flat&logo=discord)

A Discord bot built using Python and the discord.py library. This bot provides various functionalities, including meme fetching, joke telling, and command history tracking.

## Features

- Set a specific channel to receive memes using a slash command.
- Automatically fetches and posts memes every 10 seconds.
- Fetch random jokes and GIFs.
- Command history tracking.

## Setup

### Prerequisites

- Python 3.12.8
- A Discord account and a server where you have permission to add bots.
- A Discord bot token. You can create a bot and get a token from the [Discord Developer Portal](https://discord.com/developers/applications).

### Installation

1. Clone the repository:  
   ```bash
   git clone https://github.com/Dinos17/Auto-memer.git  
   cd Auto-memer
   ```

2. Install the required packages:  
   ```bash
   pip install -r requirements.txt
   ```

3. Set up your environment variable for the Discord bot token:  
   On Windows:  
   ```bash
   set DISCORD_TOKEN=your_token_here  
   ```  
   On macOS/Linux:  
   ```bash
   export DISCORD_TOKEN=your_token_here
   ```

4. Run the bot:  
   ```bash
   python bot.py
   ```

## Usage

- Use the `/setchannel` slash command in your Discord server to specify which channel should receive memes.
- The bot will start posting memes to the specified channel every 10 seconds.
- Use `/random_joke` to fetch a random joke.
- Use `/gif [keyword]` to search and display a random GIF based on a specified keyword.
- Use `/command_history` to view the history of commands used.

## Invitation Links

- **Invite the Bot**: [Add the Discord Meme Bot to your server](https://discord.com/oauth2/authorize?client_id=1325110227225546854&permissions=2147600384&integration_type=0&scope=bot+applications.commands)
- **Join the Support Server**: [Join our Discord Server](https://discord.gg/QegFaGhmmq)

## Deployment

- The bot can be deployed on platforms that support Python, such as Heroku. Ensure the `Procfile` is correctly set up for deployment.

## Files

- `bot.py`: The main bot script.
- `Procfile`: Configuration for deploying the bot as a worker.
- `requirements.txt`: Python dependencies.
- `runtime.txt`: Specifies the Python version.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## About

This bot is designed to enhance your Discord experience by providing fun and engaging content through memes, jokes, and GIFs.

## Acknowledgments

- [discord.py](https://discordpy.readthedocs.io/en/stable/) - The library used to interact with the Discord API.
- [PRAW](https://praw.readthedocs.io/en/latest/) - The Python Reddit API Wrapper for fetching memes from Reddit.
- [aiohttp](https://docs.aiohttp.org/en/stable/) - Asynchronous HTTP client for making API requests.
