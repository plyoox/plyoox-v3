from __future__ import annotations

from typing import Any, TYPE_CHECKING

from recordclass import RecordClass

if TYPE_CHECKING:
    from datetime import datetime
    from lib.enums import AutomodActionEnum, AutomodChecksEnum, TimerEnum


class WelcomeModel(RecordClass):
    active: bool
    join_active: bool
    join_channel: int | None
    join_roles: list[int] | None
    join_message: str | None
    join_dm: bool
    leave_active: bool
    leave_channel: int | None
    leave_message: str | None


class LevelingModel(RecordClass):
    active: bool
    message: str | None
    channel: int | None
    roles: list[list[int]] | None
    no_xp_role: int | None
    remove_roles: bool
    no_xp_channels: list[int] | None
    booster_xp_multiplicator: int | None


class LoggingModel(RecordClass):
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


class ModerationRule(RecordClass):
    guild_id: int
    reason: str
    actions: list[AutomodExecutionModel]


class AutomodExecutionModel(RecordClass):
    action: AutomodActionEnum
    check: AutomodChecksEnum
    days: int
    points: int
    duration: int
    expires: int


class ModerationModel(RecordClass):
    active: bool
    mod_roles: list[int] | None
    ignored_roles: list[int] | None
    log_id: int | None
    log_channel: int | None
    log_token: str | None
    automod_actions: list[AutomodExecutionModel] | None
    notify_user: bool
    invite_active: bool
    invite_actions: list[AutomodExecutionModel] | None
    invite_whitelist_channels: list[int] | None
    invite_whitelist_roles: list[int] | None
    invite_allowed: list[str] | None
    link_active: bool
    link_actions: list[AutomodExecutionModel] | None
    link_whitelist_channels: list[int] | None
    link_whitelist_roles: list[int] | None
    link_list: list[str] | None
    link_is_whitelist: bool
    caps_active: bool
    caps_actions: list[AutomodExecutionModel] | None
    caps_whitelist_channels: list[int] | None
    caps_whitelist_roles: list[int] | None


class TimerModel(RecordClass):
    id: int
    guild_id: int
    target_id: int
    type: TimerEnum
    expires: datetime
    data: dict[str, Any] | None
