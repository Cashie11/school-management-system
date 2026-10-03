from django.contrib import messages
from django.db.models import Count
from django.shortcuts import redirect, render
from django.utils import timezone
from django.utils.dateparse import parse_date

from academics.models import AcademicTerm, SchoolClass
from core.pagination import paginate
from core.permissions import teaching_required
from core.utils import to_int
from notifications.services import notify_absence, notify_enrollment
from students.models import Enrollment, Student

from .models import AttendanceRecord

ALL_CLASSES = "all"


def available_classes(user):
    """Classes a user may work with. Teachers see only their assigned classes."""
    classes = SchoolClass.objects.all()
    if user.is_teacher:
        classes = classes.filter(class_subjects__teacher=user).distinct()
    return classes


def _class_selection(request, classes):
    """Return (class or None, all_mode)."""
    raw = request.POST.get("school_class") or request.GET.get("school_class")
    if raw == ALL_CLASSES:
        return None, True
    class_id = to_int(raw)
    if class_id is not None:
        match = classes.filter(pk=class_id).first()
        if match:
            return match, False
    return classes.first(), False


def _selected_term(request):
    raw = request.POST.get("term") or request.GET.get("term")
    term_id = to_int(raw)
    if term_id is not None:
        match = AcademicTerm.objects.filter(pk=term_id).first()
        if match:
            return match
    return AcademicTerm.objects.filter(is_current=True).first() or AcademicTerm.objects.first()


def _selected_date(request):
    raw = request.POST.get("date") or request.GET.get("date")
    parsed = parse_date(raw) if raw else None
    return parsed or timezone.localdate()


def _register_url(request, school_class, all_mode, term, date):
    class_value = ALL_CLASSES if all_mode else (school_class.pk if school_class else "")
    return (
        f"{request.path}?school_class={class_value}"
        f"&term={term.pk if term else ''}&date={date.isoformat()}"
    )


@teaching_required
def register(request):
    classes = available_classes(request.user)
    school_class, all_mode = _class_selection(request, classes)
    term = _selected_term(request)
    date = _selected_date(request)

    # Enroll a student into the selected class for the selected term.
    if request.method == "POST" and request.POST.get("action") == "enroll":
        if school_class and term and not all_mode:
            student_pk = to_int(request.POST.get("student"))
            student = Student.objects.filter(pk=student_pk).first() if student_pk else None
            if student and not Enrollment.objects.filter(term=term, student=student).exists():
                enrollment = Enrollment.objects.create(
                    student=student, school_class=school_class, term=term
                )
                messages.success(
                    request, f"{student.full_name} enrolled in {school_class} for {term}."
                )
                notify_enrollment(enrollment)
        return redirect(_register_url(request, school_class, all_mode, term, date))

    enrollments = []
    if term:
        if all_mode:
            enrollments = list(
                Enrollment.objects.filter(term=term).select_related("student", "school_class")
            )
        elif school_class:
            enrollments = list(
                Enrollment.objects.filter(school_class=school_class, term=term).select_related(
                    "student", "school_class"
                )
            )

    students = [enrollment.student for enrollment in enrollments]

    if request.method == "POST" and request.POST.get("action") == "save":
        posted_class = request.POST.get("school_class")
        expected = ALL_CLASSES if all_mode else (str(school_class.pk) if school_class else "")
        if str(posted_class) == expected and term and students:
            for student in students:
                status = request.POST.get(f"status_{student.pk}")
                note = (request.POST.get(f"note_{student.pk}") or "").strip()[:200]
                existing = AttendanceRecord.objects.filter(student=student, date=date).first()
                if status not in AttendanceRecord.Status.values:
                    if existing:
                        existing.delete()
                    continue
                if existing:
                    previous_status = existing.status
                    existing.status = status
                    existing.note = note
                    existing.term = term
                    existing.recorded_by = request.user
                    existing.save()
                    record = existing
                else:
                    previous_status = None
                    record = AttendanceRecord.objects.create(
                        student=student,
                        term=term,
                        date=date,
                        status=status,
                        note=note,
                        recorded_by=request.user,
                    )
                if (
                    status == AttendanceRecord.Status.ABSENT
                    and previous_status != AttendanceRecord.Status.ABSENT
                ):
                    notify_absence(record)
            messages.success(request, f"Attendance saved for {date.strftime('%d %b %Y')}.")
        return redirect(_register_url(request, school_class, all_mode, term, date))

    existing = {}
    if students:
        for record in AttendanceRecord.objects.filter(date=date, student__in=students):
            existing[record.student_id] = record

    rows = [
        {
            "student": enrollment.student,
            "school_class": enrollment.school_class,
            "status": existing[enrollment.student_id].status
            if enrollment.student_id in existing
            else AttendanceRecord.Status.PRESENT,
            "note": existing[enrollment.student_id].note
            if enrollment.student_id in existing
            else "",
        }
        for enrollment in enrollments
    ]

    # Students enrolled in another class for this term (only relevant in single-class mode).
    other_classes = []
    if term and not all_mode and school_class:
        other_classes = list(
            Enrollment.objects.filter(term=term)
            .exclude(school_class=school_class)
            .select_related("student", "school_class")
        )

    # Active students with no enrollment at all for this term.
    unlisted = Student.objects.none()
    if term:
        enrolled_ids = list(Enrollment.objects.filter(term=term).values_list("student_id", flat=True))
        unlisted = (
            Student.objects.filter(is_active=True)
            .exclude(pk__in=enrolled_ids)
            .order_by("last_name", "first_name")
        )

    return render(
        request,
        "attendance/register.html",
        {
            "classes": classes,
            "terms": AcademicTerm.objects.all(),
            "selected_class": school_class,
            "all_mode": all_mode,
            "selected_term": term,
            "date": date,
            "rows": rows,
            "other_classes": other_classes,
            "unlisted": unlisted,
            "statuses": AttendanceRecord.Status.choices,
            "active": "register",
        },
    )


@teaching_required
def record_list(request):
    records = AttendanceRecord.objects.select_related("student", "term").order_by(
        "-date", "student__last_name"
    )
    classes = available_classes(request.user)

    school_class = None
    class_id = to_int(request.GET.get("school_class"))
    if class_id is not None:
        school_class = classes.filter(pk=class_id).first()
        if school_class:
            student_ids = Enrollment.objects.filter(school_class=school_class).values_list(
                "student_id", flat=True
            )
            records = records.filter(student_id__in=student_ids)

    status = request.GET.get("status")
    if status in AttendanceRecord.Status.values:
        records = records.filter(status=status)
    else:
        status = ""

    date_raw = request.GET.get("date")
    date = parse_date(date_raw) if date_raw else None
    if date:
        records = records.filter(date=date)

    summary = {
        row["status"]: row["total"]
        for row in AttendanceRecord.objects.values("status").annotate(total=Count("id"))
    }

    return render(
        request,
        "attendance/record_list.html",
        {
            "records": paginate(request, records),
            "classes": classes,
            "selected_class": school_class,
            "status": status,
            "date": date,
            "statuses": AttendanceRecord.Status.choices,
            "summary": summary,
            "active": "records",
        },
    )
