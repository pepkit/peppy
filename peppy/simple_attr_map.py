from collections.abc import Iterator, MutableMapping
from typing import Any


class SimpleAttMap(MutableMapping):
    """
    Simplified the AttrMap class, which enables storing key-value pairs in
    a dictionary-like structure.
    It allows assigning and accessing the values both through attributes and items.
    In most cases used as SuperClass.
    """

    def __init__(self) -> None:
        super(SimpleAttMap, self).__init__()
        super(SimpleAttMap, self).__setattr__("_mapped_attr", {})

    def __delitem__(self, key: str) -> None:
        value = self[key]
        del self._mapped_attr[key]
        self.pop(value, None)

    def __setitem__(self, item: str, value: Any) -> None:
        self._try_touch_samples()
        self._mapped_attr[item] = value

    def __getitem__(self, item: str) -> Any:
        return self._mapped_attr[item]

    def __iter__(self) -> Iterator[str]:
        return iter(self._mapped_attr)

    def __len__(self) -> int:
        return len(self._mapped_attr)

    def __contains__(self, key: object) -> bool:
        return key in list(self.keys())

    def __delattr__(self, key: str) -> None:
        del self[key]

    def __setattr__(self, item: str, value: Any) -> None:
        self._mapped_attr[item] = value

    def __getattr__(self, item: str) -> Any:
        try:
            return self._mapped_attr[item]
        except KeyError:
            raise AttributeError(f"Attribute not found: {item}")

    def __eq__(self, other: "SimpleAttMap") -> bool:
        return self._mapped_attr == other._mapped_attr

    @property
    def attributes(self) -> dict:
        return self._mapped_attr
