from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from academics.models import AcademicTerm
from core.crud import delete_view, form_view
from core.pagination import paginate
from core.permissions import teaching_required
from core.utils import to_int
from notifications.services import notify_assessment_published, notify_results
from students.models import Enrollment, Student

from .exams import finalize_submission
from .forms import AssessmentForm, ChoiceForm, QuestionForm
from .models import Assessment, Choice, Question, Score, Submission
from .scoping import available_class_subjects
from .services import report_card_pdf, student_term_report, term_positions


def _selected_term(request):
    raw = request.GET.get("term")
    term_id = to_int(raw)
    if term_id is not None:
        match = AcademicTerm.objects.filter(pk=term_id).first()
        if match:
            return match
    return AcademicTerm.objects.filter(is_current=True).first() or AcademicTerm.objects.first()


def _teacher_class_ids(user):
    return set(available_class_subjects(user).values_list("school_class_id", flat=True))


def _get_assessment(request, pk):
    assessment = get_object_or_404(
        Assessment.objects.select_related(
            "class_subject__school_class", "class_subject__subject", "term"
        ),
        pk=pk,
    )
    if request.user.is_teacher and assessment.class_subject.teacher_id != request.user.pk:
        raise PermissionDenied("You can only work with assessments for your own subjects.")
    return assessment


# Assessments -------------------------------------------------------------


@teaching_required
def assessment_list(request):
    assessments = Assessment.objects.select_related(
        "class_subject__school_class", "class_subject__subject", "term"
    )
    if request.user.is_teacher:
        assessments = assessments.filter(class_subject__teacher=request.user)
    return render(
        request,
        "results/assessment_list.html",
        {"assessments": assessments, "active": "assessments"},
    )


@teaching_required
def assessment_create(request):
    return form_view(
        request,
        form_class=AssessmentForm,
        template="results/assessment_form.html",
        title="New assessment",
        success_url="results:assessment_list",
        save_message="Assessment saved.",
        form_kwargs={"user": request.user},
        extra={"active": "assessments", "cancel_url": reverse("results:assessment_list")},
    )


@teaching_required
def assessment_edit(request, pk):
    assessment = _get_assessment(request, pk)
    return form_view(
        request,
        form_class=AssessmentForm,
        template="results/assessment_form.html",
        title="Edit assessment",
        instance=assessment,
        success_url="results:assessment_list",
        save_message="Assessment saved.",
        form_kwargs={"user": request.user},
        extra={"active": "assessments", "cancel_url": reverse("results:assessment_list")},
    )


@teaching_required
def assessment_delete(request, pk):
    assessment = _get_assessment(request, pk)
    return delete_view(
        request,
        obj=assessment,
        template="partials/_confirm_delete.html",
        success_url="results:assessment_list",
        success_message="Assessment deleted.",
        extra={"active": "assessments", "cancel_url": reverse("results:assessment_list")},
    )


# Score entry -------------------------------------------------------------


@teaching_required
def score_entry(request, pk):
    assessment = _get_assessment(request, pk)
    school_class = assessment.class_subject.school_class
    enrollments = Enrollment.objects.filter(
        school_class=school_class, term=assessment.term
    ).select_related("student")
    students = [enrollment.student for enrollment in enrollments]

    if request.method == "POST":
        errors = []
        parsed = {}
        for student in students:
            raw = (request.POST.get(f"value_{student.pk}") or "").strip()
            if raw == "":
                parsed[student.pk] = None
                continue
            try:
                value = Decimal(raw)
            except InvalidOperation:
                errors.append(f"'{raw}' is not a valid score for {student.full_name}.")
                continue
            if value < 0 or value > assessment.max_score:
                errors.append(
                    f"Score for {student.full_name} must be between 0 and {assessment.max_score}."
                )
                continue
            parsed[student.pk] = value

        if errors:
            for error in errors:
                messages.error(request, error)
            rows = [
                {
                    "student": student,
                    "value": request.POST.get(f"value_{student.pk}", ""),
                }
                for student in students
            ]
        else:
            for student in students:
                value = parsed[student.pk]
                existing = Score.objects.filter(assessment=assessment, student=student).first()
                if value is None:
                    if existing:
                        existing.delete()
                elif existing:
                    existing.value = value
                    existing.save()
                else:
                    Score.objects.create(assessment=assessment, student=student, value=value)
            messages.success(request, f"Scores saved for {assessment.name}.")
            return redirect("results:score_entry", pk=assessment.pk)
    else:
        existing = {score.student_id: score for score in Score.objects.filter(assessment=assessment)}
        rows = [
            {
                "student": student,
                "value": existing[student.pk].value if student.pk in existing else "",
            }
            for student in students
        ]

    return render(
        request,
        "results/score_entry.html",
        {
            "assessment": assessment,
            "rows": rows,
            "active": "assessments",
        },
    )


# Report cards ------------------------------------------------------------


