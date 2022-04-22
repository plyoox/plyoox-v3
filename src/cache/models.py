from dataclasses import dataclass


@dataclass(frozen=True)
class WelcomeModel:
    active: bool
    join_active: bool
    join_channel: int | None
    join_role: int | None
    join_message: str | None
    leave_active: bool
    leave_channel: int | None
    leave_message: str | None


@dataclass(frozen=True)
class LevelingModel:
    active: bool
    message: str | None
    channel: int | None
    roles: list[list[int]]
    no_xp_role: int | None
    remove_roles: bool
    no_xp_channels: list[int]
