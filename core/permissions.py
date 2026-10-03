from functools import wraps

from django.contrib import messages
from django.contrib.auth.views import redirect_to_login
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect

from accounts.models import User


def role_required(*roles):
    """Allow only the given roles. Unauthenticated users are sent to login."""

    def decorator(view):
        @wraps(view)
        def wrapper(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect_to_login(request.get_full_path())
            if request.user.role not in roles:
                raise PermissionDenied("Your role does not permit this action.")
            return view(request, *args, **kwargs)

        return wrapper

    return decorator


def school_required(view):
    """Ensure a tenant is active. Super Admins must select a school first."""

    @wraps(view)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect_to_login(request.get_full_path())
        if request.user.is_super_admin and not request.session.get("active_school_id"):
            messages.info(request, "Select a school before continuing.")
            return redirect("tenancy:school_list")
        return view(request, *args, **kwargs)

    return wrapper


def management_required(view):
    """School Admins, or Super Admins working inside a selected school."""
    return role_required(User.Role.SUPER_ADMIN, User.Role.SCHOOL_ADMIN)(school_required(view))


def teaching_required(view):
    """School Admins, Super Admins in context, or Teachers."""
    return role_required(
        User.Role.SUPER_ADMIN, User.Role.SCHOOL_ADMIN, User.Role.TEACHER
    )(school_required(view))


def member_required(view):
    """Any signed-in account that belongs to a school."""
    return role_required(
        User.Role.SUPER_ADMIN,
        User.Role.SCHOOL_ADMIN,
        User.Role.TEACHER,
        User.Role.PARENT_STUDENT,
    )(school_required(view))


super_admin_required = role_required(User.Role.SUPER_ADMIN)
school_admin_required = role_required(User.Role.SCHOOL_ADMIN)
