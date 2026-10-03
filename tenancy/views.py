from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from core.permissions import super_admin_required

from .models import School


@super_admin_required
def school_list(request):
    schools = School.objects.order_by("name")
    return render(request, "tenancy/school_list.html", {"schools": schools})


@super_admin_required
@require_POST
def school_open(request, pk):
    school = get_object_or_404(School, pk=pk)
    request.session["active_school_id"] = school.pk
    messages.success(request, f"Now working in {school.name}.")
    return redirect("dashboard:home")


@super_admin_required
@require_POST
def school_clear(request):
    request.session.pop("active_school_id", None)
    messages.success(request, "Returned to platform view.")
    return redirect("tenancy:school_list")
