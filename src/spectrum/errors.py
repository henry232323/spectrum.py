class HTTPError(Exception):
    pass


class ErrAccessDenied(HTTPError):
    pass


class ArgumentError(HTTPError):
    pass


exception_map = {
    'ErrAccessDenied': ErrAccessDenied
}
