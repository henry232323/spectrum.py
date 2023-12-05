import abc

from ... import client


class HasClient(abc.ABC):
    _client: 'client.Client'
