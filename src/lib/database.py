import enum

import sqlalchemy as sql
import sqlalchemy.orm as orm

from lib import enums

metadata = sql.MetaData()
mapper_registry = orm.registry(metadata=metadata)
Base = mapper_registry.generate_base()


class _Column(sql.Column):
    def __init__(self, *args, **kwargs):
        has_nullable = kwargs.get("nullable") is not None
        default = kwargs.get("server_default")

        if default is not None and not has_nullable:
            kwargs.setdefault("nullable", False)

        if default is not None:
            if isinstance(default, enum.Enum):
                server_default = default.name
            else:
                server_default = str(default)

            kwargs["server_default"] = server_default

        super().__init__(*args, **kwargs)


class Leveling(Base):
    __tablename__ = "leveling"

    id = _Column(sql.BIGINT, primary_key=True, autoincrement=False)
    active = _Column(sql.BOOLEAN, server_default=False)
    channel = _Column(sql.BIGINT)
    message = _Column(sql.VARCHAR(length=2000))
    roles = _Column(sql.ARRAY(sql.BIGINT))
    no_xp_channels = _Column(sql.ARRAY(sql.BIGINT))
    no_xp_role = _Column(sql.BIGINT)
    remove_roles = _Column(sql.BOOLEAN, server_default=False)


class LevelingUsers(Base):
    __tablename__ = "leveling_users"

    id = _Column(sql.INTEGER, primary_key=True)
    guild_id = _Column(sql.BIGINT, nullable=False)
    user_id = _Column(sql.BIGINT, nullable=False)
    xp: _Column(sql.INTEGER, server_default=0)


class Welcome(Base):
    __tablename__ = "welcome"

    id = _Column(sql.BIGINT, primary_key=True, autoincrement=False)
    active = _Column(sql.BOOLEAN, server_default=False)
    join_channel = _Column(sql.BIGINT)
    join_message = _Column(sql.VARCHAR(length=2000))
    join_roles = _Column(sql.ARRAY(sql.BIGINT))
    join_active = _Column(sql.BOOLEAN, server_default=False)


class Logging(Base):
    __tablename__ = "logging"

    id = _Column(sql.BIGINT, primary_key=True, autoincrement=False)
    active = _Column(sql.BOOLEAN, server_default=False)
    webhook_id = _Column(sql.BIGINT)
    webhook_channel = _Column(sql.BIGINT)
    webhook_token = _Column(sql.VARCHAR(length=80))
    member_join = _Column(sql.BOOLEAN, server_default=False)
    member_leave = _Column(sql.BOOLEAN, server_default=False)
    member_ban = _Column(sql.BOOLEAN, server_default=False)
    member_unban = _Column(sql.BOOLEAN, server_default=False)
    member_rename = _Column(sql.BOOLEAN, server_default=False)
    member_role_change = _Column(sql.BOOLEAN, server_default=False)
    message_edit = _Column(sql.BOOLEAN, server_default=False)
    message_delete = _Column(sql.BOOLEAN, server_default=False)


class Automod(Base):
    __tablename__ = "automod"

    id = _Column(sql.BIGINT, primary_key=True, autoincrement=False)
    active = _Column(sql.BOOLEAN, server_default=False)

    invite_action = _Column(sql.Enum(enums.AutomodAction), server_default=enums.AutomodAction.none)
    invite_whitelist_channels = _Column(sql.ARRAY(sql.BIGINT))
    invite_whitelist_roles = _Column(sql.ARRAY(sql.BIGINT))
    invite_allowed = _Column(sql.ARRAY(sql.VARCHAR(length=10)))
    invite_points = _Column(sql.SMALLINT, server_default=1)

    link_action = _Column(sql.Enum(enums.AutomodAction), server_default=enums.AutomodAction.none)
    link_whitelist_channels = _Column(sql.ARRAY(sql.BIGINT))
    link_whitelist_roles = _Column(sql.ARRAY(sql.BIGINT))
    link_list = _Column(sql.ARRAY(sql.VARCHAR(length=30)))
    link_points = _Column(sql.SMALLINT, server_default=1)
    link_as_whitelist = _Column(sql.BOOLEAN, server_default=True)

    mention_action = _Column(sql.Enum(enums.AutomodAction), server_default=enums.AutomodAction.none)
    mention_points_channels = _Column(sql.SMALLINT, server_default=1)
    mention_points_roles = _Column(sql.SMALLINT, server_default=1)
    mention_whitelist = _Column(sql.ARRAY(sql.BIGINT))
    mention_settings = _Column(sql.Enum(enums.MentionSettings), server_default=enums.MentionSettings.member)
    mentions_count = _Column(sql.SMALLINT, server_default=5)

    caps_action = _Column(sql.Enum(enums.AutomodAction), server_default=enums.AutomodAction.none)
    caps_whitelist_channels = _Column(sql.ARRAY(sql.BIGINT))
    caps_whitelist_roles = _Column(sql.ARRAY(sql.BIGINT))
    caps_points = _Column(sql.SMALLINT, server_default=1)
