import discord
from discord.ext import commands
import os
from dotenv import load_dotenv
from keep_alive import keep_alive
import re
import requests
import base64
import time
from typing import Optional
from supabase import create_client, Client as SupabaseClient
from discord import Embed, Color, Member
import io
from moviepy.editor import VideoFileClip, ImageSequenceClip
from PIL import Image,ImageSequence
import asyncio
import aiohttp

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
# Twitter/X, Instagram, Reddit regex
# -----------------------------
twitter_regex = re.compile(r"https?://(?:www\.)?(x\.com|twitter\.com)/(\w+)/status/(\d+)")
instagram_regex = re.compile(r"(https?://(www\.)?instagram\.com/\S+)")
reddit_regex = re.compile(r"(https?://(www\.)?reddit\.com/\S+)")

# -----------------------------
# Supabase setup
# -----------------------------
url: str = os.environ.get("SUPABASE_URL")
key: str = os.environ.get("SUPABASE_KEY")
supabase: SupabaseClient = create_client(url, key)

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
    token = get_spotify_token()
    headers = {"Authorization": f"Bearer {token}"}
    r = requests.get(f"https://api.spotify.com/v1/tracks/{track_id}", headers=headers)
    r.raise_for_status()
    res = r.json()
    artist = res['artists'][0]
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
        await self.change_presence(activity=discord.Activity(type=discord.ActivityType.listening, name="tripleS - Are you Alive"))
        
    async def on_message(self, message):
        if message.author == self.user or message.author.bot:
            return

        if not message.content:
            return

        print(f"DEBUG: Reading message from {message.author}: '{message.content}'")

        # --- Link processing ---
        link_found = False
        markdown_message = ""
        
        twitter_match = twitter_regex.search(message.content)
        if twitter_match:
            link_found = True
            username = twitter_match.group(2)
            original_link = twitter_match.group(0)
            fixed_link = original_link.replace("x.com", "fixupx.com").replace("twitter.com", "fixupx.com")
            markdown_message = f"[Twitter • @{username}]({fixed_link})"

        insta_match = instagram_regex.search(message.content)
        if not link_found and insta_match:
            link_found = True
            original_link = insta_match.group(1)
            clean_link = original_link.split("?")[0]
            fixed_link = clean_link.replace("instagram.com", "g.embedez.com")
            markdown_message = f"[Instagram]({fixed_link})"

        reddit_match = reddit_regex.search(message.content)
        if not link_found and reddit_match:
            link_found = True
            original_link = reddit_match.group(1)
            fixed_link = original_link.replace("reddit.com", "rxddit.com")
            markdown_message = f"[Reddit]({fixed_link})"

        # --- Action Phase ---
        if link_found:
            print(f"DEBUG: Found link. Preparing to fix and reply.")
            try:
                await message.edit(suppress=True)
                print(f"DEBUG: Successfully suppressed embed for message {message.id}")
            except discord.Forbidden:
                print(f"ERROR: No permission to suppress embeds in channel '{message.channel.name}'. Check 'Manage Messages' permission.")
            except discord.NotFound:
                print(f"ERROR: Could not find the message {message.id} to edit.")
            except Exception as e:
                print(f"ERROR: An unexpected error occurred while trying to edit message: {e}")

            await message.reply(markdown_message, mention_author=False)
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
client = Client(command_prefix="!", intents=intents, help_command=None)
GUILD_ID = discord.Object(id=1379088766265856010)

# -----------------------------
# Spotify NP helpers
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
            
            db_response = supabase.table("spotify_profiles").select("profile_link").eq("user_id", member.id).execute()
            profile_url = track_url  # Default value
            if db_response.data:
                profile_url = db_response.data[0]['profile_link']

            artist_name, artist_url = get_artist_from_track(activity.track_id)
            progress = (discord.utils.utcnow() - activity.start).total_seconds()
            duration = (activity.end - activity.start).total_seconds()
            progress_bar = create_progress_bar(progress, duration)
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


# Badge emojis for visual flair
BADGE_EMOJIS = {
    "Discord Staff": "🛡️",
    "Partnered Server Owner": "🤝",
    "Bug Hunter": "🐛",
    "HypeSquad Bravery": "🦁",
    "HypeSquad Brilliance": "💡",
    "HypeSquad Balance": "⚖️",
    "Early Supporter": "🌟",
    "Verified Bot": "🤖",
    "Early Verified Bot Developer": "👨‍💻"
}

