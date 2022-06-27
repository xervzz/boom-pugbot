# match.py

from discord.ext import commands, tasks
import discord

from .utils import utils, api
from .. import models
from ..resources import Config
from .utils.menus import TeamDraftMessage, MapVetoMessage

from random import shuffle
from datetime import datetime
import traceback
import asyncio


class MatchCog(commands.Cog, name='Match Category', description=utils.trans('match-desc')):
    """"""

    def __init__(self, bot):
        """"""
        self.bot = bot

    @commands.command(usage='end <match_id>',
                      brief=utils.trans('command-end-brief'),
                      aliases=['cancel', 'stop'])
    @commands.has_permissions(kick_members=True)
    @models.Guild.is_guild_setup()
    async def end(self, ctx, match_id=None):
        """"""
        try:
            match_id = int(match_id)
        except (TypeError, ValueError):
            msg = utils.trans(
                'invalid-usage', self.bot.command_prefix[0], ctx.command.usage)
            raise commands.UserInputError(message=msg)

        guild_mdl = await models.Guild.get_guild(self.bot, ctx.guild.id)

        try:
            await api.Matches.cancel_match(match_id, guild_mdl.auth)
        except Exception as e:
            raise commands.UserInputError(message=str(e))

        try:
            await self.update_match(match_id)
        except Exception as e:
            traceback.print_exception(type(e), e, e.__traceback__)
            self.bot.logger.error(
                f'caught error when calling update_match({match_id}): {e}')

        title = utils.trans('command-end-success', match_id)
        embed = self.bot.embed_template(title=title)
        await ctx.message.reply(embed=embed)

    @commands.command(usage='add <match_id> <team1|team2|spec> <mention>',
                      brief=utils.trans('command-add-brief'))
    @commands.has_permissions(kick_members=True)
    @models.Guild.is_guild_setup()
    async def add(self, ctx, match_id=None, team=None):
        """"""
        if team not in ['team1', 'team2', 'spec']:
            msg = utils.trans(
                'invalid-usage', self.bot.command_prefix[0], ctx.command.usage)
            raise commands.UserInputError(message=msg)

        try:
            match_id = int(match_id)
            user = ctx.message.mentions[0]
        except (TypeError, ValueError, IndexError):
            msg = utils.trans(
                'invalid-usage', self.bot.command_prefix[0], ctx.command.usage)
            raise commands.UserInputError(message=msg)

        user_mdl = await models.User.get_user(user.id, ctx.guild)
        if not user_mdl:
            msg = utils.trans('command-add-not-linked', user.mention)
            raise commands.UserInputError(message=msg)

        guild_mdl = await models.Guild.get_guild(self.bot, ctx.guild.id)

        try:
            await api.Matches.add_match_player(user_mdl, match_id, team, guild_mdl.auth)
        except Exception as e:
            raise commands.UserInputError(message=str(e))

        await models.Match.insert_match_user(match_id, user.id)
        match_mdl = await models.Match.get_match(self.bot, match_id)

        await user.remove_roles(guild_mdl.linked_role)

        if team == 'team1':
            await match_mdl.team1_channel.set_permissions(user, connect=True)
            try:
                await user.move_to(match_mdl.team1_channel)
            except Exception:
                pass
        elif team == 'team2':
            await match_mdl.team2_channel.set_permissions(user, connect=True)
            try:
                await user.move_to(match_mdl.team2_channel)
            except Exception:
                pass

        msg = utils.trans('command-add-success', user.mention, match_id)
        embed = self.bot.embed_template(description=msg)
        await ctx.message.reply(embed=embed)

    @commands.command(usage='remove <match_id> <mention>',
                      brief=utils.trans('command-remove-brief'))
    @commands.has_permissions(kick_members=True)
    @models.Guild.is_guild_setup()
    async def remove(self, ctx, match_id=None):
        """"""
        try:
            match_id = int(match_id)
            user = ctx.message.mentions[0]
        except (TypeError, ValueError, IndexError):
            msg = utils.trans(
                'invalid-usage', self.bot.command_prefix[0], ctx.command.usage)
            raise commands.UserInputError(message=msg)

        user_mdl = await models.User.get_user(user.id, ctx.guild)
        if not user_mdl:
            msg = utils.trans('command-add-not-linked', user.mention)
            raise commands.UserInputError(message=msg)

        guild_mdl = await models.Guild.get_guild(self.bot, ctx.guild.id)

        try:
            await api.Matches.remove_match_player(user_mdl, match_id, guild_mdl.auth)
        except Exception as e:
            raise commands.UserInputError(message=str(e))

        await models.Match.delete_match_user(match_id, user.id)
        match_mdl = await models.Match.get_match(self.bot, match_id)

        await user.add_roles(guild_mdl.linked_role)
        await match_mdl.team1_channel.set_permissions(user, connect=False)
        await match_mdl.team2_channel.set_permissions(user, connect=False)
        try:
            await user.move_to(guild_mdl.prematch_channel)
        except Exception:
            pass

        msg = utils.trans('command-remove-success', user.mention, match_id)
        embed = self.bot.embed_template(description=msg)
        await ctx.message.reply(embed=embed)

    @commands.command(usage='pause <match_id>',
                      brief=utils.trans('command-pause-brief'))
    @commands.has_permissions(kick_members=True)
    @models.Guild.is_guild_setup()
    async def pause(self, ctx, match_id=None):
        """"""
        if not match_id:
            msg = utils.trans(
                'invalid-usage', self.bot.command_prefix[0], ctx.command.usage)
            raise commands.UserInputError(message=msg)

        guild_mdl = await models.Guild.get_guild(self.bot, ctx.guild.id)

        try:
            await api.Matches.pause_match(match_id, guild_mdl.auth)
        except Exception as e:
            raise commands.UserInputError(message=str(e))

        msg = utils.trans('command-pause-success', match_id)
        embed = self.bot.embed_template(description=msg)
        await ctx.message.reply(embed=embed)

    @commands.command(usage='unpause <match_id>',
                      brief=utils.trans('command-unpause-brief'))
    @commands.has_permissions(kick_members=True)
    @models.Guild.is_guild_setup()
    async def unpause(self, ctx, match_id=None):
        """"""
        if not match_id:
            msg = utils.trans(
                'invalid-usage', self.bot.command_prefix[0], ctx.command.usage)
            raise commands.UserInputError(message=msg)

        guild_mdl = await models.Guild.get_guild(self.bot, ctx.guild.id)

        try:
            await api.Matches.unpause_match(match_id, guild_mdl.auth)
        except Exception as e:
            raise commands.UserInputError(message=str(e))

        msg = utils.trans('command-unpause-success', match_id)
        embed = self.bot.embed_template(description=msg)
        await ctx.message.reply(embed=embed)

    async def autobalance_teams(self, users):
        """ Balance teams based on players' avarage raitng. """
        # Get players and sort by average rating
        try:
            leaderboard = await api.Leaderboard.get_leaderboard(users, new_players=True)
        except Exception as e:
            print(str(e))
            return self.randomize_teams(users)

        stats_dict = dict(zip(leaderboard, users))
        players = list(stats_dict.keys())
        players.sort(key=lambda x: x.average_rating)

        # Balance teams
        team_size = len(players) // 2
        team_one = [players.pop()]
        team_two = [players.pop()]

        while players:
            if len(team_one) >= team_size:
                team_two.append(players.pop())
            elif len(team_two) >= team_size:
                team_one.append(players.pop())
            elif sum(float(p.average_rating) for p in team_one) < sum(float(p.average_rating) for p in team_two):
                team_one.append(players.pop())
            else:
                team_two.append(players.pop())

        return list(map(stats_dict.get, team_one)), list(map(stats_dict.get, team_two))

    async def draft_teams(self, message, users, lobby):
        """"""
        menu = TeamDraftMessage(message, self.bot, users, lobby)
        teams = await menu.draft()
        return teams[0], teams[1]

    @staticmethod
    def randomize_teams(users):
        """"""
        temp_users = users.copy()
        shuffle(temp_users)
        team_size = len(temp_users) // 2
        return temp_users[:team_size], temp_users[team_size:]

    async def ban_maps(self, message, lobby, captain_1, captain_2):
        """"""
        menu = MapVetoMessage(message, self.bot, lobby)
        return await menu.veto(captain_1, captain_2)

    async def update_setup_msg(self, message, desc):
        """"""
        title = utils.trans('match-setup-process')
        embed = self.bot.embed_template(title=title, description=desc)
        try:
            await message.edit(embed=embed)
        except discord.NotFound:
            pass
        await asyncio.sleep(2)

    async def start_match(self, users, message, lobby, guild_mdl):
        """"""
        
        description = ''
        try:
            if lobby.team_method == 'captains' and len(users) > 3:
                team_one, team_two = await self.draft_teams(message, users, lobby)
            elif lobby.team_method == 'autobalance' and len(users) > 3:
                team_one, team_two = await self.autobalance_teams(users)
            else:  # team_method is random
                team_one, team_two = self.randomize_teams(users)

            team1_name = team_one[0].display_name
            team2_name = team_two[0].display_name

            description = '⌛️ 1. ' + utils.trans('creating-teams')
            await self.update_setup_msg(message, description)
            team1_id = await api.Teams.create_team(team1_name, team_one, guild_mdl.auth)
            team2_id = await api.Teams.create_team(team2_name, team_two, guild_mdl.auth)
            
            description = description.replace('⌛️', '✅')
            description += '\n⌛️ 2. ' + utils.trans('pick-maps')
            await self.update_setup_msg(message, description)

            veto_menu = MapVetoMessage(message, self.bot, lobby)
            maps_list = await veto_menu.veto(team_one[0], team_two[0])

            description = description.replace('⌛️', '✅')
            description += '\n⌛️ 3. ' + utils.trans('find-servers')
            await self.update_setup_msg(message, description)

            api_servers = await api.Servers.get_servers(guild_mdl.auth)
            match_server = None
            for server in api_servers:
                if server.in_use:
                    continue
                if lobby.region and server.flag != lobby.region:
                    continue
                try:
                    server_up = await api.Servers.is_server_available(server.id, guild_mdl.auth)
                except Exception as e:
                    print(e)
                    continue
                if server_up:
                    match_server = server
                    break

            if not match_server:
                await api.Teams.delete_team(team1_id, guild_mdl.auth)
                await api.Teams.delete_team(team2_id, guild_mdl.auth)
                description = description.replace('⌛️', '❌')
                await self.update_setup_msg(message, description)
                return False

            server_id = match_server.id

            description = description.replace('⌛️', '✅')
            description += '\n⌛️ 4. ' + utils.trans('creating-match')
            await self.update_setup_msg(message, description)

            str_maps = ' '.join(m.dev_name for m in maps_list)

            match_id = await api.Matches.create_match(
                server_id,
                team1_id,
                team2_id,
                str_maps,
                len(team_one + team_two),
                guild_mdl.auth
            )

            description = description.replace('⌛️', '✅')
            await self.update_setup_msg(message, description)

        except asyncio.TimeoutError:
            description = utils.trans('match-took-too-long')
        except (discord.NotFound, ValueError):
            description = utils.trans('match-setup-cancelled')
        except Exception as e:
            self.bot.logger.error(
                f'caught error when calling start_match(): {e}')
            description = description.replace('⌛️', '❌')
            description += f'\n\n```{e}```'
        else:
            guild = lobby.guild
            match_catg = await guild.create_category_channel(utils.trans("match-id", match_id))

            team1_channel = await guild.create_voice_channel(
                name=utils.trans("match-team", team1_name),
                category=match_catg,
                user_limit=len(team_one)
            )

            team2_channel = await guild.create_voice_channel(
                name=utils.trans("match-team", team2_name),
                category=match_catg,
                user_limit=len(team_two)
            )

            dict_match = {
                'id': match_id,
                'guild': guild.id,
                'channel': lobby.queue_channel.id,
                'message': message.id,
                'category': match_catg.id,
                'team1_channel': team1_channel.id,
                'team2_channel': team2_channel.id
            }

            awaitables = [
                models.Match.insert_match(
                    dict_match, [user.id for user in team_one + team_two]),
                team1_channel.set_permissions(guild.self_role, connect=True),
                team2_channel.set_permissions(guild.self_role, connect=True),
                team1_channel.set_permissions(
                    guild.default_role, connect=False, read_messages=True),
                team2_channel.set_permissions(
                    guild.default_role, connect=False, read_messages=True)
            ]

            for team in [team_one, team_two]:
                for user in team:
                    if user in team_one:
                        awaitables.append(
                            team1_channel.set_permissions(user, connect=True))
                        awaitables.append(user.move_to(team1_channel))
                    else:
                        awaitables.append(
                            team2_channel.set_permissions(user, connect=True))
                        awaitables.append(user.move_to(team2_channel))

            await asyncio.gather(*awaitables, loop=self.bot.loop, return_exceptions=True)

            connect_url = f'steam://connect/{match_server.ip_string}:{match_server.port}'
            connect_command = f'connect {match_server.ip_string}:{match_server.port}'
            title = f"🟢 {utils.trans('match-id', match_id)} --> **{team_one[0].display_name}**  vs  **{team_two[0].display_name}**"
            description = f'{utils.trans("match-server-info", connect_url, connect_command)}\n\n' \
                f'GOTV: steam://connect/{match_server.ip_string}:{match_server.gotv_port}\n\n'
            description += f"{utils.trans('message-maps')}: {''.join(m.emoji for m in maps_list)}"

            burst_embed = self.bot.embed_template(
                title=title, description=description)
            for team in [team_one, team_two]:
                team_name = f'__{team[0].display_name}__'
                burst_embed.add_field(name=team_name, value='\n'.join(
                    user.mention for user in team))

            burst_embed.set_footer(text=utils.trans('match-info-footer'))

            try:
                await message.edit(embed=burst_embed)
            except discord.NotFound:
                try:
                    await lobby.queue_channel.send(embed=burst_embed)
                except Exception as e:
                    print(e)

            if not self.check_matches.is_running():
                self.check_matches.start()

            return True

        title = 'Match setup failed'
        await message.edit(title=title, description=description)
        return False

    @tasks.loop(seconds=20.0)
    async def check_matches(self):
        match_ids = await models.Match.get_live_matches_ids()

        if match_ids:
            for match_id in match_ids:
                try:
                    await self.update_match(match_id)
                except Exception as e:
                    traceback.print_exception(type(e), e, e.__traceback__)
                    self.bot.logger.error(
                        f'caught error when calling update_match({match_id}): {e}')
        else:
            self.check_matches.cancel()

    async def update_match(self, match_id):
        """"""
        api_mapstats = []
        api_scoreboard = []
        description = ''

        try:
            api_match = await api.Matches.get_match(match_id)
        except Exception as e:
            print(e)
            return

        if not api_match.end_time:
            return

        try:
            api_mapstats = await api.MapStats.get_mapstats(api_match.id)
        except Exception as e:
            print(e)

        try:
            api_scoreboard = await api.Scoreboard.get_match_scoreboard(api_match.id)
        except Exception as e:
            print(e)

        if api_match.cancelled:
            title = '🟥  '
        else:
            title = '🔴  '
        title += utils.trans('match-id', match_id) + \
            f' --> **{api_match.team1_name}**  [{api_match.team1_score}:{api_match.team2_score}]  **{api_match.team2_name}**'

        for mapstat in api_mapstats:
            start_time = datetime.fromisoformat(mapstat.start_time.replace(
                "Z", "+00:00")).strftime("%Y-%m-%d  %H:%M:%S")
            team1_match = []
            team2_match = []

            for player_stat in api_scoreboard:
                if player_stat.map_id != mapstat.id:
                    continue
                if player_stat.team_id == api_match.team1_id:
                    team1_match.append(player_stat)
                elif player_stat.team_id == api_match.team2_id:
                    team2_match.append(player_stat)

            description += f"**{utils.trans('map')} {mapstat.map_number+1}:** {mapstat.map_name}\n" \
                           f"**{utils.trans('score')}:** {api_match.team1_name}  [{mapstat.team1_score}:{mapstat.team2_score}]  {api_match.team2_name}\n" \
                           f"**{utils.trans('start-time')}:** {start_time}\n"

            if mapstat.end_time:
                end_time = datetime.fromisoformat(mapstat.end_time.replace(
                    "Z", "+00:00")).strftime("%Y-%m-%d  %H:%M:%S")
                description += f"**{utils.trans('end-time')}:** {end_time}\n"

            if team1_match and team2_match:
                for team in [team1_match, team2_match]:
                    team.sort(key=lambda x: x.score, reverse=True)
                    data = [['Player'] + [player.name for player in team],
                            ['Kills'] + [f"{player.kills}" for player in team],
                            ['Assists'] + [f"{player.assists}" for player in team],
                            ['Deaths'] + [f"{player.deaths}" for player in team],
                            ['KDR'] + [f"{0 if player.deaths == 0 else player.kills/player.deaths:.2f}" for player in team]]

                    # Shorten long names
                    data[0] = [name if len(
                        name) < 12 else name[:9] + '...' for name in data[0]]
                    widths = list(map(lambda x: len(max(x, key=len)), data))
                    aligns = ['left', 'center', 'center', 'center', 'right']
                    z = zip(data, widths, aligns)
                    formatted_data = [list(map(lambda x: utils.align_text(
                        x, width, align), col)) for col, width, align in z]
                    # Transpose list for .format() string
                    formatted_data = list(map(list, zip(*formatted_data)))
                    description += '```ml\n    {}  {}  {}  {}  {}  \n'.format(
                        *formatted_data[0])

                    for rank, player_row in enumerate(formatted_data[1:], start=1):
                        description += ' {}. {}  {}  {}  {}  {}  \n'.format(
                            rank, *player_row)

                    description += '```\n'
            description += '\n'
        description += f"[{utils.trans('more-info')}]({Config.web_panel}/match/{match_id})"

        embed = self.bot.embed_template(title=title, description=description)

        match_mdl = await models.Match.get_match(self.bot, match_id)
        guild_mdl = await models.Guild.get_guild(self.bot, match_mdl.guild.id)

        try:
            message = await match_mdl.message.fetch()
            await message.edit(embed=embed)
        except Exception:
            try:
                await match_mdl.channel.send(embed=embed)
            except Exception as e:
                print(e)
                pass

        guild = guild_mdl.guild

        match_player_ids = await models.Match.get_match_users(match_id)
        match_players = [guild.get_member(user_id)
                         for user_id in match_player_ids]

        awaitables = []
        for user in match_players:
            if user is not None:
                awaitables.append(user.move_to(guild_mdl.prematch_channel))
                awaitables.append(user.add_roles(guild_mdl.linked_role))

        await asyncio.gather(*awaitables, loop=self.bot.loop, return_exceptions=True)

        for channel in [match_mdl.team1_channel, match_mdl.team2_channel, match_mdl.category]:
            try:
                await channel.delete()
            except (AttributeError, discord.NotFound):
                pass

        await models.Match.delete_match(match_mdl.id)
