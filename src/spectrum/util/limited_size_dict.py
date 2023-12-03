from collections import OrderedDict


class LimitedSizeDict(OrderedDict):
    """https://stackoverflow.com/questions/2437617/how-to-limit-the-size-of-a-dictionary"""

    def __init__(self, *args, size_limit: int, **kwargs):
        self.size_limit = size_limit
        OrderedDict.__init__(self, *args, **kwargs)
        self._check_size_limit()

    def __setitem__(self, key, value):
        OrderedDict.__setitem__(self, key, value)
        self._check_size_limit()

    def _check_size_limit(self):
        if self.size_limit is not None:
            while len(self) > self.size_limit:
                self.popitem(last=False)
