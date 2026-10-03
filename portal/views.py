from django.contrib import messages
from django.db.models import Count
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.dateparse import parse_date

from academics.models import AcademicTerm
from accounts.models import User
from attendance.models import AttendanceRecord
from core.permissions import role_required
from core.utils import to_int
from results.exams import (
    finalize_submission,
    mark_objective_answers,
    online_assessments_for,
)
from results.models import Answer, Assessment, Submission
from results.services import report_card_pdf, student_term_report, term_positions
from students.models import Enrollment, Guardian

parent_required = role_required(User.Role.PARENT_STUDENT)


def _my_student(request, pk):
    """A student this account is a guardian of, or 404."""
    link = get_object_or_404(
        Guardian.objects.select_related("student"), user=request.user, student_id=pk
    )
    return link.student


@parent_required
def home(request):
    from announcements.selectors import visible_announcements

    students = [
        link.student for link in Guardian.objects.filter(user=request.user).select_related("student")
    ]
    return render(
        request,
        "portal/home.html",
        {"students": students, "announcements": visible_announcements(request.user)[:3]},
    )


@parent_required
def student_exams(request, pk):
    student = _my_student(request, pk)
    assessments = online_assessments_for(student)
    submissions = {s.assessment_id: s for s in Submission.objects.filter(student=student)}
    now = timezone.now()

    rows = []
    for assessment in assessments:
        is_open, reason = assessment.opens_at(now)
        rows.append(
            {
                "assessment": assessment,
                "is_open": is_open,
                "reason": reason,
                "submission": submissions.get(assessment.pk),
            }
        )
    return render(
        request,
        "portal/student_exams.html",
        {"student": student, "rows": rows, "active": "exams"},
    )


@parent_required
def exam_take(request, pk, assessment_pk):
    student = _my_student(request, pk)
    assessment = get_object_or_404(
        Assessment.objects.select_related("class_subject__subject", "term"), pk=assessment_pk
    )

    enrolled = Enrollment.objects.filter(
        student=student, school_class=assessment.class_subject.school_class, term=assessment.term
    ).exists()
    if not enrolled:
        messages.error(request, "This assessment is not set for this student.")
        return redirect("portal:student_exams", pk=student.pk)

    is_open, reason = assessment.opens_at()
    if not is_open:
        messages.error(request, reason)
        return redirect("portal:student_exams", pk=student.pk)

    submission = Submission.objects.filter(assessment=assessment, student=student).first()
    if submission and submission.is_submitted:
        messages.info(request, "This assessment has already been submitted.")
        return redirect("portal:exam_result", pk=student.pk, assessment_pk=assessment.pk)

    questions = list(
        assessment.questions.prefetch_related("choices").order_by("section", "order", "id")
    )

    if submission is None:
        duration = assessment.duration_minutes
        submission = Submission.objects.create(
            assessment=assessment,
            student=student,
            status=Submission.Status.IN_PROGRESS,
            started_at=timezone.now(),
            expires_at=timezone.now() + timezone.timedelta(minutes=duration) if duration else None,
        )
        for question in questions:
            Answer.objects.create(submission=submission, question=question)

    expired = submission.expires_at is not None and timezone.now() >= submission.expires_at

    if request.method == "POST" or expired:
        for question in questions:
            answer = submission.answers.filter(question=question).first()
            if answer is None:
                answer = Answer.objects.create(submission=submission, question=question)
            if question.is_objective:
                raw = to_int(request.POST.get(f"choice_{question.pk}"))
                answer.selected_choice = question.choices.filter(pk=raw).first() if raw else None
                answer.save(update_fields=["selected_choice"])
            else:
                answer.text_answer = (request.POST.get(f"text_{question.pk}") or "").strip()
                answer.save(update_fields=["text_answer"])
        mark_objective_answers(submission)
        finalize_submission(submission)
        if expired and request.method != "POST":
            messages.warning(request, "Time ran out. Your answers were submitted.")
        else:
            messages.success(request, "Your answers were submitted.")
        return redirect("portal:exam_result", pk=student.pk, assessment_pk=assessment.pk)

    answers = {answer.question_id: answer for answer in submission.answers.all()}
    objective_rows = []
    theory_rows = []
    for question in questions:
        answer = answers.get(question.pk)
        if question.is_objective:
            objective_rows.append(
                {
                    "question": question,
                    "choices": question.choices.all(),
                    "selected_choice_id": answer.selected_choice_id if answer else None,
                }
            )
        else:
            theory_rows.append(
                {"question": question, "text_answer": answer.text_answer if answer else ""}
            )

    return render(
        request,
        "portal/exam_take.html",
        {
            "student": student,
            "assessment": assessment,
            "objective_rows": objective_rows,
            "theory_rows": theory_rows,
            "submission": submission,
        },
    )


@parent_required
def exam_result(request, pk, assessment_pk):
    student = _my_student(request, pk)
    assessment = get_object_or_404(Assessment, pk=assessment_pk)
    submission = get_object_or_404(Submission, assessment=assessment, student=student)
    return render(
        request,
        "portal/exam_result.html",
        {"student": student, "assessment": assessment, "submission": submission},
    )


# Results -----------------------------------------------------------------


def _report_context(request, student, term):
    report = student_term_report(student, term)
    positions, class_size = term_positions(report["school_class"], term)
    return {
        "report": report,
        "position": positions.get(student.pk),
        "class_size": class_size,
    }


@parent_required
def student_results(request, pk):
    student = _my_student(request, pk)
    enrollments = list(
        Enrollment.objects.filter(student=student)
        .select_related("term", "school_class")
        .order_by("-term__start_date")
    )
    selected = None
    term_id = request.GET.get("term")
    if term_id:
        selected = next((e for e in enrollments if str(e.term_id) == str(term_id)), None)
    if selected is None and enrollments:
        selected = enrollments[0]

    context = {"student": student, "enrollments": enrollments, "selected": selected, "active": "results"}
    if selected is not None:
        context.update(_report_context(request, student, selected.term))
    return render(request, "portal/student_results.html", context)


@parent_required
def student_report_pdf(request, pk, term_pk):
    student = _my_student(request, pk)
    term = get_object_or_404(AcademicTerm, pk=term_pk)
    context = _report_context(request, student, term)
    report = context["report"]
    school = request.user.school
    pdf_bytes = report_card_pdf(
        report,
        school_name=str(school) if school else "School",
        position=context["position"],
        class_size=context["class_size"],
    )
    filename = f"report-card-{report['student'].admission_number}-{report['term'].name}.pdf"
    response = HttpResponse(pdf_bytes, content_type="application/pdf")
    response["Content-Disposition"] = f'inline; filename="{filename}"'
    return response


# Attendance --------------------------------------------------------------


@parent_required
def student_attendance(request, pk):
    student = _my_student(request, pk)
    records = AttendanceRecord.objects.filter(student=student).select_related("term").order_by("-date")

    term_id = request.GET.get("term")
    term_filter = to_int(term_id)
    if term_filter is not None:
        records = records.filter(term_id=term_filter)

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
        for row in AttendanceRecord.objects.filter(student=student)
        .values("status")
        .annotate(total=Count("id"))
    }

    return render(
        request,
        "portal/student_attendance.html",
        {
            "student": student,
            "records": records[:300],
            "terms": AcademicTerm.objects.all(),
            "selected_term": term_id or "",
            "status": status,
            "date": date,
            "statuses": AttendanceRecord.Status.choices,
            "summary": summary,
            "active": "attendance",
        },
    )
