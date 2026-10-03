from django.db.models import Count
from django.shortcuts import get_object_or_404, render
from django.urls import reverse

from core.crud import delete_view, form_view
from core.permissions import management_required

from .forms import AcademicTermForm, ClassSubjectForm, SchoolClassForm, SubjectForm
from .models import AcademicTerm, ClassSubject, SchoolClass, Subject

# Terms -------------------------------------------------------------------


@management_required
def term_list(request):
    terms = AcademicTerm.objects.all()
    return render(request, "academics/term_list.html", {"terms": terms, "active": "terms"})


@management_required
def term_create(request):
    return form_view(
        request,
        form_class=AcademicTermForm,
        template="academics/term_form.html",
        title="New term",
        success_url="academics:term_list",
        save_message="Term saved.",
        extra={"active": "terms", "cancel_url": reverse("academics:term_list")},
    )


@management_required
def term_edit(request, pk):
    term = get_object_or_404(AcademicTerm, pk=pk)
    return form_view(
        request,
        form_class=AcademicTermForm,
        template="academics/term_form.html",
        title="Edit term",
        instance=term,
        success_url="academics:term_list",
        save_message="Term saved.",
        extra={"active": "terms", "cancel_url": reverse("academics:term_list")},
    )


@management_required
def term_delete(request, pk):
    term = get_object_or_404(AcademicTerm, pk=pk)
    return delete_view(
        request,
        obj=term,
        template="partials/_confirm_delete.html",
        success_url="academics:term_list",
        success_message="Term deleted.",
        extra={"active": "terms", "cancel_url": reverse("academics:term_list")},
    )


# Subjects ----------------------------------------------------------------


@management_required
def subject_list(request):
    subjects = Subject.objects.all()
    return render(request, "academics/subject_list.html", {"subjects": subjects, "active": "subjects"})


@management_required
def subject_create(request):
    return form_view(
        request,
        form_class=SubjectForm,
        template="academics/subject_form.html",
        title="New subject",
        success_url="academics:subject_list",
        save_message="Subject saved.",
        extra={"active": "subjects", "cancel_url": reverse("academics:subject_list")},
    )


@management_required
def subject_edit(request, pk):
    subject = get_object_or_404(Subject, pk=pk)
    return form_view(
        request,
        form_class=SubjectForm,
        template="academics/subject_form.html",
        title="Edit subject",
        instance=subject,
        success_url="academics:subject_list",
        save_message="Subject saved.",
        extra={"active": "subjects", "cancel_url": reverse("academics:subject_list")},
    )


@management_required
def subject_delete(request, pk):
    subject = get_object_or_404(Subject, pk=pk)
    return delete_view(
        request,
        obj=subject,
        template="partials/_confirm_delete.html",
        success_url="academics:subject_list",
        success_message="Subject deleted.",
        extra={"active": "subjects", "cancel_url": reverse("academics:subject_list")},
    )


# Classes -----------------------------------------------------------------


@management_required
def class_list(request):
    classes = SchoolClass.objects.annotate(subject_count=Count("class_subjects"))
    return render(request, "academics/class_list.html", {"classes": classes, "active": "classes"})


@management_required
def class_create(request):
    return form_view(
        request,
        form_class=SchoolClassForm,
        template="academics/class_form.html",
        title="New class",
        success_url="academics:class_list",
        save_message="Class saved.",
        extra={"active": "classes", "cancel_url": reverse("academics:class_list")},
    )


@management_required
def class_edit(request, pk):
    school_class = get_object_or_404(SchoolClass, pk=pk)
    return form_view(
        request,
        form_class=SchoolClassForm,
        template="academics/class_form.html",
        title="Edit class",
        instance=school_class,
        success_url="academics:class_list",
        save_message="Class saved.",
        extra={"active": "classes", "cancel_url": reverse("academics:class_list")},
    )


@management_required
def class_delete(request, pk):
    school_class = get_object_or_404(SchoolClass, pk=pk)
    return delete_view(
        request,
        obj=school_class,
        template="partials/_confirm_delete.html",
        success_url="academics:class_list",
        success_message="Class deleted.",
        extra={"active": "classes", "cancel_url": reverse("academics:class_list")},
    )


# Teacher assignments -----------------------------------------------------


@management_required
def assignment_list(request):
    assignments = ClassSubject.objects.select_related("school_class", "subject", "teacher")
    return render(
        request,
        "academics/assignment_list.html",
        {"assignments": assignments, "active": "assignments"},
    )


@management_required
def assignment_create(request):
    return form_view(
        request,
        form_class=ClassSubjectForm,
        template="academics/assignment_form.html",
        title="New teacher assignment",
        success_url="academics:assignment_list",
        save_message="Assignment saved.",
        extra={"active": "assignments", "cancel_url": reverse("academics:assignment_list")},
    )


@management_required
def assignment_edit(request, pk):
    assignment = get_object_or_404(ClassSubject, pk=pk)
    return form_view(
        request,
        form_class=ClassSubjectForm,
        template="academics/assignment_form.html",
        title="Edit teacher assignment",
        instance=assignment,
        success_url="academics:assignment_list",
        save_message="Assignment saved.",
        extra={"active": "assignments", "cancel_url": reverse("academics:assignment_list")},
    )


@management_required
def assignment_delete(request, pk):
    assignment = get_object_or_404(ClassSubject, pk=pk)
    return delete_view(
        request,
        obj=assignment,
        template="partials/_confirm_delete.html",
        success_url="academics:assignment_list",
        success_message="Assignment deleted.",
        extra={"active": "assignments", "cancel_url": reverse("academics:assignment_list")},
    )
