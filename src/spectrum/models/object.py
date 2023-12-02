from . import abc


class Object(abc.Identifier):
    def __init__(self, client, id):
        self.id = id
        self._client = client