from datetime import datetime, time, timedelta
from discord.utils import get
import emoji

DEFAULT_EXPIRE = 3 #Default days of expiration

class Event:
    def __init__(self, id_num, ctx, author, args, expire=None):
        self.id = id_num
        self.ctx = ctx
        self.author = author
        self.args = args
        self.message = None
        self.reactions = [] #List of (Reaction, User) Tuples
        self.rsvp_list = [] #Users who have been asked to rsvp
        self.status = {}
        self.expire = expire

        for arg in args:
            if arg == "req":
                var = " ".join(args[arg])
                if get(ctx.guild.roles, name=var): #Name passed is a group
                    for member in get(ctx.guild.roles, name=var).members:
                        self.rsvp_list.append(member)
            if arg == "expire" and self.expire is None:
                try:
                    self.expire = datetime.strptime(" ".join(args[arg]), "%m/%d/%Y %H:%M")
                except:
                    args["expire"] = datetime.strftime(datetime.now() + timedelta(days = DEFAULT_EXPIRE), "%m/%d/%Y %H:%M")
                    self.expire = args["expire"]
        
        for member in self.rsvp_list:
            self.status[member] = "grey_question"
        

    async def selfDestruct(self):
        await self.message.delete() #Remove message on destruction
    
    async def ProcessReactions(self):
        for reaction in self.reactions:
            if reaction[1] not in self.rsvp_list: #Users reaction is not important
                pass

            elif reaction[0].custom_emoji:
                pass

            else:
                demoji = emoji.demojize(str(reaction[0]))
                if demoji in [":check_mark_button:", ":cross_mark:", ":red_exclamation_mark:"]:
                    if demoji == ":check_mark_button:":
                        self.status[reaction[1]] = "white_check_mark"
                    elif demoji == ":cross_mark:":
                        self.status[reaction[1]] = "x"
                    elif demoji == ":red_exclamation_mark:":
                        self.status[reaction[1]] = "exclamation"
        
        
        await self.message.edit(content=self.CreateString())

    async def ImportReact(self):
        if self.message is not None:
            for reaction in self.message.reactions:
                async for user in reaction.users():
                    self.reactions.append((reaction,user))

    def CreateString(self):
        sendString = f"{self.author} is creating an event: \n"
        sendString += "----------------------------------\n"
        for arg in self.args:
            if arg == "message": #User is adding a message
                sendString += "**" + " ".join(self.args[arg]) + "**\n" #Append any message, such as "Climbing at ET on Saturday 0900"

            elif arg == "req": #User is requesting certain users or groups to be pinged
                sendString += " They have requested that the following individuals respond:\n"
                var = " ".join(self.args[arg])
                if get(self.ctx.guild.roles, name=var): #Name passed is a group
                    for member in get(self.ctx.guild.roles, name=var).members:
                        sendString += f"\t\t {member.mention} \t:{self.status.get(member)}:\n"

        return sendString
    
    def JsonDump(self):
        dictionary = { "guild_id": self.ctx.guild.id, 
                       "channel_id": self.ctx.channel.id, 
                       "message_id": self.message.id, 
                       "author_id": self.author.id, 
                       "args": self.args
                    }

        string = f"{self.id}: {dictionary}"
        return string
