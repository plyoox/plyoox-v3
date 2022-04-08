from dataclasses import dataclass
from datetime import datetime
from typing import TypedDict


@dataclass(frozen=True)
class WelcomeModel:
    join_active: bool
    join_channel: int | None
    join_role: int | None
    join_message: str | None
    leave_active: bool
    leave_channel: int | None
    leave_message: str | None


class GuildCache(TypedDict):
    accessed_at: datetime
    welcome: Welcome