def get_user_badges(member: Member):
    badges = []
    flags = member.public_flags

    # Use getattr to avoid AttributeErrors if flag doesn't exist
    if getattr(flags, "staff", False): badges.append("Discord Staff")
    if getattr(flags, "partner", False): badges.append("Partnered Server Owner")
    if getattr(flags, "bug_hunter", False): badges.append("Bug Hunter")
    if getattr(flags, "hypesquad_bravery", False): badges.append("HypeSquad Bravery")
    if getattr(flags, "hypesquad_brilliance", False): badges.append("HypeSquad Brilliance")
    if getattr(flags, "hypesquad_balance", False): badges.append("HypeSquad Balance")
    if getattr(flags, "early_supporter", False): badges.append("Early Supporter")
    if getattr(flags, "verified_bot", False): badges.append("Verified Bot")
    if getattr(flags, "verified_developer", False): badges.append("Early Verified Bot Developer")

    return badges if badges else ["None"]

async def fetch_assets_embed(member: Member) -> Embed:
    embed = Embed(
        title=f"✨ Profile Assets — {member.display_name}",
        color=Color.blurple()
    )
    embed.set_thumbnail(url=member.display_avatar.url)

    # Avatar Decoration (simulate using top role color)
    deco_color = member.top_role.color if member.top_role.name != "@everyone" else Color.default()
    embed.add_field(name="Avatar Decoration", value=f"Role Color: {deco_color}", inline=False)

    # Profile Effects (simulated using badges)
    badges = get_user_badges(member)
    badge_display = " ".join([BADGE_EMOJIS.get(b, b) for b in badges])
    embed.add_field(name="HypeSquad House", value=badge_display, inline=False)

    # Nameplate (simulated using top role name)
    nameplate = member.top_role.name if member.top_role.name != "@everyone" else "No Pronouns"
    embed.add_field(name="Pronouns", value=nameplate, inline=False)

    # Roles
    roles = [r.mention for r in member.roles if r.name != "@everyone"]
    embed.add_field(name="Roles", value=", ".join(roles) if roles else "None", inline=False)

    # Account creation date
    embed.add_field(name="Account Created", value=member.created_at.strftime("%d %b %Y, %H:%M:%S UTC"), inline=False)

    return embed


import ffmpeg
import os
from PIL import Image, ImageSequence
import asyncio

MAX_SIZE = 25 * 1024 * 1024  # 25MB limit

async def compress_gif_until_fit(input_path: str, max_attempts: int = 10) -> str:
    """Compress GIF iteratively until it fits Discord's limit."""
    loop = asyncio.get_event_loop()
    current_path = input_path

    for attempt in range(max_attempts):
        if os.path.getsize(current_path) <= MAX_SIZE:
            return current_path

        base, ext = os.path.splitext(current_path)
        if base.endswith("_compressed"):
            base = base.rsplit("_compressed", 1)[0]
        output_path = f"{base}_compressed.gif"

        success = await loop.run_in_executor(None, compress_gif_sync, current_path, output_path, 0.85)
        if not success:
            break

        if current_path != input_path:
            os.remove(current_path)
        current_path = output_path

    return current_path


def compress_gif_sync(input_path: str, output_path: str, scale_factor: float) -> bool:
    """Sync helper for compressing GIF."""
    try:
        with Image.open(input_path) as img:
            frames = []
            duration = img.info.get('duration', 100)
            loop_val = img.info.get('loop', 0)
            for frame in ImageSequence.Iterator(img):
                frame = frame.convert("RGBA")
                new_size = (int(frame.width * scale_factor), int(frame.height * scale_factor))
                frames.append(frame.resize(new_size, Image.Resampling.LANCZOS))
            frames[0].save(output_path, save_all=True, append_images=frames[1:], optimize=True,
                           duration=duration, loop=loop_val, disposal=2)
        return True
    except Exception as e:
        print(f"Error compressing GIF: {e}")
        return False




# -----------------------------
# Commands
# -----------------------------
@client.command()
async def hello(ctx):
    await ctx.send("Hi there!")

@client.tree.command(name="hello", description="Say hello!", guild=GUILD_ID)
async def hello_slash(interaction: discord.Interaction):
    await interaction.response.send_message("Hi there!")

@client.command()
async def ping(ctx):
    await ctx.send(f"Pong! Latency is {round(client.latency * 1000)}ms")

@client.tree.command(name="ping", description="Check bot latency", guild=GUILD_ID)
async def ping_slash(interaction: discord.Interaction):
    await interaction.response.send_message(f"Pong! Latency is {round(client.latency * 1000)}ms")

# --- Spotify commands ---
@client.command(name="setspotify")
async def set_spotify(ctx, link: str):
    if not link.startswith("https://open.spotify.com/user/"):
        await ctx.send("❌ Please provide a valid Spotify profile link.\nExample: `https://open.spotify.com/user/yourid`")
        return
    supabase.table("spotify_profiles").upsert({
        "user_id": ctx.author.id,
        "profile_link": link
    }).execute()
    await ctx.send(f"✅ Saved your Spotify profile link, {ctx.author.display_name}!")

