import enum


class PlyooxModule(enum.Enum):
    Leveling = 1


class AutomodAction(enum.Enum):
    delete = "delete"
    kick = "kick"
    ban = "ban"
    tempban = "tban"
    tempmute = "tmute"
    points = "points"


class AutomodFinalAction(enum.Enum):
    none = "none"
    kick = "kick"
    ban = "ban"
    tempban = "tban"
    tmute = "tmute"
    mute = "mute"


class MentionSettings(enum.Enum):
    member = "member"
    include_roles = "include_roles"
    include_mass = "include_mass"
    include_all = "include_all"


class AutomodChecks:
    no_role = "no_role"
    no_avatar = "no_avatar"
    account_age = "account_age"
    join_date = "join_date"
