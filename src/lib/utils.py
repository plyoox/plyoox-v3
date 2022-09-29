# https://github.com/Rapptz/RoboDanny/blob/rewrite/cogs/utils/cache.py#L22
import time


class ExpiringCache(dict):
    def __init__(self, seconds):
        self.__ttl = seconds
        super().__init__()

    def __verify_cache_integrity(self):
        # Have to do this in two steps...
        current_time = time.monotonic()
        to_remove = [k for (k, (v, t)) in self.items() if current_time > (t + self.__ttl)]
        for k in to_remove:
            del self[k]

    def __contains__(self, key):
        self.__verify_cache_integrity()
        return super().__contains__(key)

    def __getitem__(self, key):
        self.__verify_cache_integrity()
        return super().__getitem__(key)[0]

    def __setitem__(self, key, value):
        super().__setitem__(key, (value, time.monotonic()))

    def get(self, key, value=None):
        try:
            return self.__getitem__(key)
        except KeyError:
            return value
