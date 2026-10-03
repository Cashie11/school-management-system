from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db.models import Count
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from academics.models import AcademicTerm, SchoolClass, Subject
from academics.selectors import class_subjects_for, classes_for
from accounts.models import User
from announcements.selectors import visible_announcements
from attendance.models import AttendanceRecord
from results.models import Assessment
from students.models import Enrollment, Student
from students.selectors import students_for
from tenancy.models import School

from .reporting import platform_rows


@login_required
def home(request):
    """Route each role to the dashboard that fits it."""
    user = request.user
    if user.is_super_admin and not request.school_id:
        return _platform_dashboard(request)
    if user.is_parent_student:
        return redirect("portal:home")
    if user.is_teacher:
        return _teacher_dashboard(request)
    return _admin_dashboard(request)


def _platform_dashboard(request):
    """Platform view for Super Admins, who have no school of their own."""
    schools = list(School.objects.order_by("name"))
    rows = platform_rows(schools)
    return render(
        request,
        "dashboard/platform_home.html",
        {
            "rows": rows,
            "school_count": len(schools),
            "active_school_count": sum(1 for school in schools if school.is_active),
            "total_students": sum(row["students"] for row in rows),
            "total_users": User.objects.count(),
        },
    )


def _teacher_dashboard(request):
    user = request.user
    class_subjects = list(
        class_subjects_for(user).order_by("school_class__level", "school_class__name", "subject__name")
    )
    class_ids = {class_subject.school_class_id for class_subject in class_subjects}
    subject_ids = [class_subject.pk for class_subject in class_subjects]

    assessment_counts = {
        row["class_subject_id"]: row["n"]
        for row in Assessment.objects.filter(class_subject_id__in=subject_ids)
        .values("class_subject_id")
        .annotate(n=Count("id"))
    }

    student_counts = {}
    if class_ids:
        pairs = (
            Enrollment.objects.filter(school_class_id__in=class_ids)
            .values("school_class_id", "student_id")
            .distinct()
        )
        for row in pairs:
            student_counts[row["school_class_id"]] = student_counts.get(row["school_class_id"], 0) + 1

    rows = [
        {
            "class_subject": class_subject,
            "student_count": student_counts.get(class_subject.school_class_id, 0),
            "assessment_count": assessment_counts.get(class_subject.pk, 0),
        }
        for class_subject in class_subjects
    ]

    assessments = Assessment.objects.filter(class_subject_id__in=subject_ids).select_related(
        "class_subject__subject", "class_subject__school_class", "term"
    ).order_by("-term__start_date", "class_subject__subject__name", "name")
    return render(
        request,
        "dashboard/teacher_home.html",
        {
            "rows": rows,
            "assessments": assessments,
            "class_count": len(class_ids),
            "subject_count": len(class_subjects),
            "student_count": students_for(user).count(),
            "assessment_count": assessments.count(),
            "announcements": visible_announcements(user)[:3],
        },
    )


def _admin_dashboard(request):
    term = AcademicTerm.objects.filter(is_current=True).first() or AcademicTerm.objects.first()
    return render(
        request,
        "dashboard/admin_home.html",
        {
            "term": term,
            "student_count": Student.objects.count(),
            "teacher_count": User.objects.filter(
                school_id=request.school_id, role=User.Role.TEACHER, removed_at__isnull=True
            ).count(),
            "class_count": SchoolClass.objects.count(),
            "subject_count": Subject.objects.count(),
            "assessment_count": Assessment.objects.count(),
            "today_attendance": AttendanceRecord.objects.filter(date=timezone.localdate()).count(),
            "today": timezone.localdate(),
            "announcements": visible_announcements(request.user)[:3],
        },
    )


@login_required
def class_list(request):
    user = request.user
    if not (user.is_teacher or user.is_school_admin or user.is_super_admin):
        raise PermissionDenied("Your role does not permit this action.")

    rows = []
    for school_class in classes_for(user).order_by("level", "name"):
        rows.append(
            {
                "school_class": school_class,
                "subjects": class_subjects_for(user).filter(school_class=school_class),
                "student_count": Enrollment.objects.filter(school_class=school_class)
                .values("student_id")
                .distinct()
                .count(),
            }
        )
    return render(request, "dashboard/class_list.html", {"rows": rows})


@login_required
def class_detail(request, pk):
    user = request.user
    if not (user.is_teacher or user.is_school_admin or user.is_super_admin):
        raise PermissionDenied("Your role does not permit this action.")

    school_class = get_object_or_404(SchoolClass, pk=pk)
    class_subjects = class_subjects_for(user).filter(school_class=school_class)
    if user.is_teacher and not class_subjects.exists():
        raise PermissionDenied("You can only open the classes you teach.")

    subject_ids = [class_subject.pk for class_subject in class_subjects]
    return render(
        request,
        "dashboard/class_detail.html",
        {
            "school_class": school_class,
            "class_subjects": class_subjects,
            "enrollments": Enrollment.objects.filter(school_class=school_class).select_related(
                "student", "term"
            ),
            "assessments": Assessment.objects.filter(class_subject_id__in=subject_ids)
            .select_related("class_subject__subject", "term")
            .order_by("-term__start_date", "name"),
        },
    )
