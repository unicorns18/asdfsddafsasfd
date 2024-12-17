import interactions
from interactions import Extension, slash_command, Embed, Button, ButtonStyle, ComponentCommand, listen, Guild, \
    ComponentContext
from typing import Optional

class RolesExtension(Extension):
    def __init__(self, bot):
        self.bot = bot
        self.role_type_map = {
            "Buyer": 1273737954874884176,
            "Seller": 1273738137897799782,
            "SFW-Only Seller": 1275288485078634537
        }
        self.role_pronouns_map = {
            "He/him": 1273738502093275197,
            "She/her": 1273738255841624165,
            "They/them": 1273738409877442680,
            "Ask My Pronouns": 1275288797189505025
        }
        self.role_country_map = {
            "USA": 1275293088847499324,
            "EU": 1275293109240074260,
            "BR": 1275293127594213396,
            "Other world zone": 1275293219562721280
        }
        # TODO: Figure out a better name for this
        self.role_suits_you_best_map = {
            "Music Viber": 1275300717883555881,
            "Pet Owner": 1275300662405763112,
            "Artist": 1275300542977151046,
            "Gamer": 1275300482453082122,
            "Movie Watcher": 1275300283441741867,
        }
        self.age_role_map = {
            "18+": 1267921174529048649,
            "18-" :1267921264392011878
        }

    @slash_command(
        name="sendfancyroles",
        description="Send all role selection menus",
    )
    async def sendfancyroles(self, ctx):
        # Role type embed and buttons
        type_embed = Embed(
            title="Role Type Selection",
            description="Please select your role type:\n\n"
                        "💸 **Buyer**\n"
                        "💼 **Seller**\n"
                        "👔 **SFW-Only Seller**",
            color=0x2b2d31
        )
        type_buttons = [
            Button(
                style=ButtonStyle.PRIMARY,
                label="Buyer",
                custom_id="type_buyer"
            ),
            Button(
                style=ButtonStyle.PRIMARY,
                label="Seller",
                custom_id="type_seller"
            ),
            Button(
                style=ButtonStyle.PRIMARY,
                label="SFW-Only Seller",
                custom_id="type_sfw_seller"
            )
        ]
        await ctx.channel.send(embed=type_embed, components=type_buttons)

        # Age roles embed and buttons
        age_embed = Embed(
            title="Age Role Selection",
            description="Please select your age role:\n\n"
                        "💜 **18+**\n"
                        "💙 **18-**",
            color=0x2b2d31
        )
        age_buttons = [
            Button(
                style=ButtonStyle.PRIMARY,
                label="18+",
                custom_id="age_18plus"
            ),
            Button(
                style=ButtonStyle.PRIMARY,
                label="18-",
                custom_id="age_18minus"
            )
        ]
        await ctx.channel.send(embed=age_embed, components=age_buttons)

        # Pronoun roles embed and buttons
        pronoun_embed = Embed(
            title="Pronoun Role Selection",
            description="Please select your pronouns:\n\n"
                        "💙 **He/him**\n"
                        "💗 **She/her**\n"
                        "💜 **They/them**\n"
                        "💚 **Ask My Pronouns**",
            color=0x2b2d31
        )
        pronoun_buttons = [
            Button(
                style=ButtonStyle.PRIMARY,
                label="He/him",
                custom_id="pronouns_he"
            ),
            Button(
                style=ButtonStyle.PRIMARY,
                label="She/her",
                custom_id="pronouns_she"
            ),
            Button(
                style=ButtonStyle.PRIMARY,
                label="They/them",
                custom_id="pronouns_they"
            ),
            Button(
                style=ButtonStyle.PRIMARY,
                label="Ask My Pronouns",
                custom_id="pronouns_ask"
            )
        ]
        await ctx.channel.send(embed=pronoun_embed, components=pronoun_buttons)

        # Country roles embed and buttons
        country_embed = Embed(
            title="Country Role Selection",
            description="Please select your country role:\n\n"
                        ":flag_us: **USA**\n"
                        ":flag_eu: **EU**\n"
                        ":flag_br: **BR**\n"
                        "🌍 **Other world zone**",
            color=0x2b2d31
        )

        country_buttons = [
            Button(
                style=ButtonStyle.PRIMARY,
                label="USA",
                custom_id="country_usa"
            ),
            Button(
                style=ButtonStyle.PRIMARY,
                label="EU",
                custom_id="country_eu"
            ),
            Button(
                style=ButtonStyle.PRIMARY,
                label="BR",
                custom_id="country_br"
            ),
            Button(
                style=ButtonStyle.PRIMARY,
                label="Other world zone",
                custom_id="country_other"
            )
        ]
        await ctx.channel.send(embed=country_embed, components=country_buttons)

        # Suits you best roles embed and buttons
        suits_you_best_embed = Embed(
            title="Suits You Best Role Selection",
            description="Please select the role that suits you best:\n\n"
                        "🎵 **Music Viber**\n"
                        "🐾 **Pet Owner**\n"
                        "🎨 **Artist**\n"
                        "🎮 **Gamer**\n"
                        "🎬 **Movie Watcher**",
            color=0x2b2d31
        )

        suits_you_best_buttons = [
            Button(
                style=ButtonStyle.PRIMARY,
                label="Music Viber",
                custom_id="suits_you_best_music"
            ),
            Button(
                style=ButtonStyle.PRIMARY,
                label="Pet Owner",
                custom_id="suits_you_best_pet"
            ),
            Button(
                style=ButtonStyle.PRIMARY,
                label="Artist",
                custom_id="suits_you_best_artist"
            ),
            Button(
                style=ButtonStyle.PRIMARY,
                label="Gamer",
                custom_id="suits_you_best_gamer"
            ),
            Button(
                style=ButtonStyle.PRIMARY,
                label="Movie Watcher",
                custom_id="suits_you_best_movie"
            )
        ]
        await ctx.channel.send(embed=suits_you_best_embed, components=suits_you_best_buttons)

        await ctx.send("Role selection menus have been sent.", ephemeral=True)

    @interactions.component_callback("type_buyer")
    async def type_buyer(self, ctx):
        await ctx.author.add_roles([self.role_type_map["Buyer"]])
        await ctx.send("You have been given the Buyer role.", ephemeral=True)

    @interactions.component_callback("type_seller")
    async def type_seller(self, ctx):
        await ctx.author.add_roles([self.role_type_map["Seller"]])
        await ctx.send("You have been given the Seller role.", ephemeral=True)

    @interactions.component_callback("type_sfw_seller")
    async def type_sfw_seller(self, ctx):
        await ctx.author.add_roles([self.role_type_map["SFW-Only Seller"]])
        await ctx.send("You have been given the SFW-Only Seller role.", ephemeral=True)

    @interactions.component_callback("age_18plus")
    async def age_18plus(self, ctx):
        minus_role = ctx.guild.get_role(self.age_role_map["18-"])
        if minus_role in ctx.author.roles:
            await ctx.author.remove_roles([minus_role])
        await ctx.author.add_roles([self.age_role_map["18+"]])
        await ctx.send("You have been given the 18+ role.", ephemeral=True)

    @interactions.component_callback("age_18minus")
    async def age_18minus(self, ctx):
        plus_role = ctx.guild.get_role(self.age_role_map["18+"])
        if plus_role in ctx.author.roles:
            await ctx.author.remove_roles([plus_role])
        await ctx.author.add_roles([self.age_role_map["18-"]])
        await ctx.send("You have been given the 18- role.", ephemeral=True)

    @interactions.component_callback("pronouns_he")
    async def pronouns_he(self, ctx):
        await ctx.author.add_roles([self.role_pronouns_map["He/him"]])
        await ctx.send("You have been given the He/him role.", ephemeral=True)

    @interactions.component_callback("pronouns_she")
    async def pronouns_she(self, ctx):
        await ctx.author.add_roles([self.role_pronouns_map["She/her"]])
        await ctx.send("You have been given the She/her role.", ephemeral=True)

    @interactions.component_callback("pronouns_they")
    async def pronouns_they(self, ctx):
        await ctx.author.add_roles([self.role_pronouns_map["They/them"]])
        await ctx.send("You have been given the They/them role.", ephemeral=True)

    @interactions.component_callback("pronouns_ask")
    async def pronouns_ask(self, ctx):
        await ctx.author.add_roles([self.role_pronouns_map["Ask My Pronouns"]])
        await ctx.send("You have been given the Ask My Pronouns role.", ephemeral=True)

    @interactions.component_callback("country_usa")
    async def country_usa(self, ctx):
        await ctx.author.add_roles([self.role_country_map["USA"]])
        await ctx.send("You have been given the USA role.", ephemeral=True)

    @interactions.component_callback("country_eu")
    async def country_eu(self, ctx):
        await ctx.author.add_roles([self.role_country_map["EU"]])
        await ctx.send("You have been given the EU role.", ephemeral=True)

    @interactions.component_callback("country_br")
    async def country_br(self, ctx):
        await ctx.author.add_roles([self.role_country_map["BR"]])
        await ctx.send("You have been given the BR role.", ephemeral=True)

    @interactions.component_callback("country_other")
    async def country_other(self, ctx):
        await ctx.author.add_roles([self.role_country_map["Other world zone"]])
        await ctx.send("You have been given the Other world zone role.", ephemeral=True)

    @interactions.component_callback("suits_you_best_music")
    async def suits_you_best_music(self, ctx):
        await ctx.author.add_roles([self.role_suits_you_best_map["Music Viber"]])
        await ctx.send("You have been given the Music Viber role.", ephemeral=True)

    @interactions.component_callback("suits_you_best_pet")
    async def suits_you_best_pet(self, ctx):
        await ctx.author.add_roles([self.role_suits_you_best_map["Pet Owner"]])
        await ctx.send("You have been given the Pet Owner role.", ephemeral=True)

    @interactions.component_callback("suits_you_best_artist")
    async def suits_you_best_artist(self, ctx):
        await ctx.author.add_roles([self.role_suits_you_best_map["Artist"]])
        await ctx.send("You have been given the Artist role.", ephemeral=True)

    @interactions.component_callback("suits_you_best_gamer")
    async def suits_you_best_gamer(self, ctx):
        await ctx.author.add_roles([self.role_suits_you_best_map["Gamer"]])
        await ctx.send("You have been given the Gamer role.", ephemeral=True)

    @interactions.component_callback("suits_you_best_movie")
    async def suits_you_best_movie(self, ctx):
        await ctx.author.add_roles([self.role_suits_you_best_map["Movie Watcher"]])
        await ctx.send("You have been given the Movie Watcher role.", ephemeral=True)