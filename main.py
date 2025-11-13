import discord
from discord.ext import commands
from discord import app_commands
from motor.motor_asyncio import AsyncIOMotorClient
import logging
from dotenv import load_dotenv
import os
import aiohttp

## maximum amount of ideas for a user to submit to the jam, setting this to 3 for now
from typing import Final # wow i forgot how strange this is to declare finals in python
MAX_AMT_OF_IDEAS: Final = 3

from keep_alive import keep_alive # this tricks the host into running the bot 24/7

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
ideas_collection = db['ideas']
users_collection = db['users']

### HANDLER
handler = logging.FileHandler(filename='discord.log', encoding='utf-8', mode='w')
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix='/', intents=intents)


## this is the main class we use, VoteView
class VoteView(discord.ui.View):

    def __init__(self, idea_id): # on init
        super().__init__(timeout=None)  ## when called, it stays here forever
        self.idea_id = idea_id ## set the id for the mongo db

    @discord.ui.button(label="Yes", style=discord.ButtonStyle.success, custom_id="vote_yes") # vote yes button
    async def vote_yes(self, interaction: discord.Interaction, button: discord.ui.Button): ## on button press
        await self.handle_vote(interaction, "yes") ## calls handle vote with yes input

    @discord.ui.button(label="No", style=discord.ButtonStyle.danger, custom_id="vote_no") # vote no
    async def vote_no(self, interaction: discord.Interaction, button: discord.ui.Button): # on button press
        await self.handle_vote(interaction, "no") ## call handle_vote with no vote

    async def handle_vote(self, interaction: discord.Interaction, vote_type: str): # this is the input of opinion
        user_id = interaction.user.id ## take user id for storing inside mongo

        ## FIRST : retrieve the idea
        idea = await ideas_collection.find_one({"_id": self.idea_id})
        if not idea:
            await interaction.response.send_message("ERROR: could not find the jam idea you clicked on", ephemeral=True)
            return

        voters = idea.get('voters', {}) ## get the current array of voters for this idea
        current_vote = voters.get(str(user_id)) ## get the current vote from userid on this idea
        idea_text = idea.get('idea', 'this idea')

        #first check if weve already voted on this idea, if so then remove it
        if current_vote == "yes":
            idea['yes_count'] = idea.get('yes_count', 0) - 1
        elif current_vote == "no":
            idea['no_count'] = idea.get('no_count', 0) - 1

        ## if we press the same button twice we act like a toggle
        if current_vote == vote_type:
            voters.pop(str(user_id)) # this is how we can remove the user from the voting list for this idea
            await interaction.response.send_message(f"Vote removed for **{idea_text}**", ephemeral=True) #hidden reply to user
        else:
        ## THIS IS HOW WE VOTE FOR FIRST TIME NEW IDEA
            voters[str(user_id)] = vote_type # set vote in the voters array
            if vote_type == "yes":
                idea['yes_count'] = idea.get('yes_count', 0) + 1 ## add into the db +1 to yes
            else:
                idea['no_count'] = idea.get('no_count', 0) + 1 ## same but to no

            vote_emoji = "✅" if vote_type == "yes" else "❌" ## chose which emoji for reply
            await interaction.response.send_message(
                f"Voted {vote_emoji} **{vote_type.upper()}** for **{idea_text}**", ## hidden response
                ephemeral=True
            )

        ## input the changed values into the db
        await ideas_collection.update_one(
            {"_id": self.idea_id}, ## on idea id
            {
                "$set": { ## set new voter array, yes and no count
                    "voters": voters,
                    "yes_count": idea.get('yes_count', 0),
                    "no_count": idea.get('no_count', 0)
                }
            }
        )


@bot.tree.command(name="submit", description="Submit a theme idea for the game jam (You can submit a maximum of 3 and cannot change a submission") ## command for /submit
@app_commands.describe(idea="Your theme idea") # the description (this stinks rn)

