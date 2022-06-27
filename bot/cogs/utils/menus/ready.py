import discord
import asyncio

from .. import utils


class ReadyMessage(discord.Message):
    def __init__(self, message, bot, users, guild):
        """"""
        for attr_name in message.__slots__:
            try:
                attr_val = getattr(message, attr_name)
            except AttributeError:
                continue

            setattr(self, attr_name, attr_val)

        self.bot = bot
        self.users = users
        self.guild = guild
        self.reactors = None
        self.future = None

    def _ready_embed(self):
        """"""
        str_value = ''
        description = utils.trans('message-react-ready', '✅')
        embed = self.bot.embed_template(title=utils.trans(
            'message-lobby-filled-up'), description=description)

        for num, user in enumerate(self.users, start=1):
            if user not in self.reactors:
                str_value += f':heavy_multiplication_x:  {num}. {user.mention}\n '
            else:
                str_value += f'✅  {num}. {user.mention}\n '

        embed.add_field(name=f":hourglass: __{utils.trans('players')}__",
                        value='-------------------\n' + str_value)
        return embed

    async def _process_ready(self, reaction, user):
        """"""
        if reaction.message.id != self.id or user == self.author:
            return

        if user not in self.users or reaction.emoji != '✅':
            await self.remove_reaction(reaction, user)
            return

        self.reactors.add(user)
        await self.edit(embed=self._ready_embed())

        if self.reactors.issuperset(self.users):
            if self.future is not None:
                try:
                    self.future.set_result(None)
                except asyncio.InvalidStateError:
                    pass

    async def ready_up(self):
        """"""
        self.reactors = set()
        self.future = self.bot.loop.create_future()
        await self.edit(embed=self._ready_embed())
        await self.add_reaction('✅')

        self.bot.add_listener(self._process_ready, name='on_reaction_add')

        awaitables = []
        for user in self.users:
            awaitables.append(user.remove_roles(self.guild.linked_role))
        await asyncio.gather(*awaitables, loop=self.bot.loop, return_exceptions=True)

        try:
            await asyncio.wait_for(self.future, 60)
        except asyncio.TimeoutError:
            pass

        self.bot.remove_listener(self._process_ready, name='on_reaction_add')

        return self.reactors