@client.tree.command(name="setspotify", description="Register your Spotify profile", guild=GUILD_ID)
async def setspotify_slash(interaction: discord.Interaction, link: str):
    if not link.startswith("https://open.spotify.com/user/"):
        await interaction.response.send_message(
            "❌ Please provide a valid Spotify profile link.\nExample: `https://open.spotify.com/user/yourid`",
            ephemeral=True
        )
        return
    supabase.table("spotify_profiles").upsert({
        "user_id": interaction.user.id,
        "profile_link": link
    }).execute()
    await interaction.response.send_message(f"✅ Saved your Spotify profile link, {interaction.user.display_name}!", ephemeral=True)

@client.command(name="removespotify")
async def remove_spotify(ctx):
    user_id = ctx.author.id
    data, count = supabase.table("spotify_profiles").delete().eq("user_id", user_id).execute()
    if count[1] > 0:
        await ctx.send(f"🗑️ Removed your Spotify profile link, {ctx.author.display_name}.")
    else:
        await ctx.send("❌ You don't have a Spotify profile link saved.")

@client.tree.command(name="removespotify", description="Remove your Spotify profile", guild=GUILD_ID)
async def removespotify_slash(interaction: discord.Interaction):
    user_id = interaction.user.id
    data, count = supabase.table("spotify_profiles").delete().eq("user_id", user_id).execute()
    if count[1] > 0:
        await interaction.response.send_message(f"🗑️ Removed your Spotify profile link, {interaction.user.display_name}.", ephemeral=True)
    else:
        await interaction.response.send_message("❌ You don't have a Spotify profile link saved.", ephemeral=True)

@client.command(name="myspotify")
async def my_spotify(ctx):
    user_id = ctx.author.id
    response = supabase.table("spotify_profiles").select("profile_link").eq("user_id", user_id).execute()
    link = None
    if response.data:
        link = response.data[0]['profile_link']
    
    if link:
        await ctx.send(f"🎶 Your Spotify profile link: {link}")
    else:
        await ctx.send("❌ You haven't registered a Spotify profile link yet. Use `!setspotify <link>`.")

@client.tree.command(name="myspotify", description="View your registered Spotify profile", guild=GUILD_ID)
async def myspotify_slash(interaction: discord.Interaction):
    user_id = interaction.user.id
    response = supabase.table("spotify_profiles").select("profile_link").eq("user_id", user_id).execute()
    link = None
    if response.data:
        link = response.data[0]['profile_link']
    
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
# Custom Help Command
# -----------------------------
client.remove_command("help")

@client.command(name="help")
async def help_command(ctx):
    embed = discord.Embed(
        title="🤖 Bot Help — Commands",
        description="Here are all the commands you can use:",
        color=discord.Color.green()
    )
    embed.add_field(name="👋 Hello", value="`!hello` or `/hello` — Say hello to the bot.", inline=False)
    embed.add_field(name="🏓 Ping", value="`!ping` or `/ping` — Check the bot latency.", inline=False)
    embed.add_field(
        name="🎵 Spotify Profiles",
        value=(
            "`!setspotify <link>` or `/setspotify <link>` — Save your Spotify profile.\n"
            "`!removespotify` or `/removespotify` — Remove your saved profile.\n"
            "`!myspotify` or `/myspotify` — Show your saved profile."
        ),
        inline=False
    )
    embed.add_field(name="🎶 Now Playing", value="`!np [@member]` or `/np [member]` — Show what you or someone else is listening to on Spotify.", inline=False)
    embed.add_field(name="🔗 Link Fixer", value="Posting Twitter/X, Instagram, or Reddit links will automatically be fixed.", inline=False)
    embed.set_footer(text="Use the slash (/) versions for cleaner interactions!")
    await ctx.send(embed=embed)

@client.tree.command(name="help", description="Show the help menu", guild=GUILD_ID)
async def help_slash(interaction: discord.Interaction):
    embed = discord.Embed(
        title="🤖 Bot Help — Commands",
        description="Here are all the commands you can use:",
        color=discord.Color.green()
    )
    embed.add_field(name="👋 Hello", value="`/hello` or `!hello` — Say hello to the bot.", inline=False)
    embed.add_field(name="🏓 Ping", value="`/ping` or `!ping` — Check the bot latency.", inline=False)
    embed.add_field(
        name="🎵 Spotify Profiles",
        value=(
            "`/setspotify <link>` or `!setspotify <link>` — Save your Spotify profile.\n"
            "`/removespotify` or `!removespotify` — Remove your saved profile.\n"
            "`/myspotify` or `!myspotify` — Show your saved profile."
        ),
        inline=False
    )
    embed.add_field(name="🎶 Now Playing", value="`/np [member]` or `!np [@member]` — Show what you or someone else is listening to on Spotify.", inline=False)
    embed.add_field(name="🔗 Link Fixer", value="Posting Twitter/X, Instagram, or Reddit links will automatically be fixed.", inline=False)
    embed.set_footer(text="Use the slash (/) versions for cleaner interactions!")
    await interaction.response.send_message(embed=embed, ephemeral=True)
