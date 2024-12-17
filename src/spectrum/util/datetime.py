from datetime import datetime


def parse_timestamp(s):
    try:
        return datetime.utcfromtimestamp(s) if s else None
    except OSError:
        return None