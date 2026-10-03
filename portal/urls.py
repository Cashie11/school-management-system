from django.urls import path

from . import views

app_name = "portal"

urlpatterns = [
    path("", views.home, name="home"),
    path("students/<int:pk>/exams/", views.student_exams, name="student_exams"),
    path(
        "students/<int:pk>/exams/<int:assessment_pk>/",
        views.exam_take,
        name="exam_take",
    ),
    path(
        "students/<int:pk>/exams/<int:assessment_pk>/result/",
        views.exam_result,
        name="exam_result",
    ),
    path("students/<int:pk>/results/", views.student_results, name="student_results"),
    path(
        "students/<int:pk>/results/<int:term_pk>/pdf/",
        views.student_report_pdf,
        name="student_report_pdf",
    ),
    path("students/<int:pk>/attendance/", views.student_attendance, name="student_attendance"),
]
