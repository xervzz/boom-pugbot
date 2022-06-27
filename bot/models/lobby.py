# lobby.py

from typing import List
from ..cogs.utils.db import DB


class Lobby:
    """"""

    def __init__(self, lobby_id, guild, name, region, capacity, series, category,
                 queue_channel, lobby_channel, last_message, team_method, captain_method, mpool):
        """"""
        self.id = lobby_id
        self.guild = guild
        self.name = name
        self.region = region
        self.capacity = capacity
        self.series = series
        self.category = category
        self.queue_channel = queue_channel
        self.lobby_channel = lobby_channel
        self.last_message = last_message
        self.team_method = team_method
        self.captain_method = captain_method
        self.mpool = mpool

    @classmethod
    def from_dict(cls, bot, lobby_data: dict):
        """"""
        guild = bot.get_guild(lobby_data['guild'])
        category = guild.get_channel(lobby_data['category'])
        queue_channel = guild.get_channel(lobby_data['queue_channel'])
        lobby_channel = guild.get_channel(lobby_data['lobby_channel'])
        try:
            last_message = queue_channel.get_partial_message(
                lobby_data['last_message'])
        except AttributeError:
            last_message = None

        return cls(
            lobby_data['id'],
            guild,
            lobby_data['name'],
            lobby_data['region'],
            lobby_data['capacity'],
            lobby_data['series_type'],
            category,
            queue_channel,
            lobby_channel,
            last_message,
            lobby_data['team_method'],
            lobby_data['captain_method'],
            [m for m in bot.all_maps.values() if lobby_data[m.dev_name]]
        )

    @staticmethod
    async def get_lobby(bot, lobby_id: int, guild_id: int):
        """"""
        try:
            sql = "SELECT * FROM lobbies\n" \
                f"    WHERE id = {lobby_id} AND guild = {guild_id};"
            lobby_data = await DB.fetch_row(sql)
            if lobby_data:
                return Lobby.from_dict(bot, lobby_data)
        except Exception:
            pass

    @staticmethod
    async def get_guild_lobbies(bot, guild_id: int):
        """"""
        sql = "SELECT id FROM lobbies\n" \
              f"    WHERE guild = {guild_id};"
        lobby_ids = await DB.query(sql, ret_key='id')
        return [await Lobby.get_lobby(bot, lobby_id, guild_id) for lobby_id in lobby_ids]

    @staticmethod
    async def get_lobby_by_voice_channel(bot, channel_id: int):
        """"""
        sql = "SELECT * FROM lobbies\n" \
            f"    WHERE lobby_channel = {channel_id};"
        lobby_data = await DB.fetch_row(sql)
        if lobby_data:
            return Lobby.from_dict(bot, lobby_data)

    @staticmethod
    async def get_lobby_by_text_channel(bot, channel_id: int):
        """"""
        sql = "SELECT * FROM lobbies\n" \
            f"    WHERE queue_channel = {channel_id};"
        lobby_data = await DB.fetch_row(sql)
        if lobby_data:
            return Lobby.from_dict(bot, lobby_data)

    @staticmethod
    async def insert_lobby(data: dict) -> List[int]:
        """"""
        cols = ", ".join(col for col in data)
        vals = ", ".join(str(val) for val in data.values())
        sql = f"INSERT INTO lobbies ({cols})\n" \
              f"    VALUES({vals})\n" \
            "RETURNING id;"
        return await DB.query(sql, ret_key='id')

    @staticmethod
    async def update_lobby(lobby_id: int, data: dict):
        """"""
        col_vals = ",\n    ".join(
            f"{key} = {val}" for key, val in data.items())
        sql = "UPDATE lobbies\n" \
              f"    SET {col_vals}\n" \
              f"    WHERE id = {lobby_id};"
        await DB.query(sql)

    @staticmethod
    async def delete_lobby(lobby_id: int):
        """"""
        sql = f"DELETE FROM lobbies WHERE id = {lobby_id};"
        await DB.query(sql)

    @staticmethod
    async def get_queued_users(lobby_id: int) -> List[int]:
        """"""
        sql = "SELECT user_id FROM queued_users\n" \
              f"    WHERE lobby_id = {lobby_id};"
        return await DB.query(sql, ret_key='user_id')

    @staticmethod
    async def insert_queued_user(lobby_id: int, user_id: int):
        """"""
        sql = "INSERT INTO queued_users (lobby_id, user_id)\n" \
              f"    VALUES({lobby_id}, {user_id});"
        await DB.query(sql)

    @staticmethod
    async def delete_queued_user(lobby_id: int, user_id: int) -> List[int]:
        """"""
        sql = "DELETE FROM queued_users\n" \
              f"    WHERE lobby_id = {lobby_id} AND user_id = {user_id}\n" \
              "    RETURNING user_id;"
        return await DB.query(sql, ret_key='user_id')

    @staticmethod
    async def delete_queued_users(lobby_id: int, user_ids: List[int]):
        """"""
        sql = "DELETE FROM queued_users\n" \
              f"    WHERE lobby_id = {lobby_id} AND user_id::BIGINT = ANY(ARRAY{user_ids}::BIGINT[]);"
        await DB.query(sql)

    @staticmethod
    async def clear_queued_users(lobby_id: int):
        """"""
        sql = f"DELETE FROM queued_users WHERE lobby_id = {lobby_id};"
        await DB.query(sql)
