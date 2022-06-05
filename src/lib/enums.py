import enum


class PlyooxModule(enum.Enum):
    Leveling = 1


class AutomodAction(enum.Enum):
    none = "none"
    kick = "kick"
    ban = "ban"
    tempban = "tban"
    tmute = "tmute"
    mute = "mute"


class AutomodFinalAction(AutomodAction):
    points = "points"


class MentionSettings(enum.Enum):
    member = "member"
    include_roles = "include_roles"
    include_mass = "include_mass"
    include_all = "include_all"
