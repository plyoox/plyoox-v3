from dataclasses import dataclass

from lib import enums


@dataclass(slots=True)
class WelcomeModel:
    active: bool
    join_active: bool
    join_channel: int | None
    join_role: int | None
    join_message: str | None
    leave_active: bool
    leave_channel: int | None
    leave_message: str | None


@dataclass(slots=True)
class LevelingModel:
    active: bool
    message: str | None
    channel: int | None
    roles: list[list[int]] | None
    no_xp_role: int | None
    remove_roles: bool
    no_xp_channels: list[int] | None


@dataclass(slots=True)
class LoggingModel:
    active: bool
    webhook_id: int | None
    webhook_channel: int | None
    webhook_token: str | None
    member_join: bool
    member_leave: bool
    member_ban: bool
    member_unban: bool
    member_rename: bool
    member_role_change: bool
    message_edit: bool
    message_delete: bool


@dataclass(slots=True)
class ModerationModel:
    mod_roles: list[int]
    ignored_roles = list[int] | None
    mute_role = int | None
    logchannel = int | None
    ban_time = int
    mute_time = int

    active: bool
    automod_action: enums.AutomodFinalAction
    notify_user: bool

    invite_action: enums.AutomodAction
    invite_whitelist_channels: list[int] | None
    invite_whitelist_roles: list[int] | None
    invite_allowed: list[str] | None
    invite_points: int

    link_action: enums.AutomodAction
    link_whitelist_channels: list[int] | None
    link_whitelist_roles: list[int] | None
    link_list: list[str] | None
    link_points: int
    link_as_whitelist: bool

    mention_action: enums.AutomodAction
    mention_points_channels: int
    mention_points_roles: int
    mention_whitelist: list[int] | None
    mention_settings: enums.MentionSettings
    mentions_count: int

    caps_action: enums.AutomodAction
    caps_whitelist_channels: list[int] | None
    caps_whitelist_roles: list[int] | None
    caps_points: int
