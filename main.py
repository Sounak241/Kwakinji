import discord
from discord.ext import commands
import os
from dotenv import load_dotenv
from keep_alive import keep_alive
import re

# Load environment variables from a .env file
load_dotenv()

# Define the bot's intents
# message_content is required to read messages for links
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

# Regex to find Twitter/X links
# This catches both x.com and twitter.com links
twitter_regex = re.compile(r"https?://(?:www\.)?(x\.com|twitter\.com)/(\w+)/status/(\d+)")

# --- Custom Bot Class ---
class Client(commands.Bot):
    # This event runs when the bot is ready and connected to Discord
    async def on_ready(self):
        print(f'✅ Logged on as {self.user}!')
        try:
            # Sync commands to a specific guild for instant updates
            guild = discord.Object(id=1379088766265856010)
            synced = await self.tree.sync(guild=guild)
            print(f'Synced {len(synced)} commands to guild {guild.id}')
        except Exception as e:
            print(f'Error syncing commands: {e}')

    # This event runs on every message sent in a channel the bot can see
    # This event runs on every message sent in a channel the bot can see
    async def on_message(self, message):
        # Ignore messages sent by the bot itself to prevent loops
        if message.author == self.user:
            return

        # Regex to find original Twitter/X links
        match = twitter_regex.search(message.content)

        # If a link is found, proceed
        if match:
            print(f"✅ Found Twitter link from {message.author.name}, creating Markdown link.")
            
            # --- MODIFICATION START ---

            # Extract the username from the link (it's the 2nd captured group)
            username = match.group(2)
            
            # Get the original link
            original_link = match.group(0)

            # Create the corrected fixupx.com link
            fixed_link = original_link.replace("x.com", "fixupx.com").replace("twitter.com", "fixupx.com")

            # Create the final Markdown message string
            # Format: [Visible Text](URL)
            markdown_message = f"[Twitter • @{username}]({fixed_link})"

            # Send the new Markdown formatted message
            await message.channel.send(markdown_message)

            # --- MODIFICATION END ---
            
            # Optional: To keep the chat clean, you can delete the user's original message.
            # await message.delete()

            return # Stop the function here

        # This allows other commands to still work if no link was found
        await self.process_commands(message)
    
    # This event runs when a new member joins the server
    async def on_member_join(self, member):
        # Replace with your welcome channel ID
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


# --- Bot Setup ---

# Create an instance of the bot with a command prefix and intents
client = Client(command_prefix="!", intents=intents)

# Define the server ID for slash commands
GUILD_ID = discord.Object(id=1379088766265856010)

# A simple slash command example
@client.tree.command(name="hello", description="Say hello!", guild=GUILD_ID)
async def say_hello(interaction: discord.Interaction):
    await interaction.response.send_message("Hi there!")

# A simple text command example
@client.command()
async def ping(ctx):
    await ctx.send(f"Pong! Latency is {round(client.latency * 1000)}ms")


# --- Run the Bot ---
if __name__ == "__main__":
    # This function is in your keep_alive.py file and is used for hosting
    keep_alive()
    
    # Get the bot token from environment variables
    token = os.getenv("DISCORD_TOKEN")
    if not token:
        raise ValueError("❌ Bot token not found. Set the DISCORD_TOKEN environment variable.")
    
    # Run the bot with your token
    client.run(token)
