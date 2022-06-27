# stats.py

from discord.ext import commands

from .utils import utils, api
from .. import models

from pprint import pprint
from ..resources import Config
import asyncio
from datetime import datetime
import json


class StatsCog(commands.Cog, name='Stats Category', description=utils.trans('stats-desc')):
    """"""

    def __init__(self, bot):
        self.bot = bot

    @commands.command(brief=utils.trans('command-stats-brief'),
                      aliases=['rank'])
    async def stats(self, ctx):
        """"""
        user_mdl = await models.User.get_user(ctx.author.id, ctx.guild)

        if not user_mdl:
            msg = utils.trans('stats-not-linked', ctx.author.display_name)
            raise commands.UserInputError(message=msg)

        try:
            stats = await api.PlayerStats.get_player_stats(user_mdl)
        except Exception as e:
            raise commands.UserInputError(message=str(e))

        if not stats:
            msg = utils.trans('stats-no-matches', ctx.author.display_name)
            raise commands.UserInputError(message=msg)

        description = '```ml\n' \
            f' {utils.trans("stats-kills")}:             {stats.kills} \n' \
            f' {utils.trans("stats-deaths")}:            {stats.deaths} \n' \
            f' {utils.trans("stats-assists")}:           {stats.assists} \n' \
            f' {utils.trans("stats-kdr")}:         {stats.kdr} \n' \
            f' {utils.trans("stats-hs")}:         {stats.headshot_kills} \n' \
            f' {utils.trans("stats-hsp")}:  {stats.hsp} \n' \
            f' {utils.trans("stats-played")}:    {stats.total_maps} \n' \
            f' {utils.trans("stats-wins")}:        {stats.wins} \n' \
            f' {utils.trans("stats-win-rate")}:       {stats.win_percent} \n' \
            f' {utils.trans("stats-total-damage")}:      {stats.total_damage} \n' \
            f' {utils.trans("stats-aces")}:              {stats.k5} \n' \
            f' \n -Clutch Wins - \n' \
            f' {utils.trans("stats-1v1")}:        {stats.v1} \n' \
            f' {utils.trans("stats-1v2")}:        {stats.v2} \n' \
            f' {utils.trans("stats-1v3")}:      {stats.v3} \n' \
            f' {utils.trans("stats-1v4")}:       {stats.v4} \n' \
            f' {utils.trans("stats-1v5")}:       {stats.v5} \n' \
            f' ------------------------- \n' \
            f' {utils.trans("stats-rating")}:    {stats.average_rating} \n' \
                      '```'
        embed = self.bot.embed_template(
            title=ctx.author.display_name, description=description)
        await ctx.message.reply(embed=embed)

    @commands.command(brief=utils.trans('command-leaders-brief'),
                      aliases=['top', 'ranks'])
    async def leaders(self, ctx):
        """"""
        num = 15
        minMaps = 15
        try:
            guild_players = await api.Leaderboard.get_leaderboard(ctx.guild.members)
        except Exception as e:
            raise commands.UserInputError(message=str(e))
    
    

        guild_players.sort(key=lambda u: (u.average_rating), reverse=True)
        guild_players.sort(key=lambda u: (u.total_maps) >= minMaps, reverse=True)
        guild_players = guild_players[:num]

        # Generate leaderboard text
        data = [['Player'] + [player.name for player in guild_players],
                ['Kills'] + [str(player.kills) for player in guild_players],
                ['Deaths'] + [str(player.deaths) for player in guild_players],
                ['Played'] + [str(player.total_maps) for player in guild_players],
                ['Wins'] + [str(player.wins) for player in guild_players],
                ['Rating'] + [str(player.average_rating) for player in guild_players]]
        data[0] = [name if len(name) < 12 else name[:9] + '...' for name in data[0]]  # Shorten long names
        widths = list(map(lambda x: len(max(x, key=len)), data))
        aligns = ['left', 'center', 'center', 'center', 'center', 'right']
        z = zip(data, widths, aligns)
        formatted_data = [list(map(lambda x: utils.align_text(
            x, width, align), col)) for col, width, align in z]
        # Transpose list for .format() string
        formatted_data = list(map(list, zip(*formatted_data)))

        description = '```ml\n    {}  {}  {}  {}  {}  {} \n'.format(
            *formatted_data[0])

        for rank, player_row in enumerate(formatted_data[1:], start=1):
            description += ' {}. {}  {}  {}  {}  {}  {} \n'.format(
                rank, *player_row)

        description += '```'

        # Send leaderboard
        title = f'__{utils.trans("leaderboard")}__ with at least ({minMaps}) maps played'
        embed = self.bot.embed_template(title=title, description=description)
        await ctx.message.reply(embed=embed)
           
    @commands.command(brief=utils.trans('command-match-stats'),
                      aliases=['match', 'game'])
    async def matchstats(self, ctx, arg1):
        """"""
        matchid = arg1
        
        api_mapstats = []
        api_scoreboard = []
        description = ''
        
        #if arg1 is not a number return
        try:
            val = int(arg1)
        except ValueError:
            ctx.send(f'Match ID {arg1} is not a valid match id - has to be a number')
            return
        
        try:
            api_match = await api.Matches.get_match(matchid)
        except Exception as e:
            raise commands.UserInputError(message=str(e))

        if not api_match:
            msg = utils.trans('stats-no-matches', ctx.author.display_name)
            raise commands.UserInputError(message=msg)

       # if not api_match.end_time:
            #return

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
            title = 'Fetched Old Match Data\n🟢  '
        title += utils.trans('match-id', arg1) + \
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
            else: 
                end_time = "Not Finished..."
                description += f"**{utils.trans('end-time')}:** {end_time}\n"

            if team1_match and team2_match:
                for team in [team1_match, team2_match]:
                    team.sort(key=lambda x: x.score, reverse=True)
                    data = [['Player'] + [player.name for player in team],
                            ['K/D/A'] + [f"{player.kills}/{player.deaths}/{player.assists}" for player in team],
                            ['UD'] + [f"{player.util_damage}" for player in team],
                            ['FK'] + [f"{0 if player.firstkill_ct and player.firstkill_t == 0 else player.firstkill_ct + player.firstkill_t}" for player in team],
                            ['FD'] + [f"{0 if player.firstdeath_ct and player.firstdeath_t == 0 else player.firstdeath_ct + player.firstdeath_t}" for player in team],
                            ['HS% (+)'] + [f"{0 if player.headshot_kills == 0 else player.headshot_kills / player.kills:.0%} ({player.headshot_kills})" for player in team],
                            ['ACE'] + [f"{player.k5}" for player in team],
                            ['KDR'] + [f"{0 if player.deaths == 0 else player.kills/player.deaths:.2f}" for player in team]]

                    # Shorten long names
                    data[0] = [name if len(
                        name) < 10 else name[:7] + '..' for name in data[0]]
                    widths = list(map(lambda x: len(max(x, key=len)), data))
                    aligns = ['left', 'center', 'left', 'center', 'center', 'left', 'center', 'right']
                    z = zip(data, widths, aligns)
                    formatted_data = [list(map(lambda x: utils.align_text(
                        x, width, align), col)) for col, width, align in z]
                    # Transpose list for .format() string
                    formatted_data = list(map(list, zip(*formatted_data)))
                    description += '```ml\n    {}  {}  {}  {}  {}  {}  {}  {}  \n'.format(
                        *formatted_data[0])

                    for rank, player_row in enumerate(formatted_data[1:], start=1):
                        description += ' {}. {}  {}  {}  {}  {}  {}  {}  {}  \n'.format(
                            rank, *player_row)

                    description += '```\n'
            description += '\n'
        description += f"[{utils.trans('more-info')}]({Config.web_panel}/match/{arg1})"

        embed = self.bot.embed_template(title=title, description=description)
        
        try:
            await ctx.send(embed=embed)
        except Exception:
            print(e)
            await ctx.send("There was an error...")

    @commands.command(brief=utils.trans('command-ongoing-match'),
                      aliases=['ongoing', 'current'])
    async def ongoingmatchstats(self, ctx):
        """"""
        api_allmapstats = []
        activeGameCount = 0
        string = ''
        description = ''

        try:
            api_allmapstats = await api.MapStats.get_allmapstats()
        except Exception as e:
            print(e)
        
        for mapstat in api_allmapstats:
            if hasattr(mapstat, 'end_time') == False or mapstat.end_time == None:

                try:
                    api_match = await api.Matches.get_match(mapstat.match_id)
                    TeamOne = f"{api_match.team1_name}"
                    TeamTwo = f"{api_match.team2_name}"
                except:
                    TeamOne = f"Team 1"
                    TeamTwo = f"Team 2"

                activeGameCount += 1
                string += f"{activeGameCount}. __**{TeamOne}**__ VS __**{TeamTwo}**__\n ⤷ [Score: **{mapstat.team1_score}**:**{mapstat.team2_score}**] [Map: **{mapstat.map_name}**] [Match ID: **{mapstat.match_id}**]\n"
        
        description += f"Currently there is __**{activeGameCount}**__ ongoing games\n\n{string}\nTo see stats for a specific game, use `q!match <Match ID>`"
        
        embed = self.bot.embed_template(
            title="Ongoing Games", 
            description=description
        )

        try:
            await ctx.send(embed=embed)
        except Exception:
            print(e)
            await ctx.send("There was an error...")