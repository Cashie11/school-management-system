from core.utils import to_int
from tenancy.models import School


def active_school(request):
    """Expose the resolved tenant to every template."""
    school_id = to_int(getattr(request, "school_id", None))
    school = School.objects.filter(pk=school_id).first() if school_id else None
    return {"active_school": school}


def navigation(request):
    """Expose the two-pane navigation for the signed-in account."""
    if not getattr(request, "user", None) or not request.user.is_authenticated:
        return {"nav_sections": []}

    from core.navigation import build_navigation

    return build_navigation(request)