@teaching_required
def report_card_select(request):
    term = _selected_term(request)
    enrollments = []
    if term:
        enrollments = (
            Enrollment.objects.filter(term=term)
            .select_related("student", "school_class")
            .order_by("student__last_name", "student__first_name")
        )
        if request.user.is_teacher:
            enrollments = enrollments.filter(school_class_id__in=_teacher_class_ids(request.user))
    return render(
        request,
        "results/report_card_select.html",
        {
            "terms": AcademicTerm.objects.all(),
            "selected_term": term,
            "enrollments": paginate(request, enrollments),
            "active": "report_cards",
        },
    )


def _report_context(request, student_pk, term_pk):
    student = get_object_or_404(Student, pk=student_pk)
    term = get_object_or_404(AcademicTerm, pk=term_pk)

    if request.user.is_teacher:
        enrolled_classes = set(
            Enrollment.objects.filter(student=student, term=term).values_list(
                "school_class_id", flat=True
            )
        )
        if not (enrolled_classes & _teacher_class_ids(request.user)):
            raise PermissionDenied("You can only view report cards for your own classes.")

    report = student_term_report(student, term)
    positions, class_size = term_positions(report["school_class"], term)
    return {
        "report": report,
        "position": positions.get(student.pk),
        "class_size": class_size,
    }


@teaching_required
def report_card(request, student_pk, term_pk):
    context = _report_context(request, student_pk, term_pk)
    context["active"] = "report_cards"
    return render(request, "results/report_card.html", context)


@teaching_required
@require_POST
def email_report(request, student_pk, term_pk):
    context = _report_context(request, student_pk, term_pk)
    queued = notify_results(
        context["report"]["student"],
        context["report"],
        position=context["position"],
        class_size=context["class_size"],
    )
    if queued:
        messages.success(request, f"Results queued for {queued} recipient(s).")
    else:
        messages.warning(
            request,
            "There are no email addresses on file for this student or their guardians.",
        )
    return redirect("results:report_card", student_pk=student_pk, term_pk=term_pk)


@teaching_required
def report_card_download(request, student_pk, term_pk):
    context = _report_context(request, student_pk, term_pk)
    report = context["report"]
    school = request.user.school or getattr(report["student"], "school", None)
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


# Online assessment authoring ---------------------------------------------


def _may_manage(user, assessment):
    return not user.is_teacher or assessment.class_subject.teacher_id == user.pk


def _require_manage(request, assessment):
    if not _may_manage(request.user, assessment):
        raise PermissionDenied("You can only work with assessments for your own subjects.")


def _questions_locked(assessment):
    """Questions freeze once a student has started, so scores cannot shift under them."""
    return assessment.submissions.exists()


def _locked_response(request, assessment):
    messages.error(
        request,
        "Students have already started this assessment, so its questions are locked. "
        "Reset their attempts first if you need to change it.",
    )
    return redirect("results:assessment_questions", pk=assessment.pk)


@teaching_required
def assessment_questions(request, pk):
    assessment = _get_assessment(request, pk)
    questions = list(assessment.questions.prefetch_related("choices"))
    return render(
        request,
        "results/assessment_questions.html",
        {
            "assessment": assessment,
            "objective": [q for q in questions if q.section == Question.Section.OBJECTIVE],
            "theory": [q for q in questions if q.section == Question.Section.THEORY],
            "submissions": assessment.submissions.select_related("student"),
            "locked": _questions_locked(assessment),
            "active": "assessments",
        },
    )


@teaching_required
def question_create(request, pk):
    assessment = _get_assessment(request, pk)
    if _questions_locked(assessment):
        return _locked_response(request, assessment)
    form = QuestionForm(request.POST or None, initial={"order": assessment.questions.count() + 1})
    if request.method == "POST" and form.is_valid():
        question = form.save(commit=False)
        question.assessment = assessment
        question.save()
        assessment.sync_max_score()
        messages.success(request, "Question added.")
        return redirect("results:assessment_questions", pk=assessment.pk)
    return render(
        request,
        "results/question_form.html",
        {
            "form": form,
            "assessment": assessment,
            "title": "Add question",
            "cancel_url": reverse("results:assessment_questions", args=[assessment.pk]),
            "active": "assessments",
        },
    )


@teaching_required
def question_edit(request, pk):
    question = get_object_or_404(
        Question.objects.select_related("assessment__class_subject"), pk=pk
    )
    _require_manage(request, question.assessment)
    if _questions_locked(question.assessment):
        return _locked_response(request, question.assessment)
    form = QuestionForm(request.POST or None, instance=question)
    if request.method == "POST" and form.is_valid():
        form.save()
        question.assessment.sync_max_score()
        messages.success(request, "Question saved.")
        return redirect("results:assessment_questions", pk=question.assessment_id)
    return render(
        request,
        "results/question_form.html",
        {
            "form": form,
            "assessment": question.assessment,
            "title": "Edit question",
            "cancel_url": reverse("results:assessment_questions", args=[question.assessment_id]),
            "active": "assessments",
        },
    )