# -----------------------------
# Assets Command
# -----------------------------    
@client.command(name="profile")
async def assets(ctx, member: Optional[discord.Member] = None):
    if member is None:
        member = ctx.author
    embed = await fetch_assets_embed(member)
    await ctx.send(embed=embed)

@client.tree.command(
    name="profile",
    description="Show a user's Discord profile with badges, roles, and simulated effects",
    guild=GUILD_ID
)
async def assets_slash(interaction: discord.Interaction, member: Optional[discord.Member] = None):
    if member is None:
        member = interaction.guild.get_member(interaction.user.id)
    embed = await fetch_assets_embed(member)
    await interaction.response.send_message(embed=embed, ephemeral=True)

import discord
from discord.ext import commands
from discord import app_commands
import os
from moviepy.editor import VideoFileClip
from PIL import Image

# -----------------------------
# !gif Command (prefix)
# -----------------------------
@client.command(name="gif")
async def gif_prefix(ctx):
    if not ctx.message.attachments:
        await ctx.send("❌ Please attach a video or image to convert.")
        return

    attachment = ctx.message.attachments[0]
    processing_msg = await ctx.send("⏳ Processing your file, please wait...")

    base_path = f"./{ctx.author.id}_{attachment.filename}"
    output_path = f"./{ctx.author.id}_output.gif"

    try:
        await attachment.save(base_path)

        if attachment.content_type and attachment.content_type.startswith('video'):
            # Use ffmpeg to convert video to GIF with scale + fps
            ffmpeg.input(base_path).output(
                output_path, vf="fps=15,scale=320:-1:flags=lanczos"
            ).run(overwrite_output=True, capture_stdout=True, capture_stderr=True)
        elif attachment.content_type and attachment.content_type.startswith('image'):
            with Image.open(base_path) as img:
                img.save(output_path, save_all=True, duration=200, loop=0)
        else:
            await processing_msg.edit(content="❌ Unsupported file type.")
            return

        # Compress GIF iteratively
        final_path = await compress_gif_until_fit(output_path)

        if os.path.getsize(final_path) > MAX_SIZE:
            await processing_msg.edit(content="❌ The final GIF is still too large to upload to Discord.")
        else:
            await processing_msg.delete()
            await ctx.send(file=discord.File(final_path))

    except Exception as e:
        try:
            await processing_msg.edit(content=f"❌ An error occurred: {e}")
        except discord.NotFound:
            await ctx.send(f"❌ An error occurred: {e}")

    finally:
        # Cleanup all temp files
        for path in [base_path, output_path, final_path]:
            if path and os.path.exists(path):
                try:
                    os.remove(path)
                except Exception as e:
                    print(f"Cleanup error: {e}")



# -----------------------------
# /gif Command (slash)
# -----------------------------
@client.tree.command(name="gif", description="Convert an image or video to GIF", guild=GUILD_ID)
async def gif_slash(interaction: discord.Interaction, file: discord.Attachment):
    await interaction.response.defer()
    base_path = f"./{interaction.user.id}_{file.filename}"
    output_path = f"./{interaction.user.id}_output.gif"

    try:
        await file.save(base_path)

        if file.content_type.startswith('video'):
            ffmpeg.input(base_path).output(
                output_path, vf="fps=15,scale=320:-1:flags=lanczos"
            ).run(overwrite_output=True, capture_stdout=True, capture_stderr=True)
        elif file.content_type.startswith('image'):
            with Image.open(base_path) as img:
                img.save(output_path, save_all=True, duration=200, loop=0)
        else:
            await interaction.edit_original_response(content="❌ Unsupported file type.")
            return

        final_path = await compress_gif_until_fit(output_path)

        if os.path.getsize(final_path) > MAX_SIZE:
            await interaction.edit_original_response(content="❌ The final GIF is still too large to upload to Discord.")
        else:
            await interaction.edit_original_response(content=None, attachments=[discord.File(final_path)])

    except Exception as e:
        await interaction.edit_original_response(content=f"❌ An error occurred: {e}")

    finally:
        for path in [base_path, output_path, final_path]:
            if path and os.path.exists(path):
                try:
                    os.remove(path)
                except Exception as e:
                    print(f"Cleanup error: {e}")


# -----------------------------
# Run the Bot
# -----------------------------
if __name__ == "__main__":
    keep_alive()
    token = os.getenv("DISCORD_TOKEN")
    if not token:
        raise ValueError("❌ Bot token not found. Set the DISCORD_TOKEN environment variable.")
    client.run(token)
