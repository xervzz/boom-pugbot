# match.py

from typing import List
from ..cogs.utils.db import DB


class Match:
    """"""

    def __init__(self, match_id, guild, channel, message, category, team1_channel, team2_channel):
        """"""
        self.id = match_id
        self.guild = guild
        self.channel = channel
        self.message = message
        self.category = category
        self.team1_channel = team1_channel
        self.team2_channel = team2_channel

    @classmethod
    def from_dict(cls, bot, match_data: dict):
        """"""
        guild = bot.get_guild(match_data['guild'])
        channel = guild.get_channel(match_data['channel'])

        try:
            message = channel.get_partial_message(match_data['message'])
        except AttributeError:
            message = None

        return cls(
            match_data['id'],
            guild,
            channel,
            message,
            guild.get_channel(match_data['category']),
            guild.get_channel(match_data['team1_channel']),
            guild.get_channel(match_data['team2_channel'])
        )

    @staticmethod
    async def get_match(bot, match_id: int):
        """"""
        try:
            sql = "SELECT * FROM matches\n" \
                f"    WHERE id = {match_id};"
            match_data = await DB.fetch_row(sql)
            if match_data:
                return Match.from_dict(bot, match_data)
        except Exception:
            pass

    @staticmethod
    async def insert_match(data: dict, user_ids: list):
        """"""
        cols = ", ".join(col for col in data)
        vals = ", ".join(str(val) for val in data.values())
        sql = f"INSERT INTO matches ({cols})\n" \
              f"    VALUES({vals});"
        await DB.query(sql)
        await DB.insert_match_users(data['id'], *user_ids)

    @staticmethod
    async def insert_match_user(match_id: int, user_id: int):
        """"""
        sql = "INSERT INTO match_users (match_id, user_id)\n" \
              f"    VALUES({match_id}, {user_id});"
        await DB.query(sql)

    @staticmethod
    async def delete_match_user(match_id: int, user_id: int):
        """"""
        sql = "DELETE FROM match_users\n" \
              f"    WHERE match_id = {match_id} AND user_id = {user_id};"
        await DB.query(sql)

    @staticmethod
    async def delete_match(match_id: int):
        """"""
        sql = f"DELETE FROM matches WHERE id = {match_id};"
        await DB.query(sql)

    @staticmethod
    async def get_match_users(match_id: int) -> List[int]:
        """"""
        sql = "SELECT user_id FROM match_users\n" \
              f"    WHERE match_id = {match_id};"
        return await DB.query(sql, ret_key='user_id')

    @staticmethod
    async def get_live_matches_ids() -> List[int]:
        """"""
        sql = "SELECT id FROM matches;"
        return await DB.query(sql, ret_key='id')
