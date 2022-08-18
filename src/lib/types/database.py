from typing import TypedDict


class LevelUserData(TypedDict):
    id: int
    user_id: int
    guild_id: int
    xp: int
    rank: int
