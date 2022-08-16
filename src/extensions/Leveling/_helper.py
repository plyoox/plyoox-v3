def get_xp_from_lvl(lvl: int):
    """Calculates the overall needed xp to gain this level."""
    xp = 100
    for _ in range(1, lvl + 1):
        xp += get_level_xp(_)
    return xp


def get_level_xp(lvl: int) -> int:
    """Calculates the needed xp for the level."""
    return 5 * (lvl**2) + 50 * lvl + 100


def get_level_from_xp(xp: int) -> tuple[int, int]:
    """Calculates the level from the xp. Returns the current level and the remaining xp."""
    level = 0
    while xp >= get_level_xp(level):
        xp -= get_level_xp(level)
        level += 1
    return level, xp
