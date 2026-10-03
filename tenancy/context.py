from contextlib import contextmanager
from contextvars import ContextVar

_current_school_id = ContextVar("current_school_id", default=None)


def get_current_school_id():
    return _current_school_id.get()


@contextmanager
def school_context(school):
    school_id = getattr(school, "pk", school)
    token = _current_school_id.set(school_id)
    try:
        yield
    finally:
        _current_school_id.reset(token)