"""Grade boundaries used on report cards."""

GRADE_SCALE = (
    (80, "A", "Excellent"),
    (70, "B", "Very good"),
    (60, "C", "Good"),
    (50, "D", "Fair"),
    (40, "E", "Pass"),
    (0, "F", "Fail"),
)


def grade_for(percentage):
    """Return (code, label) for a percentage, or None when there is no mark."""
    if percentage is None:
        return None
    for threshold, code, label in GRADE_SCALE:
        if percentage >= threshold:
            return code, label
    return GRADE_SCALE[-1][1], GRADE_SCALE[-1][2]
