import discord
from discord.ext import commands
from discord import app_commands
import os
from dotenv import load_dotenv
from keep_alive import keep_alive  # Flask keep-alive server
import re

# Load environment variables
load_dotenv()

# Intents
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

# Regex for Twitter links
twitter_regex = re.compile(r"(https?://)(?:www\.)?twitter\.com/\S+")

# Custom Bot class
class Client(commands.Bot):
    async def on_ready(self):
        print(f'✅ Logged on as {self.user}!')
        try:
            guild = discord.Object(id=1379088766265856010)  # Replace with your guild ID
            synced = await self.tree.sync(guild=guild)
            print(f'Synced {len(synced)} commands to guild {guild.id}')
        except Exception as e:
            print(f'Error syncing commands: {e}')

    async def on_message(self, message):
        if message.author == self.user:
            return

        # Twitter link fixer
        match = twitter_regex.search(message.content)
        if match:
            fixed_link = message.content.replace("twitter.com", "vxtwitter.com")
            await message.reply(f"🔗 Fixed link:\n{fixed_link}")

        # Example text command
        if message.content.startswith('hello'):
            await message.channel.send(f'Hi there {message.author.mention}')

        await self.process_commands(message)

    async def on_reaction_add(self, reaction, user):
        await reaction.message.channel.send('You reacted')

    async def on_member_join(self, member):
        channel = self.get_channel(1379088767004049550)  # replace with your channel ID
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

# Run keep_alive + bot safely
if __name__ == "__main__":
    keep_alive()  # start small Flask server for uptime ping
    token = os.getenv("DISCORD_TOKEN")
    if token is None:
        raise ValueError("❌ Bot token not found. Set DISCORD_TOKEN env var.")
    client.run(token)
