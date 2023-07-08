from typing import Literal

AutomodExecutionReason = Literal["link", "invite", "caps", "points", "discord_rule"]
ModerationExecutedCommand = Literal["tempban", "ban", "tempmute", "kick", "unban", "softban", "unmute"]
