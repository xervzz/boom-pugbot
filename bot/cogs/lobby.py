# lobby.py

import discord
from discord.ext import commands

from collections import defaultdict
import asyncio

from .utils import utils
from .. import models
from .utils.menus import ReadyMessage, MapPoolMessage


class LobbyCog(commands.Cog, name='Lobby Category', description=utils.trans('lobby-desc')):
    """"""

    def __init__(self, bot):
        self.bot = bot
        self.locked_lobby = {}
        self.locked_lobby = defaultdict(lambda: False, self.locked_lobby)

    @commands.command(brief=utils.trans('display-lobby-command-brief'))
    async def lobbies(self, ctx):
        """"""
        guild_lobbies = await models.Lobby.get_guild_lobbies(self.bot, ctx.guild.id)
        if not guild_lobbies:
            msg = utils.trans('no-lobbies', self.bot.command_prefix[0])
            raise commands.UserInputError(message=msg)

        for lobby in guild_lobbies:
            title = utils.trans('lobby-title', lobby.name, lobby.id)
            desc = f"{utils.trans('lobby-region', lobby.region)}\n" \
                   f"{utils.trans('lobby-capacity', lobby.capacity)}\n" \
                   f"{utils.trans('lobby-series-type', lobby.series)}\n" \
                   f"{utils.trans('lobby-team-method', lobby.team_method)}\n" \
                   f"{utils.trans('lobby-captain-method', lobby.captain_method)}\n" \
                   f"{utils.trans('lobby-map-pool')} {''.join(m.emoji for m in lobby.mpool)}"

            embed = self.bot.embed_template(title=title, description=desc)
            await ctx.send(embed=embed)

    @commands.command(brief=utils.trans('create-lobby-command-brief'),
                      usage='create-lobby <name>',
                      aliases=['create-lobby', 'createlobby'])
    @commands.has_permissions(administrator=True)
    @models.Guild.is_guild_setup()
    async def create_lobby(self, ctx, name=None):
        """"""
        if not name:
            msg = utils.trans(
                'invalid-usage', self.bot.command_prefix[0], ctx.command.usage)
            raise commands.UserInputError(message=msg)

        guild_mdl = await models.Guild.get_guild(self.bot, ctx.guild.id)

        if not guild_mdl.is_setup:
            raise commands.UserInputError(message=utils.trans(
                'bot-not-setup', self.bot.command_prefix[0]))

        dict_data = {'guild': ctx.guild.id, 'name': f"'{name}'"}
        lobby_id = await models.Lobby.insert_lobby(dict_data)
        lobby = await models.Lobby.get_lobby(self.bot, lobby_id[0], ctx.guild.id)

        category = await ctx.guild.create_category_channel(name=f'{lobby.name} lobby (#{lobby.id})')
        queue_channel = await ctx.guild.create_text_channel(category=category, name=f'{lobby.name} setup')
        lobby_channel = await ctx.guild.create_voice_channel(category=category, name=f'{lobby.name} lobby', user_limit=lobby.capacity)

        try:
            await queue_channel.set_permissions(ctx.guild.self_role, send_messages=True)
            await lobby_channel.set_permissions(ctx.guild.self_role, connect=True)
        except discord.InvalidArgument:
            pass
        await queue_channel.set_permissions(ctx.guild.default_role, send_messages=False)
        await lobby_channel.set_permissions(ctx.guild.default_role, connect=False)
        await lobby_channel.set_permissions(guild_mdl.linked_role, connect=True)

        dict_data = {
            'category': category.id,
            'queue_channel': queue_channel.id,
            'lobby_channel': lobby_channel.id
        }
        await models.Lobby.update_lobby(lobby.id, dict_data)

        msg = utils.trans('success-create-lobby', lobby.name)
        embed = self.bot.embed_template(title=msg)
        await ctx.message.reply(embed=embed)

    @commands.command(brief=utils.trans('delete-lobby-command-brief'),
                      usage='delete-lobby <Lobby ID>',
                      aliases=['delete-lobby', 'deletelobby'])
    @commands.has_permissions(administrator=True)
    async def delete_lobby(self, ctx, *args):
        """ Delete the lobby. """
        try:
            lobby_id = int(args[0])
        except (IndexError, ValueError):
            msg = utils.trans(
                'invalid-usage', self.bot.command_prefix[0], ctx.command.usage)
            raise commands.UserInputError(message=msg)

        lobby = await models.Lobby.get_lobby(self.bot, lobby_id, ctx.guild.id)
        if not lobby:
            raise commands.UserInputError(
                message=utils.trans('invalid-lobby-id'))

        await models.Lobby.delete_lobby(lobby.id)

        for chnl in [lobby.lobby_channel, lobby.queue_channel, lobby.category]:
            try:
                await chnl.delete()
            except (AttributeError, discord.NotFound):
                pass

        msg = utils.trans('success-delete-lobby', lobby.name)
        embed = self.bot.embed_template(title=msg)
        await ctx.message.reply(embed=embed)

    @commands.command(usage='cap <Lobby ID> <new capacity>',
                      brief=utils.trans('command-cap-brief'),
                      aliases=['capacity'])
    @commands.has_permissions(administrator=True)
    async def cap(self, ctx, *args):
        """ Set the queue capacity. """
        try:
            new_cap = int(args[1])
            lobby_id = int(args[0])
        except (IndexError, ValueError):
            msg = utils.trans(
                'invalid-usage', self.bot.command_prefix[0], ctx.command.usage)
            raise commands.UserInputError(message=msg)

        lobby = await models.Lobby.get_lobby(self.bot, lobby_id, ctx.guild.id)
        if not lobby:
            raise commands.UserInputError(
                message=utils.trans('invalid-lobby-id'))

        if new_cap == lobby.capacity:
            msg = utils.trans('capacity-already', new_cap)
            raise commands.UserInputError(message=msg)

        if new_cap < 2 or new_cap > 10 or new_cap % 2 != 0:
            msg = utils.trans('capacity-out-range')
            raise commands.UserInputError(message=msg)

        self.locked_lobby[lobby.id] = True
        await models.Lobby.clear_queued_users(lobby.id)
        await models.Lobby.update_lobby(lobby.id, {'capacity': new_cap})
        await self.update_last_msg(lobby, utils.trans('queue-emptied'))

        guild_mdl = await models.Guild.get_guild(self.bot, ctx.guild.id)

        awaitables = []
        for user in lobby.lobby_channel.members:
            awaitables.append(user.move_to(guild_mdl.prematch_channel))
        awaitables.append(lobby.lobby_channel.edit(user_limit=new_cap))
        await asyncio.gather(*awaitables, loop=self.bot.loop, return_exceptions=True)

        self.locked_lobby[lobby.id] = False

        msg = utils.trans('set-capacity', new_cap)
        embed = self.bot.embed_template(title=msg)
        await ctx.message.reply(embed=embed)

    @commands.command(usage='teams <lobby ID> {captains|autobalance|random}',
                      brief=utils.trans('command-teams-brief'),
                      aliases=['team'])
    @commands.has_permissions(administrator=True)
    async def teams(self, ctx, *args):
        """ Set the method by which teams are created. """
        try:
            new_method = args[1].lower()
            lobby_id = int(args[0])
        except (IndexError, ValueError):
            msg = utils.trans(
                'invalid-usage', self.bot.command_prefix[0], ctx.command.usage)
            raise commands.UserInputError(message=msg)

        lobby = await models.Lobby.get_lobby(self.bot, lobby_id, ctx.guild.id)
        if not lobby:
            raise commands.UserInputError(
                message=utils.trans('invalid-lobby-id'))

        curr_method = lobby.team_method
        valid_methods = ['captains', 'autobalance', 'random']

        if new_method not in valid_methods:
            msg = utils.trans(
                'team-valid-methods', valid_methods[0], valid_methods[1], valid_methods[2])
            raise commands.UserInputError(message=msg)

        if curr_method == new_method:
            msg = utils.trans('team-method-already', new_method)
            raise commands.UserInputError(message=msg)

        await models.Lobby.update_lobby(lobby.id, {'team_method': f"'{new_method}'"})

        title = utils.trans('set-team-method', new_method)
        embed = self.bot.embed_template(title=title)
        await ctx.message.reply(embed=embed)

    @commands.command(usage='captains <Lobby ID> {volunteer|rank|random}',
                      brief=utils.trans('command-captains-brief'),
                      aliases=['captain', 'picker', 'pickers'])
    @commands.has_permissions(administrator=True)
    async def captains(self, ctx, *args):
        """ Set the method by which captains are selected. """
        try:
            new_method = args[1].lower()
            lobby_id = int(args[0])
        except (IndexError, ValueError):
            msg = utils.trans(
                'invalid-usage', self.bot.command_prefix[0], ctx.command.usage)
            raise commands.UserInputError(message=msg)

        lobby = await models.Lobby.get_lobby(self.bot, lobby_id, ctx.guild.id)
        if not lobby:
            raise commands.UserInputError(
                message=utils.trans('invalid-lobby-id'))

        curr_method = lobby.captain_method
        valid_methods = ['volunteer', 'rank', 'random']

        if new_method not in valid_methods:
            msg = utils.trans(
                'captains-valid-method', valid_methods[0], valid_methods[1], valid_methods[2])
            raise commands.UserInputError(message=msg)

        if curr_method == new_method:
            msg = utils.trans('captains-method-already', new_method)
            raise commands.UserInputError(message=msg)

        await models.Lobby.update_lobby(lobby.id, {'captain_method': f"'{new_method}'"})

        title = utils.trans('set-captains-method', new_method)
        embed = self.bot.embed_template(title=title)
        await ctx.message.reply(embed=embed)

    @commands.command(usage='series <lobby ID> {bo1|bo2|bo3}',
                      brief=utils.trans('command-series-brief'))
    @commands.has_permissions(administrator=True)
    async def series(self, ctx, *args):
        """ Set series type of the lobby. """
        try:
            new_series = args[1].lower()
            lobby_id = int(args[0])
        except (IndexError, ValueError):
            msg = utils.trans(
                'invalid-usage', self.bot.command_prefix[0], ctx.command.usage)
            raise commands.UserInputError(message=msg)

        lobby = await models.Lobby.get_lobby(self.bot, lobby_id, ctx.guild.id)
        if not lobby:
            raise commands.UserInputError(
                message=utils.trans('invalid-lobby-id'))

        curr_series = lobby.series
        valid_values = ['bo1', 'bo2', 'bo3']

        if new_series not in valid_values:
            msg = utils.trans('series-valid-methods',
                              valid_values[0], valid_values[1], valid_values[2])
            raise commands.UserInputError(message=msg)

        if curr_series == new_series:
            msg = utils.trans('series-value-already', new_series)
            raise commands.UserInputError(message=msg)

        await models.Lobby.update_lobby(lobby.id, {'series_type': f"'{new_series}'"})

        title = utils.trans('set-series-value', new_series)
        embed = self.bot.embed_template(title=title)
        await ctx.message.reply(embed=embed)

    @commands.command(usage='region <lobby ID> {none|region code}',
                      brief=utils.trans('command-region-brief'))
    @commands.has_permissions(administrator=True)
    async def region(self, ctx, *args):
        """ Set or remove the region of the lobby. """
        try:
            new_region = args[1].upper()
            lobby_id = int(args[0])
        except (IndexError, ValueError):
            msg = utils.trans(
                'invalid-usage', self.bot.command_prefix[0], ctx.command.usage)
            raise commands.UserInputError(message=msg)

        lobby = await models.Lobby.get_lobby(self.bot, lobby_id, ctx.guild.id)
        if not lobby:
            raise commands.UserInputError(
                message=utils.trans('invalid-lobby-id'))

        curr_region = lobby.region
        valid_regions = list(utils.FLAG_CODES.values())

        if new_region == 'NONE':
            new_region = None

        if new_region not in [None] + valid_regions:
            msg = utils.trans('region-not-valid')
            raise commands.UserInputError(message=msg)

        if curr_region == new_region:
            msg = utils.trans('lobby-region-already', curr_region)
            raise commands.UserInputError(message=msg)

        region = f"'{new_region}'" if new_region else 'NULL'
        await models.Lobby.update_lobby(lobby.id, {'region': region})

        title = utils.trans('set-lobby-region', new_region)
        embed = self.bot.embed_template(title=title)
        await ctx.message.reply(embed=embed)

    @commands.command(usage='mpool <Lobby ID> ',
                      brief=utils.trans('command-mpool-brief'),
                      aliases=['mappool', 'pool'])
    async def mpool(self, ctx, *args):
        """ Edit the lobby's map pool. """
        try:
            lobby_id = int(args[0])
        except (IndexError, ValueError):
            msg = utils.trans(
                'invalid-usage', self.bot.command_prefix[0], ctx.command.usage)
            raise commands.UserInputError(message=msg)

        lobby = await models.Lobby.get_lobby(self.bot, lobby_id, ctx.guild.id)
        if not lobby:
            raise commands.UserInputError(
                message=utils.trans('invalid-lobby-id'))

        message = await ctx.send('Map Pool')
        menu = MapPoolMessage(message, self.bot, ctx.author, lobby)
        await menu.edit_map_pool()

    async def update_last_msg(self, lobby, title):
        """"""
        queued_ids = await models.Lobby.get_queued_users(lobby.id)

        if title:
            title += f' ({len(queued_ids)}/{lobby.capacity})'

        if len(queued_ids) == 0:
            queue_str = utils.trans('lobby-is-empty')
        else:
            queued_users = [lobby.guild.get_member(
                user_id) for user_id in queued_ids]
            queue_str = ''.join(
                f'{num}. {user.mention}\n' for num, user in enumerate(queued_users, start=1))

        embed = self.bot.embed_template(title=title, description=queue_str)
        embed.set_footer(text=utils.trans('lobby-footer'))

        try:
            msg = await lobby.last_message.fetch()
            await msg.edit(embed=embed)
        except (AttributeError, discord.NotFound, discord.HTTPException):
            try:
                msg = await lobby.queue_channel.send(embed=embed)
                await models.Lobby.update_lobby(lobby.id, {'last_message': msg.id})
            except (AttributeError, discord.NotFound, discord.HTTPException):
                pass

    async def check_ready(self, message, users, guild):
        """"""
        menu = ReadyMessage(message, self.bot, users, guild)
        ready_users = await menu.ready_up()
        return ready_users

    @commands.Cog.listener()
    async def on_voice_state_update(self, user, before, after):
        """"""
        if before.channel == after.channel:
            return

        if before.channel is not None:
            before_lobby = await models.Lobby.get_lobby_by_voice_channel(self.bot, before.channel.id)
            if before_lobby and not self.locked_lobby[before_lobby.id]:
                removed = await models.Lobby.delete_queued_user(before_lobby.id, user.id)

                if user.id in removed:
                    title = utils.trans(
                        'lobby-user-removed', user.display_name)
                else:
                    title = utils.trans(
                        'lobby-user-not-in-lobby', user.display_name)

                await self.update_last_msg(before_lobby, title)

        if after.channel is not None:
            after_lobby = await models.Lobby.get_lobby_by_voice_channel(self.bot, after.channel.id)
            if after_lobby and not self.locked_lobby[after_lobby.id]:
                awaitables = [
                    models.User.is_linked(user.id),
                    models.User.is_inmatch(user.id),
                    models.Lobby.get_queued_users(after_lobby.id),
                ]
                results = await asyncio.gather(*awaitables, loop=self.bot.loop)
                is_linked = results[0]
                in_match = results[1]
                queued_ids = results[2]

                if not is_linked:
                    title = utils.trans(
                        'lobby-user-not-linked', user.display_name)
                elif in_match:
                    title = utils.trans(
                        'lobby-user-in-match', user.display_name)
                elif user.id in queued_ids:
                    title = utils.trans(
                        'lobby-user-in-lobby', user.display_name)
                elif len(queued_ids) >= after_lobby.capacity:
                    title = utils.trans('lobby-is-full', user.display_name)
                else:
                    await models.Lobby.insert_queued_user(after_lobby.id, user.id)
                    queued_ids += [user.id]
                    title = utils.trans('lobby-user-added', user.display_name)

                    if len(queued_ids) == after_lobby.capacity:
                        self.locked_lobby[after_lobby.id] = True

                        guild_mdl = await models.Guild.get_guild(self.bot, after.channel.guild.id)

                        linked_role = guild_mdl.linked_role
                        prematch_channel = guild_mdl.prematch_channel
                        queue_channel = after_lobby.queue_channel
                        queued_users = [user.guild.get_member(
                            user_id) for user_id in queued_ids]

                        await after.channel.set_permissions(linked_role, connect=False)

                        try:
                            queue_msg = await after_lobby.last_message.fetch()
                            await queue_msg.delete()
                        except (AttributeError, discord.NotFound, discord.HTTPException):
                            pass

                        ready_msg = await queue_channel.send(''.join([user.mention for user in queued_users]))
                        ready_users = await self.check_ready(ready_msg, queued_users, guild_mdl)
                        await asyncio.sleep(1)
                        unreadied = set(queued_users) - ready_users

                        if unreadied:
                            description = ''.join(
                                f':x: {user.mention}\n' for user in unreadied)
                            title = utils.trans('lobby-not-all-ready')
                            burst_embed = self.bot.embed_template(
                                title=title, description=description)
                            burst_embed.set_footer(
                                text=utils.trans('lobby-unready-footer'))
                            unreadied_ids = [user.id for user in unreadied]

                            awaitables = [
                                ready_msg.clear_reactions(),
                                ready_msg.edit(content='', embed=burst_embed),
                                models.Lobby.delete_queued_users(
                                    after_lobby.id, unreadied_ids)
                            ]

                            for user in queued_users:
                                awaitables.append(user.add_roles(linked_role))
                            for user in unreadied:
                                awaitables.append(
                                    user.move_to(prematch_channel))
                            await asyncio.gather(*awaitables, loop=self.bot.loop, return_exceptions=True)
                        else:
                            await ready_msg.clear_reactions()
                            match_cog = self.bot.get_cog('Match Category')
                            new_match = await match_cog.start_match(
                                queued_users,
                                ready_msg,
                                after_lobby,
                                guild_mdl
                            )

                            if not new_match:
                                awaitables = []
                                for user in queued_users:
                                    awaitables.append(
                                        user.add_roles(linked_role))
                                for user in queued_users:
                                    awaitables.append(
                                        user.move_to(prematch_channel))
                                await asyncio.gather(*awaitables, loop=self.bot.loop, return_exceptions=True)

                            await models.Lobby.clear_queued_users(after_lobby.id)

                        title = utils.trans('lobby-players-in-lobby')
                        await self.update_last_msg(after_lobby, title)

                        self.locked_lobby[after_lobby.id] = False
                        try:
                            await after_lobby.lobby_channel.set_permissions(linked_role, connect=True)
                        except discord.NotFound:
                            pass
                        return

                await self.update_last_msg(after_lobby, title)
