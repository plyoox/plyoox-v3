from __future__ import annotations

import enum
import json
from typing import TYPE_CHECKING

import sqlalchemy as sql
import sqlalchemy.dialects.postgresql as pg
import sqlalchemy.orm as orm

from lib.enums import MentionSettings

if TYPE_CHECKING:
    import asyncpg

metadata = sql.MetaData()
mapper_registry = orm.registry(metadata=metadata)
Base = mapper_registry.generate_base()


async def _init_db_connection(conn: asyncpg.Connection):
    await conn.set_type_codec("json", encoder=json.dumps, decoder=json.loads, schema="pg_catalog")


class _Column(sql.Column):
    def __init__(self, *args, **kwargs):
        has_nullable = kwargs.get("nullable") is not None
        default = kwargs.get("server_default")

        if default is not None and not has_nullable:
            kwargs.setdefault("nullable", False)

        if default is not None:
            if isinstance(default, enum.Enum):
                server_default = default.name
            elif isinstance(default, list):
                server_default = "{}"
            else:
                server_default = str(default)

            kwargs["server_default"] = server_default

        super().__init__(*args, **kwargs)


class Leveling(Base):
    __tablename__ = "leveling"

    id = _Column(pg.BIGINT, primary_key=True, autoincrement=False)
    active = _Column(pg.BOOLEAN, server_default=False)
    channel = _Column(pg.BIGINT)
    message = _Column(pg.VARCHAR(length=2000))
    roles = _Column(pg.ARRAY(sql.BIGINT))
    no_xp_channels = _Column(pg.ARRAY(sql.BIGINT))
    no_xp_role = _Column(pg.BIGINT)
    remove_roles = _Column(pg.BOOLEAN, server_default=False)


class LevelingUsers(Base):
    __tablename__ = "leveling_users"

    id = _Column(pg.INTEGER, primary_key=True)
    guild_id = _Column(pg.BIGINT, nullable=False)
    user_id = _Column(pg.BIGINT, nullable=False)
    xp = _Column(pg.INTEGER, server_default=0)

    uix_user = sql.UniqueConstraint("guild_id", "user_id")


class Welcome(Base):
    __tablename__ = "welcome"

    id = _Column(pg.BIGINT, primary_key=True, autoincrement=False)
    active = _Column(pg.BOOLEAN, server_default=False)
    join_channel = _Column(pg.BIGINT)
    join_message = _Column(pg.VARCHAR(length=2000))
    join_roles = _Column(pg.ARRAY(pg.BIGINT), server_default=[])
    join_active = _Column(pg.BOOLEAN, server_default=False)
    leave_channel = _Column(pg.BIGINT)
    leave_message = _Column(pg.VARCHAR(length=2000))
    leave_active = _Column(pg.BOOLEAN, server_default=False)


class Logging(Base):
    __tablename__ = "logging"

    id = _Column(pg.BIGINT, primary_key=True, autoincrement=False)
    active = _Column(pg.BOOLEAN, server_default=False)
    webhook_id = _Column(pg.BIGINT)
    webhook_channel = _Column(pg.BIGINT)
    webhook_token = _Column(pg.VARCHAR(length=80))
    member_join = _Column(pg.BOOLEAN, server_default=False)
    member_leave = _Column(pg.BOOLEAN, server_default=False)
    member_ban = _Column(pg.BOOLEAN, server_default=False)
    member_unban = _Column(pg.BOOLEAN, server_default=False)
    member_rename = _Column(pg.BOOLEAN, server_default=False)
    member_role_change = _Column(pg.BOOLEAN, server_default=False)
    message_edit = _Column(pg.BOOLEAN, server_default=False)
    message_delete = _Column(pg.BOOLEAN, server_default=False)


class Moderation(Base):
    __tablename__ = "moderation"

    id = _Column(pg.BIGINT, primary_key=True, autoincrement=False)
    active = _Column(pg.BOOLEAN, server_default=False)
    mod_roles = _Column(pg.ARRAY(pg.BIGINT))
    ignored_roles = _Column(pg.ARRAY(pg.BIGINT))
    log_id = _Column(pg.BIGINT)
    log_channel = _Column(pg.BIGINT)
    log_token = _Column(pg.VARCHAR(length=80))

    automod_active = _Column(pg.BOOLEAN, server_default=False)
    automod_actions = _Column(pg.JSON)
    notify_user = _Column(pg.BOOLEAN, server_default=False)

    invite_active = _Column(pg.BOOLEAN, server_default=False)
    invite_whitelist_channels = _Column(pg.ARRAY(pg.BIGINT))
    invite_whitelist_roles = _Column(pg.ARRAY(pg.BIGINT))
    invite_allowed = _Column(pg.ARRAY(pg.VARCHAR(length=10)))
    invite_actions = _Column(pg.JSON)

    link_active = _Column(pg.BOOLEAN, server_default=False)
    link_whitelist_channels = _Column(pg.ARRAY(pg.BIGINT))
    link_whitelist_roles = _Column(pg.ARRAY(pg.BIGINT))
    link_list = _Column(pg.ARRAY(pg.VARCHAR(length=30)))
    link_is_whitelist = _Column(pg.BOOLEAN, server_default=True)
    link_actions = _Column(pg.JSON)

    mention_active = _Column(pg.BOOLEAN, server_default=False)
    mention_whitelist_channels = _Column(pg.ARRAY(pg.BIGINT))
    mention_whitelist_roles = _Column(pg.ARRAY(pg.BIGINT))
    mention_settings = _Column(pg.ENUM(MentionSettings), server_default=MentionSettings.member)
    mention_count = _Column(pg.SMALLINT, server_default=5)
    mention_actions = _Column(pg.JSON)

    caps_active = _Column(pg.BOOLEAN, server_default=False)
    caps_whitelist_channels = _Column(pg.ARRAY(pg.BIGINT))
    caps_whitelist_roles = _Column(pg.ARRAY(pg.BIGINT))
    caps_actions = _Column(pg.JSON)
