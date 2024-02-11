import enum


class PlyooxModuleEnum(enum.Enum):
    Leveling = 1


class AutoModerationPunishmentKind(enum.StrEnum):
    delete = "delete"
    kick = "kick"
    ban = "ban"
    tempban = "tempban"
    tempmute = "tempmute"
    point = "point"


class AutomodFinalActionEnum(enum.StrEnum):
    kick = "kick"
    ban = "ban"
    tempban = "tempban"
    tempmute = "tempmute"


class AutoModerationCheckKind(enum.StrEnum):
    no_role = "no_role"
    no_avatar = "no_avatar"
    account_age = "account_age"
    join_date = "join_date"


class TimerEnum(enum.StrEnum):
    temp_ban = "temp_ban"


class LoggingKind(enum.StrEnum):
    member_ban = "member_ban"
    member_rename = "member_rename"
    member_join = "member_join"
    message_edit = "message_edit"
    message_delete = "message_delete"
    member_unban = "member_unban"
    member_role_update = "member_role_update"
    member_leave = "member_leave"


class AutoModerationFinalPunishmentKind(enum.StrEnum):
    kick = "kick"
    ban = "ban"
    tempban = "tempban"
    tempmute = "tempmute"


class ModerationCommandKind(enum.StrEnum):
    tempban = "tempban"
    ban = "ban"
    tempmute = "tempmute"
    unban = "unban"
    softban = "softban"
    unmute = "unmute"
    kick = "kick"


class AutoModerationExecutionKind(enum.StrEnum):
    link = "link"
    invite = "invite"
    caps = "caps"
    point = "point"
    discord_rule = "discord_rule"


class BotError(enum.Enum):
    missing_permission = enum.auto()
