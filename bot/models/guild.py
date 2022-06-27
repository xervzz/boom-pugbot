# guild.py

from typing import List
from ..cogs.utils.db import DB
from ..cogs .utils.utils import trans
from discord.ext import commands


class Guild:
    """"""

    def __init__(self, guild, auth, linked_role, prematch_channel, category):
        """"""
        self.guild = guild
        self.auth = auth
        self.linked_role = linked_role
        self.prematch_channel = prematch_channel
        self.category = category
        self.is_setup = any(auth.values()) and linked_role and prematch_channel

    @classmethod
    def from_dict(cls, bot, guild_data: dict):
        """"""
        guild = bot.get_guild(guild_data['id'])
        return cls(
            guild,
            {'user-api': guild_data['api_key']},
            guild.get_role(guild_data['linked_role']),
            guild.get_channel(guild_data['prematch_channel']),
            guild.get_channel(guild_data['category'])
        )

    @staticmethod
    async def get_guild(bot, guild_id: int):
        """"""
        try:
            sql = "SELECT * FROM guilds\n" \
                f"    WHERE id =  {guild_id};"
            guild_data = await DB.fetch_row(sql)
            if guild_data:
                return Guild.from_dict(bot, guild_data)
        except Exception:
            pass

    @staticmethod
    async def get_guilds(bot, guild_ids: List[int]):
        """"""
        return [await Guild.get_guild(bot, guild_id) for guild_id in guild_ids]

    @staticmethod
    async def update_guild(guild_id: int, data: dict):
        """"""
        col_vals = ",\n    ".join(
            f"{key} = {val}" for key, val in data.items())
        sql = 'UPDATE guilds\n' \
            f'    SET {col_vals}\n' \
            f'    WHERE id = {guild_id};'
        await DB.query(sql)

    def is_guild_setup():
        async def predicate(ctx):
            db_guild = await Guild.get_guild(ctx.bot, ctx.guild.id)
            if not db_guild.is_setup:
                title = trans('bot-not-setup', ctx.bot.command_prefix[0])
                embed = ctx.bot.embed_template(title=title, color=0xFF0000)
                await ctx.message.reply(embed=embed)
                return False
            return True

        return commands.check(predicate)
