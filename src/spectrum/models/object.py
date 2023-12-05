from . import abc


class Object(abc.Identifier):
    def __init__(self, client, id):
        self.id = int(id)
        self._client = client

    def __repr__(self):
        return f"Object(id={self.id})"
