import discord
from discord.ext import commands
from discord import app_commands
import os
from dotenv import load_dotenv
load_dotenv()
from keep_alive import keep_alive #NEW

keep_alive()

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
                url="https://cdn.discordapp.com/attachments/1317842638774468640/1408821709716455524/kpop-triples.gif"
            )
            embed.set_footer(text=f"Member #{len(member.guild.members)}")
            await channel.send(embed=embed)

# Intents
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

GUILD_ID = discord.Object(id=1379088766265856010)

client = Client(command_prefix="!", intents=intents)

@client.tree.command(name="hello", description="Say hello!", guild=GUILD_ID)
async def sayHello(interaction: discord.Interaction):
    await interaction.response.send_message("Hi there!")

# Secure token load
token = os.getenv("DISCORD_TOKEN")
if token is None:
    raise ValueError("❌ Bot token not found. Set DISCORD_TOKEN env var.")
client.run(token)
