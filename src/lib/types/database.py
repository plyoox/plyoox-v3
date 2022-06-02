from typing import TypedDict, Optional


class LevelUserData(TypedDict):
    id: int
    user_id: int
    guild_id: int
    xp: int


class WelcomeData(TypedDict):
    id: int
    active: bool
    join_channel: Optional[int]
    join_message: Optional[str]
    join_roles: Optional[list[int]]
    join_active: bool
    leave_channel: Optional[int]
    leave_message: Optional[str]
    leave_active: bool
