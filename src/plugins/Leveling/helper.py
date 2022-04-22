def get_xp_from_lvl(lvl: int):
    xp = 100
    for _ in range(1, lvl + 1):
        xp += get_level_xp(_)
    return xp


def get_level_xp(lvl: int) -> int:
    return 5 * (lvl**2) + 50 * lvl + 100


def get_level_from_xp(xp: int) -> tuple[int, int]:
    level = 0
    while xp >= get_level_xp(level):
        xp -= get_level_xp(level)
        level += 1
    return level, xp
