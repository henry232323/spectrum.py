from . import abc


class Upload(abc.Identifier):
    """Represents an uploaded media item. Can be passed directly to ContentBuilder.image()."""

    def __init__(self, data: dict):
        self.id = data['id']
        self.type = data.get('type', 'upload')
        self.processing = data.get('processing', False)
        self.data = data.get('data')

    def __repr__(self):
        return f"Upload(id={self.id!r})"

    def __str__(self):
        return self.id
