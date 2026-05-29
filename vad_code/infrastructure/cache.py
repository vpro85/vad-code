"""
Утилиты кэширования.
"""


class SimpleLRUCache:
    """Простой LRU-кэш с ограничением по количеству элементов."""

    def __init__(self, max_size: int = 50) -> None:
        self.cache: dict[str, str] = {}
        self.max_size = max_size
        self._order: list[str] = []  # Для отслеживания порядка доступа

    def get(self, key: str) -> tuple[bool, str | None]:
        """Получить значение. Возвращает (found, value)."""
        if key in self.cache:
            self._move_to_end(key)
            return True, self.cache[key]
        return False, None

    def put(self, key: str, value: str) -> None:
        """Добавить значение."""
        if key in self.cache:
            self._move_to_end(key)
        else:
            if len(self.cache) >= self.max_size:
                self._evict()
        self.cache[key] = value
        if key not in self._order:
            self._order.append(key)

    def pop(self, key: str) -> None:
        """Удалить элемент."""
        self.cache.pop(key, None)
        if key in self._order:
            self._order.remove(key)

    def _move_to_end(self, key: str) -> None:
        """Переместить ключ в конец списка (самый свежий)."""
        if key in self._order:
            self._order.remove(key)
            self._order.append(key)

    def _evict(self) -> None:
        """Удалить самый старый элемент."""
        if self._order:
            oldest_key = self._order.pop(0)
            self.cache.pop(oldest_key, None)
