# bot.py

import discord
from discord.ext import commands
from pretty_help import PrettyHelp

from aiohttp import ClientSession, ClientTimeout

import json
import sys
import os
import logging
import Levenshtein as lev

from . import cogs
from .cogs.utils import utils
from .cogs.utils.db import DB
from .resources import Sessions, Config


_CWD = os.path.dirname(os.path.abspath(__file__))
INTENTS_JSON = os.path.join(_CWD, 'intents.json')


class G5Bot(commands.AutoShardedBot):
    """ Sub-classed AutoShardedBot modified to fit the needs of the application. """

    def __init__(self):
        """ Set attributes and configure bot. """
        # Call parent init
        with open(INTENTS_JSON) as f:
            intents_attrs = json.load(f)

        intents = discord.Intents(**intents_attrs)
        help_menu = PrettyHelp(sort_commands=False)
        super().__init__(command_prefix=Config.prefixes,
                         help_command=help_menu, case_insensitive=True, intents=intents)

        # Set argument attributes
        self.all_maps = {}

        # Set constants
        self.logo = 'https://images.discordapp.net/avatars/816798869421031435/532ee52c63bf04c59388cd13cc08cd3a.png?size=128'
        self.color = 0x0086FF
        self.logger = logging.getLogger('G5.bot')

        # Add check to not respond to DM'd commands
        self.add_check(lambda ctx: ctx.guild is not None)

        # Trigger typing before every command
        self.before_invoke(commands.Context.trigger_typing)

        # Add cogs
        for cog in cogs.__all__:
            self.add_cog(cog(self))

    async def on_error(self, event_method, *args, **kwargs):
        """"""
        try:
            logging_cog = self.get_cog('LoggingCog')
            exc_type, exc_value, traceback = sys.exc_info()
            logging_cog.log_exception(
                f'Uncaught exception when handling "{event_method}" event:', exc_value)
        except Exception as e:
            print(e)

    def embed_template(self, **kwargs):
        """ Implement the bot's default-style embed. """
        if 'color' not in kwargs:
            kwargs['color'] = self.color
        embed = discord.Embed(**kwargs)
        embed.set_author(
            name='G5', url='https://top.gg/bot/816798869421031435', icon_url=self.logo)
        return embed

    @commands.Cog.listener()
    async def on_connect(self):
        Sessions.requests = ClientSession(
            loop=self.loop,
            json_serialize=lambda x: json.dumps(x, ensure_ascii=False),
            timeout=ClientTimeout(total=5),
            trace_configs=[cogs.logging.TRACE_CONFIG]
        )

    @commands.Cog.listener()
    async def on_ready(self):
        """ Synchronize the guilds the bot is in with the guilds table. """
        match_cog = self.get_cog('Match Category')

        if self.guilds:
            await DB.sync_guilds(*(guild.id for guild in self.guilds))
            self.logger.info('Checking maps emojis...')
            await utils.create_emojis(self)

            if not match_cog.check_matches.is_running():
                match_cog.check_matches.start()

            self.logger.info('Bot is ready now!')

    @commands.Cog.listener()
    async def on_guild_join(self, guild):
        """ Insert the newly added guild to the guilds table. """
        await DB.sync_guilds(*(guild.id for guild in self.guilds))

    @commands.Cog.listener()
    async def on_guild_remove(self, guild):
        """ Delete the recently removed guild from the guilds table. """
        await DB.sync_guilds(*(guild.id for guild in self.guilds))

    @commands.Cog.listener()
    async def on_command_error(self, ctx, error):
        """"""
        if isinstance(error, commands.MissingPermissions):
            await ctx.trigger_typing()
            missing_perm = error.missing_perms[0].replace('_', ' ')
            embed = self.embed_template(title=utils.trans(
                'command-required-perm', missing_perm), color=0xFF0000)
            await ctx.message.reply(embed=embed)

        if isinstance(error, commands.UserInputError):
            await ctx.trigger_typing()
            embed = self.embed_template(
                description='**' + str(error) + '**', color=0xFF0000)
            await ctx.message.reply(embed=embed)

        if isinstance(error, commands.CommandNotFound):
            # Get Levenshtein distance from commands
            in_cmd = ctx.invoked_with
            bot_cmds = list(self.commands)
            lev_dists = [lev.distance(in_cmd, str(
                cmd)) / max(len(in_cmd), len(str(cmd))) for cmd in bot_cmds]
            lev_min = min(lev_dists)

            # Prep help message title
            embed_title = utils.trans('help-not-valid', ctx.message.content)
            prefixes = self.command_prefix
            # Prefix can be string or iterable of strings
            prefix = prefixes[0] if prefixes is not str else prefixes

            # Make suggestion if lowest Levenshtein distance is under threshold
            if lev_min <= 0.5:
                embed_title += utils.trans('help-did-you-mean') + \
                    f' `{prefix}{bot_cmds[lev_dists.index(lev_min)]}`?'
            else:
                embed_title += utils.trans('help-use-help', prefix)

            embed = self.embed_template(title=embed_title)
            await ctx.message.reply(embed=embed)

    def run(self):
        """ Override parent run to automatically include Discord token. """
        super().run(Config.discord_token)

    async def close(self):
        """ Override parent close to close the API session and DB connection pool. """
        await super().close()
        await DB.close()

        self.logger.info('Closing API helper client session')
        await Sessions.requests.close()
