# link.py

from discord.ext import commands
from steam.steamid import SteamID, from_url

from .utils import utils
from .. import models


class LinkCog(commands.Cog, name='Link Category', description=utils.trans('link-desc')):
    """"""

    def __init__(self, bot):
        """"""
        self.bot = bot

    @commands.command(brief=utils.trans('link-command-brief'),
                      usage='link <steam_id> {OPTIONAL flag_emoji}')
    @models.Guild.is_guild_setup()
    async def link(self, ctx, steam_id=None, flag='🇺🇸'):
        """"""
        user = ctx.author
        if not steam_id:
            msg = utils.trans(
                'invalid-usage', self.bot.command_prefix[0], ctx.command.usage)
            raise commands.UserInputError(message=msg)

        user_mdl = await models.User.get_user(user.id, ctx.guild)
        if user_mdl:
            raise commands.UserInputError(message=utils.trans(
                'account-already-linked', user_mdl.steam))

        try:
            steam = SteamID(steam_id)
        except ValueError:
            raise commands.UserInputError(
                message=utils.trans('invalid-steam-id'))

        if not steam.is_valid():
            steam = from_url(steam_id, http_timeout=15)
            if steam is None:
                steam = from_url(
                    f'https://steamcommunity.com/id/{steam_id}/', http_timeout=15)
                if steam is None:
                    raise commands.UserInputError(
                        message=utils.trans('invalid-steam-id'))

        if flag not in utils.FLAG_CODES:
            raise commands.UserInputError(
                message=utils.trans('invalid-flag-emoji'))

        try:
            await models.User.insert_user(user.id, steam, flag)
        except Exception:
            raise commands.UserInputError(
                message=utils.trans('steam-linked-to-another-user'))

        guild_mdl = await models.Guild.get_guild(self.bot, ctx.guild.id)
        await user.add_roles(guild_mdl.linked_role)
        embed = self.bot.embed_template(description=utils.trans(
            'link-steam-success', user.mention, steam))
        await ctx.message.reply(embed=embed)

    @commands.command(brief=utils.trans('command-unlink-brief'),
                      usage='unlink <mention>')
    @commands.has_permissions(ban_members=True)
    @models.Guild.is_guild_setup()
    async def unlink(self, ctx):
        """"""
        try:
            user = ctx.message.mentions[0]
        except IndexError:
            msg = utils.trans(
                'invalid-usage', self.bot.command_prefix[0], ctx.command.usage)
            raise commands.UserInputError(message=msg)

        user_mdl = await models.User.get_user(user.id, ctx.guild)
        if not user_mdl:
            raise commands.UserInputError(
                message=utils.trans('unable-to-unlink', user.mention))

        await models.User.delete_user(user.id)

        guild_mdl = await models.Guild.get_guild(self.bot, ctx.guild.id)
        await user.remove_roles(guild_mdl.linked_role)
        embed = self.bot.embed_template(
            description=utils.trans('unlink-steam-success', user.mention))
        await ctx.message.reply(embed=embed)
