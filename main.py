import discord
from discord.ext import commands
import os
from dotenv import load_dotenv
from keep_alive import keep_alive
import re
import json
import requests
import base64
import time
from typing import Optional

# -----------------------------
# Load environment variables
# -----------------------------
load_dotenv()

# -----------------------------
# Intents setup
# -----------------------------
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.presences = True  # Required for Spotify presence

# -----------------------------
# Twitter/X regex
# -----------------------------
twitter_regex = re.compile(r"https?://(?:www\.)?(x\.com|twitter\.com)/(\w+)/status/(\d+)")

# -----------------------------
# Spotify profile storage
# -----------------------------
SPOTIFY_FILE = "spotify_profiles.json"

if os.path.exists(SPOTIFY_FILE):
    with open(SPOTIFY_FILE, "r") as f:
        spotify_profiles = json.load(f)
else:
    spotify_profiles = {}

# -----------------------------
# Spotify API helper
# -----------------------------
SPOTIFY_TOKEN = None
SPOTIFY_TOKEN_EXP = 0

def get_spotify_token():
    global SPOTIFY_TOKEN, SPOTIFY_TOKEN_EXP
    if SPOTIFY_TOKEN and time.time() < SPOTIFY_TOKEN_EXP - 60:
        return SPOTIFY_TOKEN

    client_id = os.getenv("SPOTIFY_CLIENT_ID")
    client_secret = os.getenv("SPOTIFY_CLIENT_SECRET")

    auth_str = f"{client_id}:{client_secret}"
    b64_auth = base64.b64encode(auth_str.encode()).decode()

    headers = {"Authorization": f"Basic {b64_auth}"}
    data = {"grant_type": "client_credentials"}

    r = requests.post("https://accounts.spotify.com/api/token", headers=headers, data=data)
    r.raise_for_status()
    res = r.json()
    SPOTIFY_TOKEN = res["access_token"]
    SPOTIFY_TOKEN_EXP = time.time() + res["expires_in"]
    return SPOTIFY_TOKEN

def get_artist_from_track(track_id):
    """Get exact artist name and Spotify URL from track ID"""
    token = get_spotify_token()
    headers = {"Authorization": f"Bearer {token}"}
    r = requests.get(f"https://api.spotify.com/v1/tracks/{track_id}", headers=headers)
    r.raise_for_status()
    res = r.json()
    artist = res['artists'][0]  # main artist
    return artist['name'], artist['external_urls']['spotify']

# -----------------------------
# Custom Bot Class
# -----------------------------
class Client(commands.Bot):
    async def on_ready(self):
        print(f'✅ Logged on as {self.user}!')
        try:
            guild = discord.Object(id=1379088766265856010)
            synced = await self.tree.sync(guild=guild)
            print(f'Synced {len(synced)} commands to guild {guild.id}')
        except Exception as e:
            print(f'Error syncing commands: {e}')

    async def on_message(self, message):
        if message.author == self.user:
            return

        match = twitter_regex.search(message.content)
        if match:
            username = match.group(2)
            original_link = match.group(0)
            fixed_link = original_link.replace("x.com", "fixupx.com").replace("twitter.com", "fixupx.com")
            markdown_message = f"[Twitter • @{username}]({fixed_link})"
            await message.channel.send(markdown_message)
            await message.delete()
            return

        await self.process_commands(message)
    
    async def on_member_join(self, member):
        channel = self.get_channel(1379088767004049550)
        if channel:
            embed = discord.Embed(
                title="🎉 Welcome!",
                description=f"Glad to have you here {member.mention}!",
                color=discord.Color.blue()
            )
            embed.set_image(
                url="https://cdn.discordapp.com/attachments/996799825939005463/1408902538308354191/kpop-triples.gif"
            )
            embed.set_footer(text=f"Member #{len(member.guild.members)}")
            await channel.send(embed=embed)

# -----------------------------
# Bot Setup
# -----------------------------
client = Client(command_prefix="!", intents=intents)
GUILD_ID = discord.Object(id=1379088766265856010)

# -----------------------------
# Helper function for Spotify NP
# -----------------------------
def create_progress_bar(progress, duration, length=10):
    filled_blocks = int(progress / duration * length)
    if filled_blocks > length - 1:
        filled_blocks = length - 1
    bar = "▬" * filled_blocks + "🔘" + "▬" * (length - filled_blocks - 1)
    return bar

async def generate_np_embed(member):
    for activity in member.activities:
        if isinstance(activity, discord.Spotify):
            track_url = f"https://open.spotify.com/track/{activity.track_id}"
            profile_url = spotify_profiles.get(str(member.id), track_url)

            artist_name, artist_url = get_artist_from_track(activity.track_id)

            # Progress calculation
            progress = (discord.utils.utcnow() - activity.start).total_seconds()
            duration = (activity.end - activity.start).total_seconds()

            # Progress bar
            progress_bar = create_progress_bar(progress, duration)

            # Timestamps
            progress_time = f"{int(progress)//60}:{int(progress)%60:02d}"
            duration_time = f"{int(duration)//60}:{int(duration)%60:02d}"
            timestamps = f"`{progress_time}/{duration_time}`"

            embed = discord.Embed(
                description=f"[**{activity.title}**]({track_url})\n\n[**{artist_name}**]({artist_url}) • {activity.album}\n\n{progress_bar} {timestamps}",
                color=0x1DB954
            )
            embed.set_thumbnail(url=activity.album_cover_url)
            embed.set_author(
                name=f"Now Playing – {member.display_name}",
                url=profile_url,
                icon_url=member.avatar.url if member.avatar else member.default_avatar.url
            )
            embed.set_footer(text=f"Requested by {member.display_name}")
            return embed
    return None


