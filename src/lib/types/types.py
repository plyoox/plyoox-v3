from typing import Literal

AutomodExecutionReason = Literal["link", "mention", "invite", "caps", "points", "blacklist"]
ModerationExecutedCommand = Literal["tempban", "ban", "tempmute", "kick", "unban", "softban", "unmute"]
