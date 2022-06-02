from dataclasses import dataclass


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
    roles: list[list[int]]
    no_xp_role: int | None
    remove_roles: bool
    no_xp_channels: list[int]


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
