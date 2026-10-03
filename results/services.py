from decimal import ROUND_HALF_UP, Decimal
from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from academics.models import ClassSubject
from students.models import Enrollment

from .grading import grade_for
from .models import Assessment, Score

INK = colors.HexColor("#29303d")
DARK = colors.HexColor("#2c2c2c")
SURFACE = colors.HexColor("#ecebe8")
ACCENT = colors.HexColor("#e6fb2d")
MUTED = colors.HexColor("#8a8f98")


def _percent(obtained, possible):
    if not possible:
        return None
    value = (obtained / possible) * Decimal("100")
    return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def student_term_report(student, term):
    """Aggregate a student's scores for one term into subject rows and an overall result."""
    enrollment = (
        Enrollment.objects.filter(student=student, term=term).select_related("school_class").first()
    )
    school_class = enrollment.school_class if enrollment else None

    class_subjects = []
    if school_class:
        class_subjects = list(
            ClassSubject.objects.filter(school_class=school_class).select_related("subject")
        )

    subjects = []
    total_obtained = Decimal("0")
    total_possible = Decimal("0")

    for class_subject in class_subjects:
        assessments = list(
            Assessment.objects.filter(class_subject=class_subject, term=term).order_by("name")
        )
        scores = []
        obtained = Decimal("0")
        possible = Decimal("0")
        for assessment in assessments:
            score = Score.objects.filter(assessment=assessment, student=student).first()
            value = score.value if score else None
            scores.append({"assessment": assessment, "value": value})
            if value is not None:
                obtained += value
                possible += assessment.max_score

        percentage = _percent(obtained, possible)
        subjects.append(
            {
                "subject": class_subject.subject,
                "scores": scores,
                "obtained": obtained,
                "possible": possible,
                "percentage": percentage,
                "grade": grade_for(percentage),
            }
        )
        total_obtained += obtained
        total_possible += possible

    overall = _percent(total_obtained, total_possible)
    return {
        "student": student,
        "term": term,
        "school_class": school_class,
        "subjects": subjects,
        "total_obtained": total_obtained,
        "total_possible": total_possible,
        "overall": overall,
        "grade": grade_for(overall),
    }


def term_positions(school_class, term):
    """Return (position_by_student_id, class_size) ranked by overall percentage.

    Computed in bulk: one query for the class, one for its assessments and one for
    the scores, rather than a full report per student.
    """
    if school_class is None:
        return {}, 0

    enrollments = list(
        Enrollment.objects.filter(school_class=school_class, term=term).select_related("student")
    )
    if not enrollments:
        return {}, 0

    student_ids = [enrollment.student_id for enrollment in enrollments]
    assessments = list(
        Assessment.objects.filter(class_subject__school_class=school_class, term=term)
    )
    max_by_assessment = {assessment.pk: assessment.max_score for assessment in assessments}

    totals = {student_id: [Decimal("0"), Decimal("0")] for student_id in student_ids}
    if max_by_assessment:
        rows = Score.objects.filter(
            assessment_id__in=list(max_by_assessment), student_id__in=student_ids
        ).values("assessment_id", "student_id", "value")
        for row in rows:
            if row["value"] is None:
                continue
            bucket = totals.get(row["student_id"])
            if bucket is None:
                continue
            bucket[0] += row["value"]
            bucket[1] += max_by_assessment[row["assessment_id"]]

    overalls = {}
    for student_id, (obtained, possible) in totals.items():
        percentage = _percent(obtained, possible)
        if percentage is not None:
            overalls[student_id] = percentage

    ordered = sorted(overalls.items(), key=lambda item: item[1], reverse=True)
    positions = {student_id: index + 1 for index, (student_id, _) in enumerate(ordered)}
    return positions, len(enrollments)


def _format(value):
    if value is None:
        return "-"
    return f"{value:.2f}".rstrip("0").rstrip(".")


def report_card_pdf(report, school_name, position=None, class_size=None):
    """Build a report card PDF and return the bytes."""
    buffer = BytesIO()
    document = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=2 * cm,
        rightMargin=2 * cm,
        topMargin=2 * cm,
        bottomMargin=2 * cm,
        title="Report card",
    )
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "Title", parent=styles["Title"], fontName="Helvetica-Bold", fontSize=18, textColor=INK
    )
    meta_style = ParagraphStyle("Meta", parent=styles["Normal"], fontSize=10, textColor=INK)

    story = [
        Paragraph(school_name, title_style),
        Paragraph("Student report card", meta_style),
        Spacer(1, 0.6 * cm),
    ]

    student = report["student"]
    school_class = report["school_class"]
    info = [
        ["Student", student.full_name, "Admission number", student.admission_number],
        [
            "Class",
            str(school_class) if school_class else "-",
            "Term",
            str(report["term"]),
        ],
    ]
    info_table = Table(info, colWidths=[3 * cm, 5.5 * cm, 3.2 * cm, 5.3 * cm])
    info_table.setStyle(
        TableStyle(
            [
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("TEXTCOLOR", (0, 0), (0, -1), MUTED),
                ("TEXTCOLOR", (2, 0), (2, -1), MUTED),
                ("FONTNAME", (1, 0), (1, -1), "Helvetica-Bold"),
                ("FONTNAME", (3, 0), (3, -1), "Helvetica-Bold"),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    story.append(info_table)
    story.append(Spacer(1, 0.8 * cm))

    rows = [["Subject", "Score", "Out of", "Percentage", "Grade"]]
    for subject in report["subjects"]:
        rows.append(
            [
                str(subject["subject"]),
                _format(subject["obtained"]),
                _format(subject["possible"]),
                _format(subject["percentage"]) + "%" if subject["percentage"] is not None else "-",
                subject["grade"][0] if subject["grade"] else "-",
            ]
        )

    if len(rows) == 1:
        rows.append(["No scores recorded", "-", "-", "-", "-"])

    table = Table(rows, colWidths=[6 * cm, 2.6 * cm, 2.6 * cm, 3 * cm, 2.8 * cm])
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), DARK),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 10),
                ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, SURFACE]),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#d9d9d4")),
            ]
        )
    )
    story.append(table)
    story.append(Spacer(1, 0.8 * cm))

    overall = report["overall"]
    summary = [
        ["Overall", "Total score", "Percentage", "Grade", "Position"],
        [
            _format(overall) + "%" if overall is not None else "-",
            f"{_format(report['total_obtained'])} / {_format(report['total_possible'])}",
            _format(overall) + "%" if overall is not None else "-",
            report["grade"][0] if report["grade"] else "-",
            f"{position} of {class_size}" if position and class_size else "-",
        ],
    ]
    summary_table = Table(summary, colWidths=[3.2 * cm, 4 * cm, 3 * cm, 2.8 * cm, 3 * cm])
    summary_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), ACCENT),
                ("TEXTCOLOR", (0, 0), (-1, 0), INK),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
                ("FONTSIZE", (0, 0), (-1, -1), 10),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#d9d9d4")),
            ]
        )
    )
    story.append(summary_table)

    document.build(story)
    return buffer.getvalue()
