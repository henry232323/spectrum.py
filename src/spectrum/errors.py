class HTTPError(Exception):
    pass


class ErrAccessDenied(HTTPError):
    pass


class ArgumentError(HTTPError):
    pass


class NullResponseError(HTTPError):
    pass


class ResourceNotFound(HTTPError):
    pass


exception_map = {
    'ErrAccessDenied': ErrAccessDenied
}
