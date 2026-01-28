from __future__ import annotations

import threading
from weakref import WeakValueDictionary
from typing import Any


class FlyweightMeta(type):
    """
    Manages unique instances per class.
    Each subclass gets its own cache and its own thread-lock.
    """

    def __init__(cls, name, bases, dict):
        super().__init__(name, bases, dict)
        cls._cache = WeakValueDictionary()
        cls._lock = threading.Lock()

    def __call__(cls, *args, **kwargs):
        # Determine the unique ID for this instance
        key = cls.get_identity(*args, **kwargs)

        # Double-checked locking for thread safety
        if key in cls._cache:
            return cls._cache[key]

        with cls._lock:
            if key in cls._cache:
                return cls._cache[key]

            # Create the object (calls __new__ and __init__)
            instance = super().__call__(*args, **kwargs)
            cls._cache[key] = instance
            return instance

    def get_identity(cls, *args, **kwargs) -> Any:
        """Default: use the first argument as the unique key."""
        return args[0] if args else None


class UniqueObject(metaclass=FlyweightMeta):
    """
    Base class providing equality, hashing, and initialization guards.
    """

    def __init__(self, *args, **kwargs):
        # We use a special attribute to track if setup has already happened
        if hasattr(self, "_initialized"):
            self._already_exists = True
        else:
            self._initialized = True
            self._already_exists = False
            self._default_identity = args[0]

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, self.__class__):
            return False
        return self.get_identity(self._get_identity_args()) == other.get_identity(other._get_identity_args())

    def __hash__(self) -> int:
        return hash(self.get_identity(self._get_identity_args()))

    def _get_identity_args(self) -> Any:
        """Subclasses must return the data used to calculate identity."""
        return self._default_identity

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}: {self._get_identity_args()}>"
