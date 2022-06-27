import discord
import asyncio
from random import shuffle

from .. import utils
from .. import api


class TeamDraftMessage(discord.Message):
    """"""

    def __init__(self, message, bot, users, lobby):
        """"""
        for attr_name in message.__slots__:
            try:
                attr_val = getattr(message, attr_name)
            except AttributeError:
                continue

            setattr(self, attr_name, attr_val)

        self.bot = bot
        self.users = users
        self.lobby = lobby
        self.pick_emojis = dict(zip(utils.EMOJI_NUMBERS[1:], users))
        self.pick_order = '1' + '2211' * 20
        self.pick_number = None
        self.users_left = None
        self.teams = None
        self.captains_emojis = None
        self.future = None
        self.title = None

    @property
    def _active_picker(self):
        """"""
        if self.pick_number is None:
            return None

        picking_team_number = int(self.pick_order[self.pick_number])
        picking_team = self.teams[picking_team_number - 1]

        if len(picking_team) == 0:
            return None

        return picking_team[0]

    def _picker_embed(self, title):
        """"""
        embed = self.bot.embed_template(title=title)

        for team in self.teams:
            team_name = f'__{utils.trans("match-team")}__' if len(
                team) == 0 else f'__{utils.trans("match-team", team[0].display_name)}__'

            if len(team) == 0:
                team_players = utils.trans("message-team-empty")
            else:
                team_players = '\n'.join(p.display_name for p in team)

            embed.add_field(name=team_name, value=team_players)

        users_left_str = ''

        for index, (emoji, user) in enumerate(self.pick_emojis.items()):
            if not any(user in team for team in self.teams):
                users_left_str += f'{emoji}  {user.mention}\n'
            else:
                users_left_str += f':heavy_multiplication_x:  ~~{user.mention}~~\n'

        embed.insert_field_at(1, name=utils.trans(
            "message-players-left"), value=users_left_str)

        status_str = ''

        status_str += f'{utils.trans("message-capt1", self.teams[0][0].mention)}\n' if len(
            self.teams[0]) else f'{utils.trans("message-capt1")}\n '

        status_str += f'{utils.trans("message-capt2", self.teams[1][0].mention)}\n\n' if len(
            self.teams[1]) else f'{utils.trans("message-capt2")}\n\n '

        status_str += utils.trans("message-current-capt", self._active_picker.mention) \
            if self._active_picker is not None else utils.trans("message-current-capt")

        embed.add_field(name=utils.trans("message-info"), value=status_str)
        embed.set_footer(text=utils.trans('message-team-pick-footer'))
        return embed

    def _pick_player(self, picker, pickee):
        """"""
        if picker == pickee:
            return False
        elif not self.teams[0]:
            picking_team = self.teams[0]
            self.captains_emojis.append(list(self.pick_emojis.keys())[
                                        list(self.pick_emojis.values()).index(picker)])
            self.users_left.remove(picker)
            picking_team.append(picker)
        elif self.teams[1] == [] and picker == self.teams[0][0]:
            return False
        elif self.teams[1] == [] and picker in self.teams[0]:
            return False
        elif not self.teams[1]:
            picking_team = self.teams[1]
            self.captains_emojis.append(list(self.pick_emojis.keys())[
                                        list(self.pick_emojis.values()).index(picker)])
            self.users_left.remove(picker)
            picking_team.append(picker)
        elif picker == self.teams[0][0]:
            picking_team = self.teams[0]
        elif picker == self.teams[1][0]:
            picking_team = self.teams[1]
        else:
            return False

        if picker != self._active_picker:
            return False

        if len(picking_team) > len(self.users) // 2:
            return False

        self.users_left.remove(pickee)
        picking_team.append(pickee)
        self.pick_number += 1
        return True

    async def _process_pick(self, reaction, user):
        """"""
        if reaction.message.id != self.id or user == self.author:
            return

        pick = self.pick_emojis.get(str(reaction.emoji), None)

        if pick is None or pick not in self.users_left or user not in self.users:
            await self.remove_reaction(reaction, user)
            return

        if not self._pick_player(user, pick):
            await self.remove_reaction(reaction, user)
            return

        await self.clear_reaction(reaction.emoji)
        title = utils.trans('message-team-picked',
                            user.display_name, pick.display_name)

        if len(self.users) - len(self.users_left) == 2:
            await self.clear_reaction(self.captains_emojis[0])
        elif len(self.users) - len(self.users_left) == 4:
            await self.clear_reaction(self.captains_emojis[1])

        if len(self.users_left) == 1:
            fat_kid_team = self.teams[0] if len(self.teams[0]) <= len(
                self.teams[1]) else self.teams[1]
            fat_kid_team.append(self.users_left.pop(0))
            await self.edit(embed=self._picker_embed(title))
            if self.future is not None:
                try:
                    self.future.set_result(None)
                except asyncio.InvalidStateError:
                    pass
            return

        if len(self.users_left) == 0:
            await self.edit(embed=self._picker_embed(title))
            if self.future is not None:
                try:
                    self.future.set_result(None)
                except asyncio.InvalidStateError:
                    pass
            return

        await self.edit(embed=self._picker_embed(title))

    async def _message_deleted(self, message):
        """"""
        if message.id != self.id:
            return
        self.bot.remove_listener(self._process_pick, name='on_reaction_add')
        self.bot.remove_listener(
            self._message_deleted, name='on_message_delete')
        try:
            self.future.set_exception(ValueError)
        except asyncio.InvalidStateError:
            pass
        self.future.cancel()

    async def draft(self):
        """"""
        self.users_left = self.users.copy()
        self.teams = [[], []]
        self.pick_number = 0
        self.captains_emojis = []
        captain_method = self.lobby.captain_method

        if captain_method == 'rank':
            try:
                leaderboard = await api.Leaderboard.get_leaderboard(self.users_left)
                users_dict = dict(zip(leaderboard, self.users_left))
                players = list(users_dict.keys())
                players.sort(key=lambda x: x.average_rating)

                for team in self.teams:
                    player = [players.pop()]
                    captain = list(map(users_dict.get, player))
                    self.users_left.remove(captain[0])
                    team.append(captain[0])
                    captain_emoji_index = list(
                        self.pick_emojis.values()).index(captain[0])
                    self.captains_emojis.append(
                        list(self.pick_emojis.keys())[captain_emoji_index])
            except Exception as e:
                print(e)
                captain_method = 'random'

        if captain_method == 'random':
            temp_users = self.users_left.copy()
            shuffle(temp_users)

            for team in self.teams:
                captain = temp_users.pop()
                self.users_left.remove(captain)
                team.append(captain)
                captain_emoji_index = list(
                    self.pick_emojis.values()).index(captain)
                self.captains_emojis.append(
                    list(self.pick_emojis.keys())[captain_emoji_index])

        await self.edit(embed=self._picker_embed(utils.trans('message-team-draft-begun')))

        if self.users_left:
            for emoji, user in self.pick_emojis.items():
                if user in self.users_left:
                    await self.add_reaction(emoji)

            self.future = self.bot.loop.create_future()
            self.bot.add_listener(self._process_pick, name='on_reaction_add')
            self.bot.add_listener(self._message_deleted,
                                  name='on_message_delete')
            try:
                await asyncio.wait_for(self.future, 180)
            except asyncio.TimeoutError:
                self.bot.remove_listener(
                    self._process_pick, name='on_reaction_add')
                self.bot.remove_listener(
                    self._message_deleted, name='on_message_delete')
                await self.clear_reactions()
                raise

        await self.clear_reactions()
        return self.teams
