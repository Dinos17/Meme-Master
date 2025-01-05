# Discord Meme Bot

This is a Discord bot that posts memes to a specified channel at regular intervals. It uses the Discord API and a public meme API to fetch and send memes.

## Features

- Set a specific channel to receive memes using a slash command.
- Automatically fetches and posts memes every 10 seconds.

## Setup

### Prerequisites

- Python 3.12.8
- A Discord account and a server where you have permission to add bots.
- A Discord bot token. You can create a bot and get a token from the [Discord Developer Portal](https://discord.com/developers/applications).

### Installation

1. Clone the repository:

   ```bash
   git clone <repository-url>
   cd Discord_Bot
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

## Deployment

- The bot can be deployed on platforms that support Python, such as Heroku. Ensure the `Procfile` is correctly set up for deployment.

## Files

- `bot.py`: The main bot script.
- `Procfile`: Configuration for deploying the bot as a worker.
- `requirements.txt`: Python dependencies.
- `runtime.txt`: Specifies the Python version.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details. 
