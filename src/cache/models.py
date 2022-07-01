from dataclasses import dataclass

from lib.enums import MentionSettings
from lib.types.database import AutomodActionType


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
    active: bool
    mod_roles: list[int] | None
    ignored_roles: list[int] | None
    log_id: int | None
    log_channel: int | None
    log_token: str | None
    automod_active: bool
    automod_actions: list[AutomodActionType] | None
    notify_user: bool
    invite_active: bool
    invite_actions: list[AutomodActionType] | None
    invite_whitelist_channels: list[int] | None
    invite_whitelist_roles: list[int] | None
    invite_allowed: list[str] | None
    link_active: bool
    link_actions: list[AutomodActionType] | None
    link_whitelist_channels: list[int] | None
    link_whitelist_roles: list[int] | None
    link_list: list[str] | None
    link_is_whitelist: bool
    mention_active: bool
    mention_actions: list[AutomodActionType] | None
    mention_whitelist_channels: list[int] | None
    mention_whitelist_roles: list[int] | None
    mention_settings: MentionSettings
    mention_count: int
    caps_active: bool
    caps_actions: list[AutomodActionType] | None
    caps_whitelist_channels: list[int] | None
    caps_whitelist_roles: list[int] | None
