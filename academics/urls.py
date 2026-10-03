from django.urls import path

from . import views

app_name = "academics"

urlpatterns = [
    path("terms/", views.term_list, name="term_list"),
    path("terms/new/", views.term_create, name="term_create"),
    path("terms/<int:pk>/edit/", views.term_edit, name="term_edit"),
    path("terms/<int:pk>/delete/", views.term_delete, name="term_delete"),
    path("subjects/", views.subject_list, name="subject_list"),
    path("subjects/new/", views.subject_create, name="subject_create"),
    path("subjects/<int:pk>/edit/", views.subject_edit, name="subject_edit"),
    path("subjects/<int:pk>/delete/", views.subject_delete, name="subject_delete"),
    path("classes/", views.class_list, name="class_list"),
    path("classes/new/", views.class_create, name="class_create"),
    path("classes/<int:pk>/edit/", views.class_edit, name="class_edit"),
    path("classes/<int:pk>/delete/", views.class_delete, name="class_delete"),
    path("assignments/", views.assignment_list, name="assignment_list"),
    path("assignments/new/", views.assignment_create, name="assignment_create"),
    path("assignments/<int:pk>/edit/", views.assignment_edit, name="assignment_edit"),
    path("assignments/<int:pk>/delete/", views.assignment_delete, name="assignment_delete"),
]