# -----------------------------
# Commands (text & slash)
# -----------------------------
# Hello
@client.command()
async def hello(ctx):
    await ctx.send("Hi there!")

@client.tree.command(name="hello", description="Say hello!", guild=GUILD_ID)
async def hello_slash(interaction: discord.Interaction):
    await interaction.response.send_message("Hi there!")

# Ping
@client.command()
async def ping(ctx):
    await ctx.send(f"Pong! Latency is {round(client.latency * 1000)}ms")

@client.tree.command(name="ping", description="Check bot latency", guild=GUILD_ID)
async def ping_slash(interaction: discord.Interaction):
    await interaction.response.send_message(f"Pong! Latency is {round(client.latency * 1000)}ms")

# Spotify profile commands
@client.command(name="setspotify")
async def set_spotify(ctx, link: str):
    if not link.startswith("https://open.spotify.com/user/"):
        await ctx.send("❌ Please provide a valid Spotify profile link.\nExample: `https://open.spotify.com/user/yourid`")
        return
    spotify_profiles[str(ctx.author.id)] = link
    with open(SPOTIFY_FILE, "w") as f:
        json.dump(spotify_profiles, f, indent=4)
    await ctx.send(f"✅ Saved your Spotify profile link, {ctx.author.display_name}!")

@client.tree.command(name="setspotify", description="Register your Spotify profile", guild=GUILD_ID)
async def setspotify_slash(interaction: discord.Interaction, link: str):
    if not link.startswith("https://open.spotify.com/user/"):
        await interaction.response.send_message(
            "❌ Please provide a valid Spotify profile link.\nExample: `https://open.spotify.com/user/yourid`",
            ephemeral=True
        )
        return
    spotify_profiles[str(interaction.user.id)] = link
    with open(SPOTIFY_FILE, "w") as f:
        json.dump(spotify_profiles, f, indent=4)
    await interaction.response.send_message(f"✅ Saved your Spotify profile link, {interaction.user.display_name}!", ephemeral=True)

@client.command(name="removespotify")
async def remove_spotify(ctx):
    if str(ctx.author.id) in spotify_profiles:
        del spotify_profiles[str(ctx.author.id)]
        with open(SPOTIFY_FILE, "w") as f:
            json.dump(spotify_profiles, f, indent=4)
        await ctx.send(f"🗑️ Removed your Spotify profile link, {ctx.author.display_name}.")
    else:
        await ctx.send("❌ You don't have a Spotify profile link saved.")

@client.tree.command(name="removespotify", description="Remove your Spotify profile", guild=GUILD_ID)
async def removespotify_slash(interaction: discord.Interaction):
    if str(interaction.user.id) in spotify_profiles:
        del spotify_profiles[str(interaction.user.id)]
        with open(SPOTIFY_FILE, "w") as f:
            json.dump(spotify_profiles, f, indent=4)
        await interaction.response.send_message(f"🗑️ Removed your Spotify profile link, {interaction.user.display_name}.", ephemeral=True)
    else:
        await interaction.response.send_message("❌ You don't have a Spotify profile link saved.", ephemeral=True)

@client.command(name="myspotify")
async def my_spotify(ctx):
    link = spotify_profiles.get(str(ctx.author.id))
    if link:
        await ctx.send(f"🎶 Your Spotify profile link: {link}")
    else:
        await ctx.send("❌ You haven't registered a Spotify profile link yet. Use `!setspotify <link>`.")

@client.tree.command(name="myspotify", description="View your registered Spotify profile", guild=GUILD_ID)
async def myspotify_slash(interaction: discord.Interaction):
    link = spotify_profiles.get(str(interaction.user.id))
    if link:
        await interaction.response.send_message(f"🎶 Your Spotify profile link: {link}", ephemeral=True)
    else:
        await interaction.response.send_message("❌ You haven't registered a Spotify profile link yet. Use `/setspotify <link>`.", ephemeral=True)

# Now Playing
@client.command(name="np")
async def now_playing(ctx, member: Optional[discord.Member] = None):
    if member is None:
        member = ctx.author
    embed = await generate_np_embed(member)
    if embed:
        await ctx.send(embed=embed)
    else:
        await ctx.send(f"❌ {member.display_name} is not listening to Spotify right now.")

@client.tree.command(name="np", description="Show what someone is listening to on Spotify", guild=GUILD_ID)
async def now_playing_slash(interaction: discord.Interaction, member: Optional[discord.Member] = None):
    if member is None:
        member = interaction.guild.get_member(interaction.user.id)
    else:
        member = interaction.guild.get_member(member.id)

    embed = await generate_np_embed(member)
    if embed:
        await interaction.response.send_message(embed=embed)
    else:
        await interaction.response.send_message(f"❌ {member.display_name} is not listening to Spotify right now.", ephemeral=True)

# -----------------------------
# Run the Bot
# -----------------------------
if __name__ == "__main__":
    keep_alive()
    token = os.getenv("DISCORD_TOKEN")
    if not token:
        raise ValueError("❌ Bot token not found. Set the DISCORD_TOKEN environment variable.")
    client.run(token)