async def submit(interaction: discord.Interaction, idea: str): ## on submit
    user_id = interaction.user.id

    # first check amount of ideas submitted by user
    user_data = await users_collection.find_one({"user_id": user_id})
    idea_count = user_data.get('idea_count', 0) if user_data else 0


    if idea_count >= MAX_AMT_OF_IDEAS:
        await interaction.response.send_message("Youve already submitted 3 ideas, You cant add any more :C.", ephemeral=True)
        return

    # intitialize the idea submission
    idea_doc = {
        "user_id": user_id,
        "username": interaction.user.name,
        "idea": idea,
        "yes_count": 0,
        "no_count": 0,
        "voters": {}
    }

    result = await ideas_collection.insert_one(idea_doc)
    idea_id = result.inserted_id

    ##update users amount of ideas submitted by 1
    await users_collection.update_one(
        {"user_id": user_id},
        {
            "$inc": {"idea_count": 1},
            "$set": {"username": interaction.user.name}
        },
        upsert=True
    )

    # create the embed (circley thing on discord)
    embed = discord.Embed(
        title="New theme idea submission",
        description=idea,
        color=discord.Color.blue()
    )
    embed.set_author(name=interaction.user.name, icon_url=interaction.user.avatar.url if interaction.user.avatar else None) ## set author to submittor, can remove this if we dont like it, also fancy image support :)
    embed.set_footer(text="Vote using the buttons below (Votes are hidden)")

    ## send into the channel
    await interaction.response.send_message(embed=embed, view=VoteView(idea_id))


@bot.tree.command(name="results", description="(ADMIN ONLY) View current voting results")
async def results(interaction: discord.Interaction):
    try:
        print(f"Results command called by {interaction.user.name}")

        # defer so we get longer to calc result
        await interaction.response.defer(ephemeral=True)
        print("Response deferred")
        
        ADMIN_ROLE_ID = 760156780822003743
        if not any(role.id == ADMIN_ROLE_ID for role in interaction.user.roles):
            await interaction.followup.send(">:C hey, no cheating, only admins can see this!!!! ", ephemeral=True)
            return

        print("Fetching ideas from database...")
        # fill ideas list with results
        ideas_list = []
        async for idea in ideas_collection.find({}):
            yes_count = idea.get('yes_count', 0)
            no_count = idea.get('no_count', 0)
            net_score = yes_count - no_count

            ideas_list.append({
                'idea': idea,
                'net_score': net_score,
                'yes_count': yes_count,
                'no_count': no_count
            })

        print(f"Found {len(ideas_list)} ideas")

        if not ideas_list:
            await interaction.followup.send("nothing added to ideas yet", ephemeral=True)
            return

        # sort by net score
        ideas_list.sort(key=lambda x: x['net_score'], reverse=True)

        print("Creating embed...")
        # create result blob
        embed = discord.Embed(
            title="super secret voting results",
            description="Current vote counts for all submitted ideas",
            color=discord.Color.gold()
        )

        for idx, item in enumerate(ideas_list, 1):
            idea_data = item['idea']
            yes_count = item['yes_count']
            no_count = item['no_count']
            net_score = item['net_score']
            total_votes = yes_count + no_count

            username = idea_data.get('username', 'Unknown')
            idea_text = idea_data.get('idea', 'No description')

            embed.add_field(
                name=f"#{idx} - {idea_text[:100]}",
                value=f"By: {username}\n✅ Yes: {yes_count} | ❌ No: {no_count} | **Net: {net_score}** | Total: {total_votes}",
                inline=False
            )

        embed.set_footer(text=f"Total ideas: {len(ideas_list)}")

        await interaction.followup.send(embed=embed, ephemeral=True)

    except Exception as e:
        print(f"ERROR in results command: {e}")
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
    idea_count = 0
    try:
        async for idea in ideas_collection.find({}):
            bot.add_view(VoteView(idea['_id']))
            idea_count += 1
        print(f"Loaded {idea_count} persistent views")
    except Exception as e:
        print(f"Error loading views: {e}")

    print("everything set up")

# turn of ssl for localhost (my pc is acting funny)
original_connector = aiohttp.TCPConnector


class NoSSLConnector(aiohttp.TCPConnector):
    def __init__(self, *args, **kwargs):
        kwargs['ssl'] = False
        super().__init__(*args, **kwargs)


aiohttp.TCPConnector = NoSSLConnector


keep_alive() ## little sneaky trick


# Run bot
print("bot now runs")
bot.run(token, log_handler=handler, log_level=logging.DEBUG)
