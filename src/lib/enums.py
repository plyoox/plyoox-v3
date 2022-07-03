import enum


class PlyooxModule(enum.Enum):
    Leveling = 1


class AutomodAction(str, enum.Enum):
    delete = "delete"
    kick = "kick"
    ban = "ban"
    tempban = "tempban"
    tempmute = "tempmute"
    points = "points"


class AutomodFinalAction(str, enum.Enum):
    kick = "kick"
    ban = "ban"
    tempban = "tempban"
    tempmute = "tempmute"


class MentionSettings(str, enum.Enum):
    member = "member"
    include_roles = "include_roles"
    include_mass = "include_mass"
    include_all = "include_all"


class AutomodChecks(str, enum.Enum):
    no_role = "no_role"
    no_avatar = "no_avatar"
    account_age = "account_age"
    join_date = "join_date"


class TimerType(str, enum.Enum):
    tempban = "tempban"
