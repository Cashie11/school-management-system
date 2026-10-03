from django import forms
from django.contrib.auth import get_user_model

from core.forms import TenantModelForm
from tenancy.context import get_current_school_id

from .models import AcademicTerm, ClassSubject, SchoolClass, Subject

User = get_user_model()


class AcademicTermForm(TenantModelForm):
    class Meta:
        model = AcademicTerm
        fields = ("name", "start_date", "end_date", "is_current")
        widgets = {
            "start_date": forms.DateInput(attrs={"type": "date"}),
            "end_date": forms.DateInput(attrs={"type": "date"}),
        }

    def save(self, commit=True):
        instance = super().save(commit=False)
        if instance.is_current and instance.school_id:
            AcademicTerm.objects.filter(is_current=True).exclude(pk=instance.pk).update(is_current=False)
        elif instance.is_current and not instance.school_id:
            # The instance school is assigned on save; clear within the active school.
            AcademicTerm.objects.filter(is_current=True).update(is_current=False)
        if commit:
            instance.save()
            self.save_m2m()
        return instance


class SubjectForm(TenantModelForm):
    class Meta:
        model = Subject
        fields = ("name", "code")


class SchoolClassForm(TenantModelForm):
    class Meta:
        model = SchoolClass
        fields = ("name", "level")


class ClassSubjectForm(TenantModelForm):
    class Meta:
        model = ClassSubject
        fields = ("school_class", "subject", "teacher")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        school_id = get_current_school_id()
        # User is not tenant-scoped, so the teacher list must be filtered explicitly.
        self.fields["teacher"].queryset = User.objects.filter(
            school_id=school_id, role=User.Role.TEACHER
        ).order_by("first_name", "last_name", "email")
        self.fields["teacher"].required = False
        self.fields["teacher"].empty_label = "Unassigned"
