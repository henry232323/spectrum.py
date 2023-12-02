from . import abc


class Object(abc.Identifier):
    def __init__(self, client, id):
        self.id = int(id)
        self._client = client

    def repr(self):
        return f"Object(id={self.id})"
