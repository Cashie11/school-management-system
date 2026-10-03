from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.views import (
    LoginView,
    LogoutView,
    PasswordChangeDoneView,
    PasswordChangeView,
    PasswordResetCompleteView,
    PasswordResetConfirmView,
    PasswordResetDoneView,
    PasswordResetView,
)
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.views.decorators.http import require_POST

from core.crud import form_view
from core.permissions import management_required
from core.utils import to_int
from notifications.services import notify_account_welcome, notify_guardian_linked
from students.models import Guardian
from tenancy.models import School

from .forms import (
    EmailAuthenticationForm,
    ParentCreateForm,
    SchoolProfileForm,
    SchoolSignupForm,
    StaffCreateForm,
)
from .models import User

STAFF_ROLES = (User.Role.SCHOOL_ADMIN, User.Role.TEACHER)


class AppLoginView(LoginView):
    template_name = "accounts/login.html"
    authentication_form = EmailAuthenticationForm
    redirect_authenticated_user = True


class AppLogoutView(LogoutView):
    next_page = "core:home"


# Password reset and change ------------------------------------------------


class AppPasswordResetView(PasswordResetView):
    template_name = "accounts/password_reset_form.html"
    email_template_name = "accounts/password_reset_email.txt"
    html_email_template_name = "accounts/password_reset_email.html"
    subject_template_name = "accounts/password_reset_subject.txt"
    success_url = reverse_lazy("accounts:password_reset_done")
    extra_email_context = {"site_name": "School Management"}


class AppPasswordResetDoneView(PasswordResetDoneView):
    template_name = "accounts/password_reset_done.html"


class AppPasswordResetConfirmView(PasswordResetConfirmView):
    template_name = "accounts/password_reset_confirm.html"
    success_url = reverse_lazy("accounts:password_reset_complete")


class AppPasswordResetCompleteView(PasswordResetCompleteView):
    template_name = "accounts/password_reset_complete.html"


class AppPasswordChangeView(PasswordChangeView):
    template_name = "accounts/password_change.html"
    success_url = reverse_lazy("accounts:password_change_done")


class AppPasswordChangeDoneView(PasswordChangeDoneView):
    template_name = "accounts/password_change_done.html"


def signup(request):
    if request.user.is_authenticated:
        return redirect("dashboard:home")
    form = SchoolSignupForm(request.POST or None, request.FILES or None)
    if request.method == "POST" and form.is_valid():
        school, admin = form.save()
        login(request, admin, backend="accounts.backends.EmailBackend")
        messages.success(request, f"{school.name} is ready. Add your classes and students to get started.")
        return redirect("dashboard:home")
    return render(request, "accounts/signup.html", {"form": form})


def _active_school(request):
    school_id = to_int(request.school_id)
    return School.objects.filter(pk=school_id).first() if school_id else None


# Staff accounts ----------------------------------------------------------


@management_required
def staff_list(request):
    staff = User.objects.filter(
        school_id=request.school_id, role__in=STAFF_ROLES, removed_at__isnull=True
    ).order_by("role", "first_name", "last_name", "email")
    return render(request, "accounts/staff_list.html", {"staff": staff, "active": "staff"})


@management_required
def staff_create(request):
    return form_view(
        request,
        form_class=StaffCreateForm,
        template="accounts/staff_form.html",
        title="Add staff member",
        success_url="accounts:staff_list",
        save_message="Staff account created.",
        form_kwargs={"school": _active_school(request)},
        on_save=notify_account_welcome,
        extra={"cancel_url": reverse("accounts:staff_list"), "active": "staff"},
    )


# Parent and student accounts ---------------------------------------------


@management_required
def parent_list(request):
    parents = list(
        User.objects.filter(
            school_id=request.school_id,
            role=User.Role.PARENT_STUDENT,
            removed_at__isnull=True,
        ).order_by("first_name", "last_name", "email")
    )
    links = Guardian.objects.filter(user__in=parents).select_related("student")
    by_user = {}
    for link in links:
        by_user.setdefault(link.user_id, []).append(link)
    for parent in parents:
        parent.linked_students = by_user.get(parent.pk, [])
    return render(request, "accounts/parent_list.html", {"parents": parents, "active": "parents"})


@management_required
def parent_create(request):
    def notify_new_parent(user):
        guardian = Guardian.objects.filter(user=user).order_by("-pk").first()
        if guardian:
            notify_guardian_linked(guardian)

    return form_view(
        request,
        form_class=ParentCreateForm,
        template="accounts/parent_form.html",
        title="Add parent account",
        success_url="accounts:parent_list",
        save_message="Parent account created and linked to the student.",
        form_kwargs={"school": _active_school(request)},
        on_save=notify_new_parent,
        extra={"cancel_url": reverse("accounts:parent_list"), "active": "parents"},
    )


# Managing existing accounts ----------------------------------------------


def _school_user_or_404(request, pk):
    """A live account inside the active school, or 404."""
    return get_object_or_404(
        User.objects.filter(school_id=request.school_id, removed_at__isnull=True), pk=pk
    )


def _account_home(user):
    if user.role == User.Role.PARENT_STUDENT:
        return "accounts:parent_list"
    return "accounts:staff_list"


def _guard_change(request, target):
    """Returns an error message when a change would lock the school out."""
    if target.pk == request.user.pk:
        return "You cannot change your own account here."
    if target.role == User.Role.SCHOOL_ADMIN and target.is_active:
        others = (
            User.objects.filter(
                school_id=request.school_id, role=User.Role.SCHOOL_ADMIN, is_active=True
            )
            .exclude(pk=target.pk)
            .count()
        )
        if others == 0:
            return "A school needs at least one active School Admin."
    return None


@management_required
@require_POST
def user_toggle_active(request, pk):
    target = _school_user_or_404(request, pk)
    home = _account_home(target)

    error = _guard_change(request, target)
    if error:
        messages.error(request, error)
        return redirect(home)

    target.is_active = not target.is_active
    target.save(update_fields=["is_active"])
    if target.is_active:
        messages.success(request, f"{target.email} can sign in again.")
    else:
        messages.success(request, f"{target.email} was suspended and can no longer sign in.")
    return redirect(home)


@management_required
def user_delete(request, pk):
    target = _school_user_or_404(request, pk)
    home = _account_home(target)

    error = _guard_change(request, target)
    if error:
        messages.error(request, error)
        return redirect(home)

    if request.method == "POST":
        email = target.email
        # Removal is reversible: the account is hidden and blocked, not erased, so
        # it can recognise the person if they try to sign in and can be restored.
        target.removed_at = timezone.now()
        target.is_active = False
        target.save(update_fields=["removed_at", "is_active"])
        Guardian.objects.filter(user=target).delete()
        messages.success(request, f"{email} was removed.")
        return redirect(home)

    return render(
        request,
        "partials/_confirm_delete.html",
        {
            "object": target,
            "title": f"Remove {target.email}",
            "cancel_url": reverse(home),
        },
    )


@management_required
def school_profile(request):
    school = _active_school(request)
    form = SchoolProfileForm(request.POST or None, request.FILES or None, instance=school)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "School profile updated.")
        return redirect("accounts:school_profile")
    return render(
        request,
        "accounts/school_profile.html",
        {
            "form": form,
            "school": school,
            "cancel_url": reverse("dashboard:home"),
        },
    )
