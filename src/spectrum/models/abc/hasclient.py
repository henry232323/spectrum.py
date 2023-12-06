import abc

from ... import httpclient


class HasClient(abc.ABC):
    _client: 'httpclient.HTTPClient'
