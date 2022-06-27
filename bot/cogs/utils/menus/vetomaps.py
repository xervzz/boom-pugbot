import discord
import asyncio

from .. import utils


class MapVetoMessage(discord.Message):
    """"""

    def __init__(self, message, bot, lobby):
        """"""
        for attr_name in message.__slots__:
            try:
                attr_val = getattr(message, attr_name)
            except AttributeError:
                continue

            setattr(self, attr_name, attr_val)

        self.bot = bot
        self.ban_order = '121212'
        self.ban_number = 0
        self.lobby = lobby
        self.maps_left = {m.emoji: m for m in self.lobby.mpool}
        self.maps_pick = []
        self.maps_ban = []
        self.captains = None
        self.future = None

    @property
    def _active_picker(self):
        """"""
        picking_player_number = int(self.ban_order[self.ban_number])
        return self.captains[picking_player_number - 1]

    def _veto_embed(self, title, method):
        """"""
        embed = self.bot.embed_template(title=title)
        maps_str = ''

        for m in self.lobby.mpool:
            if m in self.maps_pick:
                maps_str += f'✅ {m.emoji}  {m.name}\n'
            elif m in self.maps_ban:
                maps_str += f'❌ {m.emoji}  ~~{m.name}~~\n'
            else:
                maps_str += f'❔ {m.emoji}  {m.name}\n'

        embed.add_field(name=utils.trans("message-maps-left"), value=maps_str)
        if self.ban_number < len(self.ban_order):
            status_str = ''
            status_str += utils.trans("message-capt1",
                                      self.captains[0].mention) + '\n'
            status_str += utils.trans("message-capt2",
                                      self.captains[1].mention) + '\n\n'
            status_str += utils.trans("message-current-capt",
                                      self._active_picker.mention) + '\n'
            status_str += utils.trans('message-map-method', method)
            embed.add_field(name=utils.trans("message-info"), value=status_str)

        embed.set_footer(text=utils.trans('message-map-veto-footer'))
        return embed

    async def _process_ban(self, reaction, user):
        """"""
        if reaction.message.id != self.id or user == self.author:
            return

        if user not in self.captains or str(reaction) not in [m for m in self.maps_left] or user != self._active_picker:
            await self.remove_reaction(reaction, user)
            return

        try:
            selected_map = self.maps_left.pop(str(reaction))
        except KeyError:
            return

        if self.lobby.series == 'bo3' and self.ban_number in [2, 3]:
            self.maps_pick.append(selected_map)
            title = utils.trans('message-user-picked-map',
                                user.display_name, selected_map.name)
        else:
            self.maps_ban.append(selected_map)
            title = utils.trans('message-user-banned-map',
                                user.display_name, selected_map.name)
            method = utils.trans('message-map-method-ban')

        if self.lobby.series == 'bo3':
            if self.ban_number in [1, 2]:
                method = utils.trans('message-map-method-pick')
            else:
                method = utils.trans('message-map-method-ban')

        self.ban_number += 1
        await self.clear_reaction(selected_map.emoji)
        embed = self._veto_embed(title, method)
        await self.edit(embed=embed)

        if (self.lobby.series == 'bo3' and len(self.maps_pick) == 2 and len(self.maps_ban) == 4) or \
           (self.lobby.series == 'bo2' and len(self.maps_left) == 2) or \
           (self.lobby.series == 'bo1' and len(self.maps_left) == 1):
            if self.future is not None:
                try:
                    self.future.set_result(None)
                except asyncio.InvalidStateError:
                    pass

    async def _message_deleted(self, message):
        """"""
        if message.id != self.id:
            return
        self.bot.remove_listener(self._process_ban, name='on_reaction_add')
        self.bot.remove_listener(
            self._message_deleted, name='on_message_delete')
        try:
            self.future.set_exception(ValueError)
        except asyncio.InvalidStateError:
            pass
        self.future.cancel()

    async def veto(self, captain_1, captain_2):
        """"""
        self.captains = [captain_1, captain_2]

        if len(self.lobby.mpool) % 2 == 0:
            self.captains.reverse()

        title = utils.trans('message-map-bans-begun')
        method = utils.trans('message-map-method-ban')
        await self.edit(embed=self._veto_embed(title, method))

        for m in self.lobby.mpool:
            await self.add_reaction(m.emoji)

        self.future = self.bot.loop.create_future()
        self.bot.add_listener(self._process_ban, name='on_reaction_add')
        self.bot.add_listener(self._message_deleted, name='on_message_delete')
        try:
            await asyncio.wait_for(self.future, 180)
        except asyncio.TimeoutError:
            self.bot.remove_listener(self._process_ban, name='on_reaction_add')
            self.bot.remove_listener(
                self._message_deleted, name='on_message_delete')
            await self.clear_reactions()
            raise

        await self.clear_reactions()
        return self.maps_pick + list(self.maps_left.values())
