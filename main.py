import discord
from discord.ext import commands
from discord import app_commands
from motor.motor_asyncio import AsyncIOMotorClient
import logging
from dotenv import load_dotenv
import os
import aiohttp

## maximum amount of ideas/wildcards for a user to submit to the jam
from typing import Final

MAX_AMT_OF_THEME_IDEAS: Final = 3
MAX_AMT_OF_WILDCARDS: Final = 3

from keep_alive import keep_alive  # this tricks the host into running the bot 24/7

### DISCORD TOKEN
load_dotenv()
token = os.getenv('DISCORD_TOKEN')

### MONGO URI
MONGO_URI = os.getenv('MONGO_URI')
mongo_client = AsyncIOMotorClient(
    MONGO_URI,
    tlsAllowInvalidCertificates=True  # disabling this since my msys2 isnt working with it otherwise
)
db = mongo_client['discord_bot']
theme_ideas_collection = db['theme_ideas']
wildcards_collection = db['wildcards']
users_collection = db['users']

### HANDLER
handler = logging.FileHandler(filename='discord.log', encoding='utf-8', mode='w')
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix='/', intents=intents)

bot_spam_ID = 763029100214222879;


## VoteView for theme ideas
class ThemeVoteView(discord.ui.View):

    def __init__(self, theme_idea_id):
        super().__init__(timeout=None)
        self.theme_idea_id = theme_idea_id

    @discord.ui.button(label="Yes", style=discord.ButtonStyle.success, custom_id="theme_vote_yes")
    async def vote_yes(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.handle_vote(interaction, "yes")

    @discord.ui.button(label="No", style=discord.ButtonStyle.danger, custom_id="theme_vote_no")
    async def vote_no(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.handle_vote(interaction, "no")

    async def handle_vote(self, interaction: discord.Interaction, vote_type: str):
        user_id = interaction.user.id

        ## retrieve the theme idea
        theme_idea = await theme_ideas_collection.find_one({"_id": self.theme_idea_id})
        if not theme_idea:
            await interaction.response.send_message("ERROR: could not find the theme idea you clicked on",
                                                    ephemeral=True)
            return

        voters = theme_idea.get('voters', {})
        current_vote = voters.get(str(user_id))
        idea_text = theme_idea.get('theme_idea', 'this theme idea')

        # remove previous vote if exists
        if current_vote == "yes":
            theme_idea['yes_count'] = theme_idea.get('yes_count', 0) - 1
        elif current_vote == "no":
            theme_idea['no_count'] = theme_idea.get('no_count', 0) - 1

        ## toggle if pressing same button twice
        if current_vote == vote_type:
            voters.pop(str(user_id))
            await interaction.response.send_message(f"Vote removed for **{idea_text}**", ephemeral=True)
        else:
            ## vote for the first time or change vote
            voters[str(user_id)] = vote_type
            if vote_type == "yes":
                theme_idea['yes_count'] = theme_idea.get('yes_count', 0) + 1
            else:
                theme_idea['no_count'] = theme_idea.get('no_count', 0) + 1

            vote_emoji = "✅" if vote_type == "yes" else "❌"
            await interaction.response.send_message(
                f"Voted {vote_emoji} **{vote_type.upper()}** for **{idea_text}**",
                ephemeral=True
            )

        ## update the database
        await theme_ideas_collection.update_one(
            {"_id": self.theme_idea_id},
            {
                "$set": {
                    "voters": voters,
                    "yes_count": theme_idea.get('yes_count', 0),
                    "no_count": theme_idea.get('no_count', 0)
                }
            }
        )


## VoteView for wildcards
class WildcardVoteView(discord.ui.View):

    def __init__(self, wildcard_id):
        super().__init__(timeout=None)
        self.wildcard_id = wildcard_id

    @discord.ui.button(label="Yes", style=discord.ButtonStyle.success, custom_id="wildcard_vote_yes")
    async def vote_yes(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.handle_vote(interaction, "yes")

    @discord.ui.button(label="No", style=discord.ButtonStyle.danger, custom_id="wildcard_vote_no")
    async def vote_no(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.handle_vote(interaction, "no")

    async def handle_vote(self, interaction: discord.Interaction, vote_type: str):
        user_id = interaction.user.id

        ## retrieve the wildcard
        wildcard = await wildcards_collection.find_one({"_id": self.wildcard_id})
        if not wildcard:
            await interaction.response.send_message("ERROR: could not find the wildcard you clicked on", ephemeral=True)
            return

        voters = wildcard.get('voters', {})
        current_vote = voters.get(str(user_id))
        wildcard_text = wildcard.get('wildcard', 'this wildcard')

        # remove previous vote if exists
        if current_vote == "yes":
            wildcard['yes_count'] = wildcard.get('yes_count', 0) - 1
        elif current_vote == "no":
            wildcard['no_count'] = wildcard.get('no_count', 0) - 1

        ## toggle if pressing same button twice
        if current_vote == vote_type:
            voters.pop(str(user_id))
            await interaction.response.send_message(f"Vote removed for **{wildcard_text}**", ephemeral=True)
        else:
            ## vote for the first time or change vote
            voters[str(user_id)] = vote_type
            if vote_type == "yes":
                wildcard['yes_count'] = wildcard.get('yes_count', 0) + 1
            else:
                wildcard['no_count'] = wildcard.get('no_count', 0) + 1

            vote_emoji = "✅" if vote_type == "yes" else "❌"
            await interaction.response.send_message(
                f"Voted {vote_emoji} **{vote_type.upper()}** for **{wildcard_text}**",
                ephemeral=True
            )

        ## update the database
        await wildcards_collection.update_one(
            {"_id": self.wildcard_id},
            {
                "$set": {
                    "voters": voters,
                    "yes_count": wildcard.get('yes_count', 0),
                    "no_count": wildcard.get('no_count', 0)
                }
            }
        )


@bot.tree.command(name="submit_theme",
                  description="Submit a theme idea for the game jam (You can submit a maximum of 3)")
@app_commands.describe(theme_idea="Your theme idea")
async def submit_theme(interaction: discord.Interaction, theme_idea: str):
    user_id = interaction.user.id

    ALLOWED_CHANNEL_ID = 1438484588388159508
    if interaction.channel_id != ALLOWED_CHANNEL_ID and interaction.channel_id != bot_spam_ID:
        await interaction.response.send_message("this command can only be used in theme submissions", ephemeral=True)
        return

    # check amount of theme ideas submitted by user
    user_data = await users_collection.find_one({"user_id": user_id})
    theme_idea_count = user_data.get('theme_idea_count', 0) if user_data else 0

    if theme_idea_count >= MAX_AMT_OF_THEME_IDEAS:
        await interaction.response.send_message("Youve already submitted 3 theme ideas, You cant add any more :C",
                                                ephemeral=True)
        return

    # initialize the theme idea submission
    theme_idea_doc = {
        "user_id": user_id,
        "username": interaction.user.name,
        "theme_idea": theme_idea,
        "yes_count": 0,
        "no_count": 0,
        "voters": {}
    }

    result = await theme_ideas_collection.insert_one(theme_idea_doc)
    theme_idea_id = result.inserted_id

    ## update user's amount of theme ideas submitted by 1
    await users_collection.update_one(
        {"user_id": user_id},
        {
            "$inc": {"theme_idea_count": 1},
            "$set": {"username": interaction.user.name}
        },
        upsert=True
    )

    # create the embed
    embed = discord.Embed(
        title="New theme idea submission",
        description=theme_idea,
        color=discord.Color.blue()
    )
    embed.set_author(name=interaction.user.name,
                     icon_url=interaction.user.avatar.url if interaction.user.avatar else None)
    embed.set_footer(text="Vote using the buttons below (Votes are hidden)")

    ## send into the channel
    await interaction.response.send_message(embed=embed, view=ThemeVoteView(theme_idea_id))


@bot.tree.command(name="submit_wildcard",
                  description="Submit a wildcard for the game jam (You can submit a maximum of 3)")
@app_commands.describe(wildcard="Your wildcard idea")
async def submit_wildcard(interaction: discord.Interaction, wildcard: str):
    user_id = interaction.user.id

    ALLOWED_CHANNEL_ID = 1439565044944732211 ## this should be the wildcard one instead
    if interaction.channel_id != ALLOWED_CHANNEL_ID and interaction.channel_id != bot_spam_ID :
        await interaction.response.send_message("this command can only be used in wildcard submissions", ephemeral=True)
        return

    # check amount of wildcards submitted by user
    user_data = await users_collection.find_one({"user_id": user_id})
    wildcard_count = user_data.get('wildcard_count', 0) if user_data else 0

    if wildcard_count >= MAX_AMT_OF_WILDCARDS:
        await interaction.response.send_message("Youve already submitted 3 wildcards, You cant add any more :C",
                                                ephemeral=True)
        return

    # initialize the wildcard submission
    wildcard_doc = {
        "user_id": user_id,
        "username": interaction.user.name,
        "wildcard": wildcard,
        "yes_count": 0,
        "no_count": 0,
        "voters": {}
    }

    result = await wildcards_collection.insert_one(wildcard_doc)
    wildcard_id = result.inserted_id

    ## update user's amount of wildcards submitted by 1
    await users_collection.update_one(
        {"user_id": user_id},
        {
            "$inc": {"wildcard_count": 1},
            "$set": {"username": interaction.user.name}
        },
        upsert=True
    )

    # create the embed
    embed = discord.Embed(
        title="New wildcard submission",
        description=wildcard,
        color=discord.Color.purple()
    )
    embed.set_author(name=interaction.user.name,
                     icon_url=interaction.user.avatar.url if interaction.user.avatar else None)
    embed.set_footer(text="Vote using the buttons below (Votes are hidden)")

    ## send into the channel
    await interaction.response.send_message(embed=embed, view=WildcardVoteView(wildcard_id))


ADMIN_ROLE_ID = 1440756072532152360
@bot.tree.command(name="theme_results", description="(ADMIN ONLY) View current theme idea voting results")
async def theme_results(interaction: discord.Interaction):
    try:
        print(f"Theme results command called by {interaction.user.name}")

        # defer so we get longer to calc result
        await interaction.response.defer(ephemeral=True)
        print("Response deferred")


        if not any(role.id == ADMIN_ROLE_ID for role in interaction.user.roles):
            await interaction.followup.send(">:C hey, no cheating, only admins can see this!!!! ", ephemeral=True)
            return

        print("Fetching theme ideas from database...")
        # fill theme ideas list with results
        theme_ideas_list = []
        async for theme_idea in theme_ideas_collection.find({}):
            yes_count = theme_idea.get('yes_count', 0)
            no_count = theme_idea.get('no_count', 0)
            net_score = yes_count - no_count

            theme_ideas_list.append({
                'theme_idea': theme_idea,
                'net_score': net_score,
                'yes_count': yes_count,
                'no_count': no_count
            })

        print(f"Found {len(theme_ideas_list)} theme ideas")

        if not theme_ideas_list:
            await interaction.followup.send("nothing added to theme ideas yet", ephemeral=True)
            return

        # sort by net score
        theme_ideas_list.sort(key=lambda x: x['net_score'], reverse=True)

        print("Creating embed...")
        # create result blob
        embed = discord.Embed(
            title="super secret theme voting results",
            description="Current vote counts for all submitted theme ideas",
            color=discord.Color.gold()
        )

        for idx, item in enumerate(theme_ideas_list, 1):
            theme_idea_data = item['theme_idea']
            yes_count = item['yes_count']
            no_count = item['no_count']
            net_score = item['net_score']
            total_votes = yes_count + no_count

            username = theme_idea_data.get('username', 'Unknown')
            idea_text = theme_idea_data.get('theme_idea', 'No description')

            embed.add_field(
                name=f"#{idx} - {idea_text[:100]}",
                value=f"By: {username}\n✅ Yes: {yes_count} | ❌ No: {no_count} | **Net: {net_score}** | Total: {total_votes}",
                inline=False
            )

        embed.set_footer(text=f"Total theme ideas: {len(theme_ideas_list)}")

        await interaction.followup.send(embed=embed, ephemeral=True)

    except Exception as e:
        print(f"ERROR in theme results command: {e}")
        import traceback
        traceback.print_exc()
        try:
            await interaction.followup.send(f"An error occurred: {str(e)}", ephemeral=True)
        except:
            pass


@bot.tree.command(name="wildcard_results", description="(ADMIN ONLY) View current wildcard voting results")
async def wildcard_results(interaction: discord.Interaction):
    try:
        print(f"Wildcard results command called by {interaction.user.name}")

        # defer so we get longer to calc result
        await interaction.response.defer(ephemeral=True)
        print("Response deferred")

        ADMIN_ROLE_ID = 1440756072532152360
        if not any(role.id == ADMIN_ROLE_ID for role in interaction.user.roles):
            await interaction.followup.send(">:C hey, no cheating, only admins can see this!!!! ", ephemeral=True)
            return

        print("Fetching wildcards from database...")
        # fill wildcards list with results
        wildcards_list = []
        async for wildcard in wildcards_collection.find({}):
            yes_count = wildcard.get('yes_count', 0)
            no_count = wildcard.get('no_count', 0)
            net_score = yes_count - no_count

            wildcards_list.append({
                'wildcard': wildcard,
                'net_score': net_score,
                'yes_count': yes_count,
                'no_count': no_count
            })

        print(f"Found {len(wildcards_list)} wildcards")

        if not wildcards_list:
            await interaction.followup.send("nothing added to wildcards yet", ephemeral=True)
            return

        # sort by net score
        wildcards_list.sort(key=lambda x: x['net_score'], reverse=True)

        print("Creating embed...")
        # create result blob
        embed = discord.Embed(
            title="super secret wildcard voting results",
            description="Current vote counts for all submitted wildcards",
            color=discord.Color.gold()
        )

        for idx, item in enumerate(wildcards_list, 1):
            wildcard_data = item['wildcard']
            yes_count = item['yes_count']
            no_count = item['no_count']
            net_score = item['net_score']
            total_votes = yes_count + no_count

            username = wildcard_data.get('username', 'Unknown')
            wildcard_text = wildcard_data.get('wildcard', 'No description')

            embed.add_field(
                name=f"#{idx} - {wildcard_text[:100]}",
                value=f"By: {username}\n✅ Yes: {yes_count} | ❌ No: {no_count} | **Net: {net_score}** | Total: {total_votes}",
                inline=False
            )

        embed.set_footer(text=f"Total wildcards: {len(wildcards_list)}")

        await interaction.followup.send(embed=embed, ephemeral=True)

    except Exception as e:
        print(f"ERROR in wildcard results command: {e}")
        import traceback
        traceback.print_exc()
        try:
            await interaction.followup.send(f"An error occurred: {str(e)}", ephemeral=True)
        except:
            pass


@bot.event
async def on_ready():
    print("on_ready triggered")

    # mongo db connection test
    try:
        await mongo_client.admin.command('ping')
        print("MongoDB connected")
    except Exception as e:
        print(f"MongoDB fail : {e}")

    print("About to sync commands...")

    # sync the / commands
    try:
        synced = await bot.tree.sync()
        print(f"Commands synced: {len(synced)}")
    except Exception as e:
        print(f"Sync failed: {e}")
        import traceback
        traceback.print_exc()

    print(f'{bot.user} is active')
    print(f'{len(synced)} commands on')
    for cmd in synced:
        print(f' cmds available : {cmd.name}')

    # FOR IF THE BOTS CONNECTION JUST DIES, refill in values
    print("refilling values")
    theme_idea_count = 0
    wildcard_count = 0
    try:
        async for theme_idea in theme_ideas_collection.find({}):
            bot.add_view(ThemeVoteView(theme_idea['_id']))
            theme_idea_count += 1
        print(f"Loaded {theme_idea_count} persistent theme vote views")

        async for wildcard in wildcards_collection.find({}):
            bot.add_view(WildcardVoteView(wildcard['_id']))
            wildcard_count += 1
        print(f"Loaded {wildcard_count} persistent wildcard vote views")
    except Exception as e:
        print(f"Error loading views: {e}")

    print("everything set up")


# turn off ssl for localhost (my pc is acting funny)
original_connector = aiohttp.TCPConnector


class NoSSLConnector(aiohttp.TCPConnector):
    def __init__(self, *args, **kwargs):
        kwargs['ssl'] = False
        super().__init__(*args, **kwargs)


aiohttp.TCPConnector = NoSSLConnector

keep_alive()  ## little sneaky trick

# Run bot
print("bot now runs")
bot.run(token, log_handler=handler, log_level=logging.DEBUG)