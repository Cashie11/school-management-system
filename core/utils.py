def to_int(value):
    """Return an int, or None when the value is missing or not numeric.

    Used for values that arrive from a query string or a form so untrusted input
    never reaches a numeric ``filter`` and raises a ValueError.
    """
    try:
        return int(value)
    except (TypeError, ValueError):
        return None
