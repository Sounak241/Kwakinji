# 🎵 Discord Music & Social Bot  

A feature-packed Discord bot built with [discord.py](https://discordpy.readthedocs.io/), combining **Spotify integration** with **social media link fixes** and fun utility commands.  

## ✨ Features  

### 🎶 Spotify Integration  
- `/np` or `!np` → Show what someone is currently listening to on Spotify with:  
  - Song title, artist, album, album art  
  - Playable Spotify link  
  - Progress bar + time elapsed  
- `/setspotify` → Save your Spotify profile link  
- `/myspotify` → Retrieve your saved Spotify profile  
- `/removespotify` → Remove your profile link  

### 🐦 Twitter/X Fixer  
- Automatically replaces `twitter.com` or `x.com` links with `fixupx.com` links (for better embed previews).  

### 👋 Utility Commands  
- `/hello` → Say hello  
- `/ping` → Check bot latency  

### 🎉 Welcome System  
- Greets new members with a custom embed + GIF  

---

## 🚀 Coming Soon  
Planned features in development:  
- 📸 **Instagram embeds**  
- 📺 **YouTube embeds**  
- 👽 **Reddit embeds**  
- 📊 **Spotify top artists & tracks**  
- 🎤 **Genius lyrics integration**  

---

## 🛠️ Installation  

1. **Clone the repo**  
   ```bash
   git clone https://github.com/YOUR_USERNAME/YOUR_REPO.git
   cd YOUR_REPO
Install dependencies

pip install -r requirements.txt


Set up environment variables

Create a .env file (for local dev) or set env vars on Render/Heroku:

DISCORD_TOKEN=your_discord_bot_token
SPOTIFY_CLIENT_ID=your_spotify_client_id
SPOTIFY_CLIENT_SECRET=your_spotify_client_secret


On Render: go to Dashboard → Environment → Add Environment Variable.

Run the bot

python main.py

📂 Project Structure
├── main.py              # Main bot logic
├── keep_alive.py        # Keeps the bot alive on hosting platforms (Flask server)
├── spotify_profiles.json # Stored user Spotify profiles
├── requirements.txt     # Python dependencies
└── README.md            # Documentation

📦 Requirements
discord.py
python-dotenv
flask
requests

🤝 Contributing

Pull requests are welcome! If you’d like to suggest a new feature (like a new embed or Spotify tool), feel free to open an issue.

📜 License

MIT License — feel free to use, modify, and share.


Would you like me to also add a **badges section** (e.g., Python version, Discord.py, Render deploy) at the very top to make it look more professional?

