from collections import deque
from typing import Iterable


class MessageCache[T]:
    def __init__(self, max_length: int | None):
        self._max_length = max_length

        self._items: deque[T] = deque(maxlen=max_length)
        self._lookup: dict[int, T] = dict()

    def __len__(self) -> int:
        return len(self._items)

    def add_item(self, item: T):
        if len(self._items) == self._max_length and self._items[0].id in self._lookup:
            # If the cache is full, and we need to remove an item from
            # the left of the deque, then remove its reference from the dict as well.
            del self._lookup[self._items[0].id]

        self._items.append(item)
        self._lookup[item.id] = item

    def get_item(self, id: int) -> T | None:
        return self._lookup.get(id)

    def remove_item(self, id: int) -> T | None:
        item_to_remove = self.get_item(id)

        if item_to_remove:
            self._items.remove(item_to_remove)
            del self._lookup[id]

        return item_to_remove

    def remove_many(self, ids: Iterable[int]):
        for id in ids:
            self.remove_item(id)

    def is_sync(self):
        return len(self._items) == len(self._lookup)
