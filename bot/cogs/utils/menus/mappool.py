import discord
import asyncio

from .... import models
from .. import utils


class MapPoolMessage(discord.Message):
    """"""

    def __init__(self, message, bot, user, lobby):
        """"""
        for attr_name in message.__slots__:
            try:
                attr_val = getattr(message, attr_name)
            except AttributeError:
                continue

            setattr(self, attr_name, attr_val)

        self.bot = bot
        self.user = user
        self.lobby = lobby
        self.map_pool = None
        self.active_maps = None
        self.inactive_maps = None
        self.future = None

    def _pick_embed(self):
        embed = self.bot.embed_template(title=utils.trans('message-map-pool'))

        active_maps = ''.join(
            f'{emoji}  `{m.name}`\n' for emoji, m in self.active_maps.items())
        inactive_maps = ''.join(
            f'{emoji}  `{m.name}`\n' for emoji, m in self.inactive_maps.items())

        if not inactive_maps:
            inactive_maps = utils.trans("message-none")

        if not active_maps:
            active_maps = utils.trans("message-none")

        embed.add_field(name=utils.trans(
            "message-active-maps"), value=active_maps)
        embed.add_field(name=utils.trans(
            "message-inactive-maps"), value=inactive_maps)
        embed.set_footer(text=utils.trans('message-map-pool-footer'))
        return embed

    async def _process_pick(self, reaction, user):
        """"""
        if reaction.message.id != self.id or user == self.author or user != self.user:
            return

        await self.remove_reaction(reaction, user)
        emoji = str(reaction.emoji)

        if emoji == '✅':
            if len(self.active_maps) != 7:
                pass
            else:
                await self.edit(embed=self._pick_embed())
                if self.future is not None:
                    try:
                        self.future.set_result(None)
                    except asyncio.InvalidStateError:
                        pass
                return

        if emoji in self.inactive_maps:
            self.active_maps[emoji] = self.inactive_maps[emoji]
            self.inactive_maps.pop(emoji)
            self.map_pool.append(self.active_maps[emoji].dev_name)
        elif emoji in self.active_maps:
            self.inactive_maps[emoji] = self.active_maps[emoji]
            self.active_maps.pop(emoji)
            self.map_pool.remove(self.inactive_maps[emoji].dev_name)

        await self.edit(embed=self._pick_embed())

    async def edit_map_pool(self):
        """"""
        self.map_pool = [m.dev_name for m in self.lobby.mpool]
        self.active_maps = {
            m.emoji: m for m in self.bot.all_maps.values() if m.dev_name in self.map_pool}
        self.inactive_maps = {m.emoji: m for m in self.bot.all_maps.values(
        ) if m.dev_name not in self.map_pool}

        await self.edit(embed=self._pick_embed())

        awaitables = [self.add_reaction(m.emoji)
                      for m in self.bot.all_maps.values()]
        await asyncio.gather(*awaitables, loop=self.bot.loop)
        await self.add_reaction('✅')

        self.future = self.bot.loop.create_future()
        self.bot.add_listener(self._process_pick, name='on_reaction_add')

        try:
            await asyncio.wait_for(self.future, 300)
        except asyncio.TimeoutError:
            self.bot.remove_listener(
                self._process_pick, name='on_reaction_add')
            return
        self.bot.remove_listener(self._process_pick, name='on_reaction_add')

        dict_mappool = {
            m.dev_name: m.dev_name in self.map_pool for m in self.bot.all_maps.values()}
        await models.Lobby.update_lobby(self.lobby.id, dict_mappool)

        embed = self.bot.embed_template(title=utils.trans(
            'lobby-map-pool-updated', self.lobby.name))
        await self.edit(embed=embed)
        await self.clear_reactions()
