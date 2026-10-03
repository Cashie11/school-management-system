from django import template

register = template.Library()


@register.filter
def in_list(value, comma_separated):
    """True when value appears in a comma separated string.

    Used to hide the back control on pages where it makes no sense.
    """
    if value is None:
        return False
    return str(value) in [item.strip() for item in str(comma_separated).split(",")]
