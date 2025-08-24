import discord
from discord.ext import commands
from discord import app_commands
import os
from dotenv import load_dotenv
from keep_alive import keep_alive
import re
import aiohttp
from bs4 import BeautifulSoup

# Load environment variables
load_dotenv()

# Intents
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

# Regex for Twitter/X links
twitter_regex = re.compile(r"(https?://)(?:www\.)?x\.com/\S+")

# Custom Bot class
class Client(commands.Bot):
    async def on_ready(self):
        print(f'✅ Logged on as {self.user}!')
        try:
            guild = discord.Object(id=1379088766265856010)
            synced = await self.tree.sync(guild=guild)
            print(f'Synced {len(synced)} commands to guild {guild.id}')
        except Exception as e:
            print(f'Error syncing commands: {e}')

    async def fetch_tweet_media(self, url):
        """Fetch image or video URL from tweet using mobile page meta tags"""
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                html = await resp.text()
        soup = BeautifulSoup(html, "html.parser")
        og_image = soup.find("meta", property="og:image")
        og_video = soup.find("meta", property="og:video")
        return (og_image["content"] if og_image else None,
                og_video["content"] if og_video else None)

    async def on_message(self, message):
        if message.author == self.user:
            return  # Ignore bot's own messages

        await self.process_commands(message)  # process commands first

        # Check for Twitter/X links
        match = twitter_regex.search(message.content)
        if match:
            original_link = match.group(0)
            fixed_link = original_link.replace("x.com", "m.fixupx.com")  # mobile link

            # Extract author
            try:
                author = fixed_link.split("fixupx.com/")[1].split("/")[0]
            except IndexError:
                author = "Unknown"

            # Fetch media
            image_url, video_url = await self.fetch_tweet_media(fixed_link)

            # Build embed
            embed = discord.Embed(
                title=f"Tweet by @{author}",
                url=fixed_link,
                description="✅ Click the title to view the tweet on Twitter/X",
                color=discord.Color.blue()
            )
            embed.set_footer(text="Platform: X/Twitter")
            embed.set_thumbnail(url="https://upload.wikimedia.org/wikipedia/en/9/9f/X_logo.png")
            if image_url:
                embed.set_image(url=image_url)
            if video_url:
                embed.add_field(name="Video", value=f"[Click to watch video]({video_url})", inline=False)

            await message.channel.send(embed=embed)

        # Simple text command
        if message.content.lower().startswith('hello'):
            await message.channel.send(f'Hi there {message.author.mention}')

    async def on_reaction_add(self, reaction, user):
        if user != self.user:  # ignore bot reactions
            await reaction.message.channel.send('You reacted')

    async def on_member_join(self, member):
        channel = self.get_channel(1379088767004049550)  # Replace with your channel ID
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


# Create bot instance
client = Client(command_prefix="!", intents=intents)

# Slash command example
GUILD_ID = discord.Object(id=1379088766265856010)

@client.tree.command(name="hello", description="Say hello!", guild=GUILD_ID)
async def sayHello(interaction: discord.Interaction):
    await interaction.response.send_message("Hi there!")

# Run bot with keep-alive server
if __name__ == "__main__":
    keep_alive()
    token = os.getenv("DISCORD_TOKEN")
    if not token:
        raise ValueError("❌ Bot token not found. Set DISCORD_TOKEN env var.")
    client.run(token)