@teaching_required
def question_delete(request, pk):
    question = get_object_or_404(
        Question.objects.select_related("assessment__class_subject"), pk=pk
    )
    _require_manage(request, question.assessment)
    if _questions_locked(question.assessment):
        return _locked_response(request, question.assessment)
    assessment = question.assessment
    return delete_view(
        request,
        obj=question,
        template="partials/_confirm_delete.html",
        success_url="results:assessment_questions",
        success_url_args=[assessment.pk],
        success_message="Question deleted.",
        extra={
            "active": "assessments",
            "cancel_url": reverse("results:assessment_questions", args=[assessment.pk]),
        },
    )


@teaching_required
def choice_create(request, pk):
    question = get_object_or_404(
        Question.objects.select_related("assessment__class_subject"), pk=pk
    )
    _require_manage(request, question.assessment)
    if not question.is_objective:
        messages.error(request, "Only objective questions have answer options.")
        return redirect("results:assessment_questions", pk=question.assessment_id)
    if _questions_locked(question.assessment):
        return _locked_response(request, question.assessment)
    form = ChoiceForm(
        request.POST or None, initial={"order": question.choices.count() + 1}
    )
    if request.method == "POST" and form.is_valid():
        choice = form.save(commit=False)
        choice.question = question
        choice.save()
        messages.success(request, "Option added.")
        return redirect("results:assessment_questions", pk=question.assessment_id)
    return render(
        request,
        "results/choice_form.html",
        {
            "form": form,
            "question": question,
            "title": "Add option",
            "cancel_url": reverse("results:assessment_questions", args=[question.assessment_id]),
            "active": "assessments",
        },
    )


@teaching_required
def choice_delete(request, pk):
    choice = get_object_or_404(
        Choice.objects.select_related("question__assessment__class_subject"), pk=pk
    )
    _require_manage(request, choice.question.assessment)
    if _questions_locked(choice.question.assessment):
        return _locked_response(request, choice.question.assessment)
    assessment_pk = choice.question.assessment_id
    return delete_view(
        request,
        obj=choice,
        template="partials/_confirm_delete.html",
        success_url="results:assessment_questions",
        success_url_args=[assessment_pk],
        success_message="Option deleted.",
        extra={
            "active": "assessments",
            "cancel_url": reverse("results:assessment_questions", args=[assessment_pk]),
        },
    )


@teaching_required
@require_POST
def assessment_publish(request, pk):
    assessment = _get_assessment(request, pk)
    was_published = assessment.is_published
    assessment.is_published = not assessment.is_published
    assessment.save(update_fields=["is_published"])
    if assessment.is_published and not was_published:
        queued = notify_assessment_published(assessment)
        if queued:
            messages.success(request, f"Assessment published and {queued} notification(s) queued.")
            return redirect("results:assessment_questions", pk=assessment.pk)
    messages.success(request, "Assessment published." if assessment.is_published else "Assessment unpublished.")
    return redirect("results:assessment_questions", pk=assessment.pk)


# Submissions -------------------------------------------------------------


@teaching_required
def submission_list(request, pk):
    assessment = _get_assessment(request, pk)
    submissions = {s.student_id: s for s in assessment.submissions.select_related("student")}
    students = [
        enrollment.student
        for enrollment in Enrollment.objects.filter(
            school_class=assessment.class_subject.school_class, term=assessment.term
        ).select_related("student")
    ]
    rows = [{"student": student, "submission": submissions.get(student.pk)} for student in students]
    return render(
        request,
        "results/submission_list.html",
        {"assessment": assessment, "rows": rows, "active": "assessments"},
    )


@teaching_required
def submission_mark(request, pk):
    submission = get_object_or_404(
        Submission.objects.select_related("assessment__class_subject", "student"), pk=pk
    )
    _require_manage(request, submission.assessment)
    theory_answers = list(
        submission.answers.filter(question__section=Question.Section.THEORY).select_related(
            "question"
        )
    )

    if request.method == "POST":
        errors = []
        for answer in theory_answers:
            raw = (request.POST.get(f"points_{answer.pk}") or "").strip()
            if raw == "":
                answer.awarded_points = None
                answer.save(update_fields=["awarded_points"])
                continue
            try:
                value = Decimal(raw)
            except InvalidOperation:
                errors.append(f"'{raw}' is not a valid mark.")
                continue
            if value < 0 or value > answer.question.points:
                errors.append(
                    f"Mark for question {answer.question.order} must be between 0 and {answer.question.points}."
                )
                continue
            answer.awarded_points = value
            answer.save(update_fields=["awarded_points"])

        if errors:
            for error in errors:
                messages.error(request, error)
        else:
            finalize_submission(submission)
            messages.success(request, "Theory answers marked.")
            return redirect("results:submission_list", pk=submission.assessment_id)

    return render(
        request,
        "results/submission_mark.html",
        {"submission": submission, "theory_answers": theory_answers, "active": "assessments"},
    )


@teaching_required
@require_POST
def submission_reset(request, pk):
    submission = get_object_or_404(Submission.objects.select_related("assessment"), pk=pk)
    _require_manage(request, submission.assessment)
    assessment_pk = submission.assessment_id
    Score.objects.filter(assessment_id=assessment_pk, student_id=submission.student_id).delete()
    submission.delete()
    messages.success(request, "Attempt reset. The student can sit it again.")
    return redirect("results:submission_list", pk=assessment_pk)
