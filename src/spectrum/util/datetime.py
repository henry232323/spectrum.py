from datetime import datetime, UTC


def parse_timestamp(s):
    try:
        return datetime.fromtimestamp(s, UTC) if s else None
    except OSError:
        return None