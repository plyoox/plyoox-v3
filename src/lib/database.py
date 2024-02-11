import json

import asyncpg


async def _init_db_connection(conn: asyncpg.Connection):
    await conn.set_type_codec("json", encoder=json.dumps, decoder=json.loads, schema="pg_catalog")
