from django.urls import path

from . import views

app_name = "results"

urlpatterns = [
    path("assessments/", views.assessment_list, name="assessment_list"),
    path("assessments/new/", views.assessment_create, name="assessment_create"),
    path("assessments/<int:pk>/edit/", views.assessment_edit, name="assessment_edit"),
    path("assessments/<int:pk>/delete/", views.assessment_delete, name="assessment_delete"),
    path("assessments/<int:pk>/scores/", views.score_entry, name="score_entry"),
    path("assessments/<int:pk>/questions/", views.assessment_questions, name="assessment_questions"),
    path("assessments/<int:pk>/questions/new/", views.question_create, name="question_create"),
    path("assessments/<int:pk>/publish/", views.assessment_publish, name="assessment_publish"),
    path("assessments/<int:pk>/submissions/", views.submission_list, name="submission_list"),
    path("questions/<int:pk>/edit/", views.question_edit, name="question_edit"),
    path("questions/<int:pk>/delete/", views.question_delete, name="question_delete"),
    path("questions/<int:pk>/choices/new/", views.choice_create, name="choice_create"),
    path("choices/<int:pk>/delete/", views.choice_delete, name="choice_delete"),
    path("submissions/<int:pk>/mark/", views.submission_mark, name="submission_mark"),
    path("submissions/<int:pk>/reset/", views.submission_reset, name="submission_reset"),
    path("report-cards/", views.report_card_select, name="report_card_select"),
    path("report-cards/<int:student_pk>/<int:term_pk>/", views.report_card, name="report_card"),
    path(
        "report-cards/<int:student_pk>/<int:term_pk>/email/",
        views.email_report,
        name="email_report",
    ),
    path(
        "report-cards/<int:student_pk>/<int:term_pk>/pdf/",
        views.report_card_download,
        name="report_card_download",
    ),
]
