from __future__ import annotations

from typing import Any, TYPE_CHECKING

from recordclass import RecordClass

if TYPE_CHECKING:
    from datetime import datetime
    from lib.enums import AutoModerationPunishmentKind, AutoModerationCheckKind, TimerEnum


class LevelRole(RecordClass):
    role: int
    level: int


class WelcomeModel(RecordClass):
    join_active: bool
    join_channel: int | None
    join_roles: list[int] | None
    join_message: str | None
    join_dm: bool
    leave_active: bool
    leave_channel: int | None
    leave_message: str | None


class LevelingModel(RecordClass):
    message: str | None
    channel: int | None
    roles: list[LevelRole]
    remove_roles: bool
    exempt_role: int | None
    exempt_channels: list[int]
    booster_xp_multiplier: int | None


class MaybeWebhook(RecordClass):
    webhook_id: int
    token: str | None
    channel_id: int | None
    guild_id: int


class LoggingSettings(RecordClass):
    channel: MaybeWebhook | None
    kind: str
    exempt_channels: list[int] | None
    exempt_roles: list[int] | None


class LoggingModel(RecordClass):
    settings: dict[str, LoggingSettings]


class ModerationRule(RecordClass):
    guild_id: int
    reason: str
    actions: list[AutoModerationAction]


class AutoModerationCheck(RecordClass):
    check: AutoModerationCheckKind
    time: int | None


class AutomoderationPunishment(RecordClass):
    action: AutoModerationPunishmentKind
    duration: int | None
    points: int | None
    expires_in: int | None


class AutoModerationAction(RecordClass):
    punishment: AutomoderationPunishment
    check: AutoModerationCheck | None


class ModerationModel(RecordClass):
    active: bool
    mod_roles: list[int] | None
    ignored_roles: list[int] | None
    log_id: int | None
    log_channel: int | None
    log_token: str | None
    point_actions: list[AutoModerationAction] | None
    notify_user: bool
    invite_active: bool
    invite_actions: list[AutoModerationAction] | None
    invite_exempt_channels: list[int] | None
    invite_exempt_roles: list[int] | None
    invite_allowed: list[str] | None
    link_active: bool
    link_actions: list[AutoModerationAction] | None
    link_exempt_channels: list[int] | None
    link_exempt_roles: list[int] | None
    link_allow_list: list[str] | None
    link_is_whitelist: bool
    caps_active: bool
    caps_actions: list[AutoModerationAction] | None
    caps_exempt_channels: list[int] | None
    caps_exempt_roles: list[int] | None


class TimerModel(RecordClass):
    id: int
    guild_id: int
    target_id: int
    type: TimerEnum
    expires: datetime
    data: dict[str, Any] | None
