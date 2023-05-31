from collections.abc import MutableMapping


class SimpleAttrMap(MutableMapping):
    """
    Simplified the AttrMap class, which enables storing key-value pairs in
    a dictionary-like structure.
    It allows assigning and accessing the values both through attributes and items.
    In most cases used as SuperClass.
    """

    def __init__(self):
        super(SimpleAttrMap, self).__init__()
        super(SimpleAttrMap, self).__setattr__("sample", {})

    def __delitem__(self, key):
        value = self[key]
        del self.sample[key]
        self.pop(value, None)

    def __setitem__(self, item, value):
        self._try_touch_samples()
        self.sample[item] = value

    def __getitem__(self, item):
        return self.sample[item]

    def __iter__(self):
        return iter(self.sample)

    def __len__(self):
        return len(self.sample)

    def __contains__(self, key):
        return key in list(self.keys())

    def __delattr__(self, key):
        del self[key]

    def __setattr__(self, item, value):
        self.sample[item] = value

    def __getattr__(self, item):
        return self.sample[item]
