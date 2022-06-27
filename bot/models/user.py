# user.py

from typing import List
from discord import Guild
from ..cogs.utils.db import DB


class User:
    """"""

    def __init__(self, discord, steam, flag):
        """"""
        self.discord = discord
        self.steam = steam
        self.flag = flag

    @classmethod
    def from_dict(cls, user_data: dict, guild: Guild):
        """"""
        return cls(
            guild.get_member(user_data['discord_id']),
            user_data['steam_id'],
            user_data['flag']
        )

    @staticmethod
    async def get_user(user_id: int, guild: Guild):
        """"""
        try:
            sql = "SELECT * FROM users\n" \
                  f"    WHERE discord_id = {user_id};"
            user_data = await DB.fetch_row(sql)
            if user_data:
                return User.from_dict(user_data, guild)
        except Exception:
            pass

    @staticmethod
    async def get_users(user_ids: List[int]):
        """"""
        users_data = await DB.get_users(user_ids)
        return [User.from_dict(user_data) for user_data in users_data]

    @staticmethod
    async def get_user_by_steam(steam_id: str, guild: Guild):
        """"""
        sql = "SELECT * FROM users\n" \
            f"    WHERE steam_id = '{steam_id}';"
        user_data = await DB.fetch_row(sql)
        if user_data:
            return User.from_dict(user_data, guild)

    @staticmethod
    async def insert_user(discord_id: int, steam_id: str, flag: str):
        """"""
        sql = "INSERT INTO users (discord_id, steam_id, flag)\n" \
            f"    VALUES({discord_id}, '{steam_id}', '{flag}')\n" \
            "    ON CONFLICT DO NOTHING\n" \
            "    RETURNING discord_id;"
        await DB.query(sql)

    @staticmethod
    async def delete_user(user_id: int):
        """"""
        sql = f"DELETE FROM users WHERE discord_id = {user_id};"
        await DB.query(sql)

    @staticmethod
    async def is_inmatch(user_id: int) -> bool:
        """"""
        sql = "SELECT user_id FROM match_users;"
        matches_users = await DB.query(sql, ret_key='user_id')
        return True if user_id in matches_users else False

    @staticmethod
    async def is_linked(user_id: int) -> bool:
        """"""
        sql = "SELECT discord_id FROM users;"
        linked_users = await DB.query(sql, ret_key='discord_id')
        return True if user_id in linked_users else False
