from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, render
from django.urls import reverse

from core.crud import delete_view, form_view
from core.pagination import paginate
from core.permissions import management_required, teaching_required
from notifications.services import (
    notify_discipline,
    notify_enrollment,
    notify_guardian_linked,
    notify_student_welcome,
)

from .forms import DisciplineForm, EnrollmentForm, GuardianForm, StudentForm
from .models import DisciplineRecord, Enrollment, Guardian, Student
from .selectors import students_for

# Students ----------------------------------------------------------------


@teaching_required
def student_list(request):
    students = students_for(request.user)
    query = request.GET.get("q", "").strip()
    if query:
        students = students.filter(
            Q(first_name__icontains=query)
            | Q(last_name__icontains=query)
            | Q(admission_number__icontains=query)
        )
    return render(
        request,
        "students/student_list.html",
        {"students": paginate(request, students), "query": query, "active": "students"},
    )


@teaching_required
def student_detail(request, pk):
    student = get_object_or_404(students_for(request.user), pk=pk)
    # Imported here to keep the students app free of an import-time coupling.
    from attendance.models import AttendanceRecord

    attendance_summary = {
        row["status"]: row["total"]
        for row in AttendanceRecord.objects.filter(student=student)
        .values("status")
        .annotate(total=Count("id"))
    }
    return render(
        request,
        "students/student_detail.html",
        {
            "student": student,
            "enrollments": student.enrollments.select_related("school_class", "term"),
            "guardians": student.guardians.select_related("user"),
            "attendance_summary": attendance_summary,
            "discipline_records": student.discipline_records.select_related("issued_by"),
            "emails": student.emails.all()[:10],
            "active": "students",
        },
    )


@management_required
def student_create(request):
    return form_view(
        request,
        form_class=StudentForm,
        template="students/student_form.html",
        title="New student",
        success_url="students:student_list",
        save_message="Student saved. A welcome email was sent where an address is on file.",
        on_save=notify_student_welcome,
        extra={"active": "students", "cancel_url": reverse("students:student_list")},
    )


@management_required
def student_edit(request, pk):
    student = get_object_or_404(Student, pk=pk)
    return form_view(
        request,
        form_class=StudentForm,
        template="students/student_form.html",
        title="Edit student",
        instance=student,
        success_url="students:student_detail",
        success_url_args=[student.pk],
        save_message="Student saved.",
        extra={"active": "students", "cancel_url": reverse("students:student_detail", args=[student.pk])},
    )


@management_required
def student_delete(request, pk):
    student = get_object_or_404(Student, pk=pk)
    return delete_view(
        request,
        obj=student,
        template="partials/_confirm_delete.html",
        success_url="students:student_list",
        success_message="Student deleted.",
        extra={"active": "students", "cancel_url": reverse("students:student_list")},
    )


# Enrollment --------------------------------------------------------------


@management_required
def enrollment_list(request):
    enrollments = Enrollment.objects.select_related("student", "school_class", "term")
    return render(
        request,
        "students/enrollment_list.html",
        {"enrollments": paginate(request, enrollments), "active": "enrollments"},
    )


@management_required
def enrollment_create(request):
    initial = {}
    student_id = request.GET.get("student")
    if student_id:
        initial["student"] = student_id
    return form_view(
        request,
        form_class=EnrollmentForm,
        template="students/enrollment_form.html",
        title="Enroll student",
        success_url="students:enrollment_list",
        save_message="Student enrolled.",
        initial=initial,
        on_save=notify_enrollment,
        extra={"active": "enrollments", "cancel_url": reverse("students:enrollment_list")},
    )


@management_required
def enrollment_delete(request, pk):
    enrollment = get_object_or_404(Enrollment, pk=pk)
    return delete_view(
        request,
        obj=enrollment,
        template="partials/_confirm_delete.html",
        success_url="students:enrollment_list",
        success_message="Enrollment removed.",
        extra={"active": "enrollments", "cancel_url": reverse("students:enrollment_list")},
    )


# Guardians ---------------------------------------------------------------


@management_required
def guardian_list(request):
    guardians = Guardian.objects.select_related("student", "user")
    return render(
        request,
        "students/guardian_list.html",
        {"guardians": paginate(request, guardians), "active": "guardians"},
    )


@management_required
def guardian_create(request):
    initial = {}
    student_id = request.GET.get("student")
    if student_id:
        initial["student"] = student_id
    return form_view(
        request,
        form_class=GuardianForm,
        template="students/guardian_form.html",
        title="Link guardian",
        success_url="students:guardian_list",
        save_message="Guardian linked and notified by email.",
        on_save=notify_guardian_linked,
        initial=initial,
        extra={"active": "guardians", "cancel_url": reverse("students:guardian_list")},
    )


@management_required
def guardian_delete(request, pk):
    guardian = get_object_or_404(Guardian, pk=pk)
    student_pk = guardian.student_id
    return delete_view(
        request,
        obj=guardian,
        template="partials/_confirm_delete.html",
        success_url="students:student_detail",
        success_url_args=[student_pk],
        success_message="Guardian unlinked.",
        extra={
            "active": "students",
            "cancel_url": reverse("students:student_detail", args=[student_pk]),
        },
    )


# Discipline --------------------------------------------------------------


@management_required
def discipline_list(request):
    records = DisciplineRecord.objects.select_related("student", "issued_by")
    return render(
        request,
        "students/discipline_list.html",
        {"records": records, "active": "discipline"},
    )


@management_required
def discipline_create(request):
    initial = {}
    student_id = request.GET.get("student")
    if student_id:
        initial["student"] = student_id

    def record_issuer(record):
        record.issued_by = request.user
        record.save(update_fields=["issued_by"])
        notify_discipline(record)

    return form_view(
        request,
        form_class=DisciplineForm,
        template="students/discipline_form.html",
        title="Record a sanction",
        success_url="students:discipline_list",
        save_message="Sanction recorded. The family was notified by email.",
        initial=initial,
        on_save=record_issuer,
        extra={"active": "discipline", "cancel_url": reverse("students:discipline_list")},
    )
