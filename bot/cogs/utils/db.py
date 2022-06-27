# db.py

import asyncio
import asyncpg
import logging
import os

from dotenv import load_dotenv

load_dotenv()

db_connect_url = 'postgresql://{POSTGRESQL_USER}:{POSTGRESQL_PASSWORD}@{POSTGRESQL_HOST}/{POSTGRESQL_DB}'
db_connect_url = db_connect_url.format(**os.environ)


class DB:
    """"""
    loop = asyncio.get_event_loop()
    logger = logging.getLogger('G5.db')
    logger.info('Creating database connection pool')
    pool = loop.run_until_complete(asyncpg.create_pool(db_connect_url))

    @classmethod
    async def close(cls):
        """"""
        cls.logger.info('Closing database connection pool')
        await cls.pool.close()

    @staticmethod
    def _get_record_attrs(records, key):
        """"""
        if not records:
            return []
        return list(map(lambda r: r[key], records))

    @classmethod
    async def query(cls, statement, ret_key=None):
        """"""
        async with cls.pool.acquire() as connection:
            async with connection.transaction():
                rows = await connection.fetch(statement)

        if ret_key:
            return cls._get_record_attrs(rows, ret_key) if rows else []

    @classmethod
    async def fetch_row(cls, statement):
        """"""
        async with cls.pool.acquire() as connection:
            async with connection.transaction():
                row = await connection.fetchrow(statement)

        return {col: val for col, val in row.items()} if row else {}

    @classmethod
    async def sync_guilds(cls, *guild_ids):
        """"""
        insert_rows = [tuple([guild_id] + [None] * 4)
                       for guild_id in guild_ids]

        insert_statement = (
            'INSERT INTO guilds (id)\n'
            '    (SELECT id FROM unnest($1::guilds[]))\n'
            '    ON CONFLICT (id) DO NOTHING\n'
            '    RETURNING id;'
        )
        delete_statement = (
            'DELETE FROM guilds\n'
            '    WHERE id::BIGINT != ALL($1::BIGINT[])\n'
            '    RETURNING id;'
        )

        async with cls.pool.acquire() as connection:
            async with connection.transaction():
                inserted = await connection.fetch(insert_statement, insert_rows)
                deleted = await connection.fetch(delete_statement, guild_ids)

        return cls._get_record_attrs(inserted, 'id'), cls._get_record_attrs(deleted, 'id')

    @classmethod
    async def get_users(cls, *user_ids):
        """"""
        statement = (
            'SELECT * FROM users\n'
            '    WHERE discord_id = ANY($1::BIGINT[]);'
        )

        async with cls.pool.acquire() as connection:
            async with connection.transaction():
                users = await connection.fetch(statement, user_ids)

        return [{col: val for col, val in user.items()} for user in users]

    @classmethod
    async def insert_match_users(cls, match_id, *user_ids):
        """"""
        statement = (
            'INSERT INTO match_users (match_id, user_id)\n'
            '    VALUES($1, $2);'
        )

        insert_rows = [(match_id, user_id) for user_id in user_ids]

        async with cls.pool.acquire() as connection:
            async with connection.transaction():
                await connection.executemany(statement, insert_rows)
