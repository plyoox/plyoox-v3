import enum


class PlyooxModuleEnum(enum.Enum):
    Leveling = 1


class AutomodActionEnum(str, enum.Enum):
    delete = "delete"
    kick = "kick"
    ban = "ban"
    tempban = "tempban"
    tempmute = "tempmute"
    points = "points"


class AutomodFinalActionEnum(str, enum.Enum):
    kick = "kick"
    ban = "ban"
    tempban = "tempban"
    tempmute = "tempmute"


class AutomodChecksEnum(str, enum.Enum):
    no_role = "no_role"
    no_avatar = "no_avatar"
    account_age = "account_age"
    join_date = "join_date"


class TimerEnum(str, enum.Enum):
    tempban = "tempban"


class HelperPermissionEnum(str, enum.Enum):
    none = "none"
    view = "view"
    full = "full"
