from django import forms
from django.contrib.auth import get_user_model

from core.forms import TenantModelForm
from tenancy.context import get_current_school_id

from .models import DisciplineRecord, Enrollment, Guardian, Student

User = get_user_model()


class StudentForm(TenantModelForm):
    class Meta:
        model = Student
        fields = (
            "admission_number",
            "first_name",
            "last_name",
            "email",
            "date_of_birth",
            "gender",
            "is_active",
        )
        widgets = {"date_of_birth": forms.DateInput(attrs={"type": "date"})}


class DisciplineForm(TenantModelForm):
    class Meta:
        model = DisciplineRecord
        fields = ("student", "kind", "reason", "start_date", "end_date")
        widgets = {
            "start_date": forms.DateInput(attrs={"type": "date"}),
            "end_date": forms.DateInput(attrs={"type": "date"}),
        }


class EnrollmentForm(TenantModelForm):
    class Meta:
        model = Enrollment
        fields = ("student", "school_class", "term")

    def clean(self):
        cleaned = super().clean()
        student = cleaned.get("student")
        term = cleaned.get("term")
        if student and term:
            existing = Enrollment.objects.filter(student=student, term=term)
            if self.instance.pk:
                existing = existing.exclude(pk=self.instance.pk)
            if existing.exists():
                raise forms.ValidationError(
                    "This student is already enrolled for the selected term."
                )
        return cleaned


class GuardianForm(TenantModelForm):
    class Meta:
        model = Guardian
        fields = ("student", "user", "relationship", "is_primary")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        school_id = get_current_school_id()
        # User is not tenant-scoped, so the parent list is filtered explicitly.
        self.fields["user"].queryset = User.objects.filter(
            school_id=school_id, role=User.Role.PARENT_STUDENT
        ).order_by("first_name", "last_name", "email")
        self.fields["user"].label = "Parent account"
        self.fields["user"].empty_label = "Select a parent account"

    def clean(self):
        cleaned = super().clean()
        student = cleaned.get("student")
        user = cleaned.get("user")
        if student and user:
            existing = Guardian.objects.filter(student=student, user=user)
            if self.instance.pk:
                existing = existing.exclude(pk=self.instance.pk)
            if existing.exists():
                raise forms.ValidationError("That account is already linked to this student.")
        return cleaned
