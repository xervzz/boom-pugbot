# setup.py

from discord.ext import commands

from bot.resources import Config
from .utils import utils, api
from .. import models


class SetupCog(commands.Cog, name='Setup Category', description=utils.trans('setup-desc')):
    """"""

    def __init__(self, bot):
        """"""
        self.bot = bot

    @commands.command(brief=utils.trans('help-info-brief'))
    async def info(self, ctx):
        """ Display the info embed. """
        description = utils.trans("help-bot-description", Config.web_panel,
                                  self.bot.command_prefix[0], self.bot.command_prefix[0])
        embed = self.bot.embed_template(
            title='__G5 Bot__', description=description)
        embed.set_thumbnail(url=self.bot.logo)
        await ctx.message.reply(embed=embed)

    @commands.command(brief=utils.trans('command-setup-brief'),
                      usage='setup <API Key>')
    @commands.has_permissions(administrator=True)
    async def setup(self, ctx, *args):
        """"""
        try:
            api_key = args[0]
        except IndexError:
            msg = utils.trans(
                'invalid-usage', self.bot.command_prefix[0], ctx.command.usage)
            raise commands.UserInputError(message=msg)

        try:
            await api.check_auth({'user-api': api_key})
        except Exception as e:
            raise commands.UserInputError(message=str(e))

        guild_mdl = await models.Guild.get_guild(self.bot, ctx.guild.id)
        category = guild_mdl.category
        linked_role = guild_mdl.linked_role
        prematch_channel = guild_mdl.prematch_channel

        if not category:
            category = await ctx.guild.create_category_channel('G5')
        if not linked_role:
            linked_role = await ctx.guild.create_role(name='Linked')
        if not prematch_channel:
            prematch_channel = await ctx.guild.create_voice_channel(category=category, name='Pre-Match')

        dict_data = {
            'api_key': f"'{api_key}'",
            'category': category.id,
            'linked_role': linked_role.id,
            'prematch_channel': prematch_channel.id
        }
        await models.Guild.update_guild(ctx.guild.id, dict_data)

        msg = utils.trans('setup-bot-success')
        embed = self.bot.embed_template(title=msg)
        await ctx.message.reply(embed=embed)
