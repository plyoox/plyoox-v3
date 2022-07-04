from typing import Literal

AutomodExecutionReason = Literal["link", "mention", "invite", "caps", "points"]
ModerationExecutedCommand = Literal["tempban", "ban", "tempmute", "kick"]
