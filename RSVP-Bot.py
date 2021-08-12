from json.decoder import JSONDecodeError
import discord, json
from discord.ext import commands, tasks
from discord.utils import get
from Event import Event
import emoji
from datetime import datetime
import asyncio



description = "Manages RSVP's. Pings all requested users and tracks responses."
intents = discord.Intents.default()
intents.members = True
intents.reactions = True
intents.emojis = True


BOT = commands.Bot(command_prefix='/', description=description, intents=intents)
ID_NUM = 0 #Each event is assigned a unique ID for record keeping (incr by one)
EVENTS = []
LOG_FILE = "logfile.txt"

class ExpireCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.CheckTimeout.start()
    
    @tasks.loop(minutes=5)
    async def CheckTimeout(self):
        global EVENTS

        print("Checking if any events have expired")
        for event in EVENTS:
            if (datetime.now() > event.expire): #Event has expired
                await event.selfDestruct()
                EVENTS.remove(event)
        Export(LOG_FILE)

@BOT.event
async def on_ready():
    print(f"Logged in as {BOT.user.name}")
    await Import(LOG_FILE)
    await asyncio.sleep(60)
    ExpireCog(BOT)

@BOT.command(name="rsvp", pass_context=True)
async def CreateEvent(ctx):
    global EVENTS
    global ID_NUM

    args = ArgParser(ctx.message.content)
    await ctx.message.delete() #Delete the command request message

    newEvent = Event(ID_NUM, ctx, ctx.author, args)
    EVENTS.append(newEvent)
    newEvent.message = await ctx.send(newEvent.CreateString())    
    ID_NUM += 1
    Export(LOG_FILE)        

@BOT.event
async def on_raw_reaction_add(payload):
    global EVENTS

    msg = await BOT.get_channel(payload.channel_id).fetch_message(payload.message_id)
    reaction = get(msg.reactions, emoji=payload.emoji.name)
    user = payload.member
    
    if (user and reaction):
        for event in EVENTS:
            if event.message.id == msg.id: #Reaction was added to a valid comp event
                print(f"User {user} has reacted with {payload.emoji.name}")
                event.reactions.append((reaction,user)) #Add reaction to list of reactions for specific event
                
            await event.ProcessReactions()


@BOT.event
async def on_raw_reaction_remove(payload):

    msg = await BOT.get_channel(payload.channel_id).fetch_message(payload.message_id)
    guild = BOT.get_guild(payload.guild_id)

    if guild is None:
        return
    
    user = guild.get_member(payload.user_id)

    if user is not None:
        for event in EVENTS:
            if event.message.id == msg.id: #Reaction was removed from a valid comp event
                print(f"User {user} has removed their reaction of {payload.emoji.name}")
                for react in event.reactions:
                    if emoji.demojize(str(react[0])) == emoji.demojize(payload.emoji.name) and react[1] == user:
                        event.reactions.remove(react) #Remove reaction from reaction list
                        event.status[user] = "grey_question" #Until reprocessed, assume the user removed all roles

            await event.ProcessReactions()
        
def ArgParser(command):
    argsParsed = {}
    cmd = command.split()
    for word in cmd[1:]:
        index = cmd.index(word)
        if word.startswith('--'):
            args = []
            try:
                for var in cmd[index+1:]:
                    if not var.startswith('--'):
                        args.append(var)
                    else:
                        break
                argsParsed[word[2:]] = args

            except IndexError:
                argsParsed[word[2:]] = args

    return argsParsed

def RetrieveToken():
    #Definately better ways to handle this
    with open("DISCORD_TOKEN.txt","r") as file:
        token = file.read()
        file.close()
    
    return token

def Export(fileName):
    with open(fileName, "w") as f:
        output = "{"
        numEvents = len(EVENTS)
        eventCounter = 0
        for event in EVENTS:
            eventCounter += 1
            #output += event.JsonDump()
            output += f'"{event.id}":{{"guild_id": {event.ctx.guild.id}, "channel_id": {event.ctx.channel.id}, "message_id": {event.message.id}, "author_id": {event.author.id}, "args": {json.dumps(event.args)}}}'
            if eventCounter != numEvents: #Need a comma delimiter
                output += ", "
        output += "}"
        f.write(output)
        #json.dump(output, f)
    print("Completed export to file.")

async def Import(fileName):
    global EVENTS


    try:
        with open(fileName, "r") as f:
            EVENTS.clear()
            jsonString = json.load(f)

            for event in jsonString:
                event_id = int(event)
                guild_id = int(jsonString[event]["guild_id"])
                channel_id = int(jsonString[event]["channel_id"])
                message_id = int(jsonString[event]["message_id"])
                if guild_id is not None:
                    guild = BOT.get_guild(guild_id)
                    if guild is not None:
                        author = await guild.fetch_member(jsonString[event]["author_id"])

                args = {}
                for flag in jsonString[event]["args"]:
                    args[flag] = jsonString[event]["args"][flag]
                
                expire = datetime.strptime(" ".join(jsonString[event]["args"]["expire"]), "%m/%d/%Y %H:%M")
                channel = BOT.get_channel(channel_id)
                message = await channel.fetch_message(message_id)

                ctx = await BOT.get_context(message)
                newEvent = Event(event_id, ctx, author, args, expire)
                newEvent.message = message
                await newEvent.ImportReact() #Check for any reactions after we set the message
                await newEvent.ProcessReactions()

                EVENTS.append(newEvent)

    except FileNotFoundError:
        pass
    except JSONDecodeError:
        raise

    print("Completed import from file.")

def main():
    BOT.run(RetrieveToken())
 

if __name__ == '__main__':
    main()