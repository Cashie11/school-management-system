from django import forms

from core.forms import TenantModelForm

from .models import Assessment, Choice, Question
from .scoping import available_class_subjects


class AssessmentForm(TenantModelForm):
    class Meta:
        model = Assessment
        fields = (
            "class_subject",
            "term",
            "name",
            "mode",
            "max_score",
            "date",
            "duration_minutes",
            "available_from",
            "available_until",
        )
        widgets = {
            "date": forms.DateInput(attrs={"type": "date"}),
            "available_from": forms.DateTimeInput(
                attrs={"type": "datetime-local"}, format="%Y-%m-%dT%H:%M"
            ),
            "available_until": forms.DateTimeInput(
                attrs={"type": "datetime-local"}, format="%Y-%m-%dT%H:%M"
            ),
        }

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user
        self.fields["available_from"].input_formats = ["%Y-%m-%dT%H:%M"]
        self.fields["available_until"].input_formats = ["%Y-%m-%dT%H:%M"]
        self.fields["max_score"].help_text = "Ignored for online assessments, where it is the total question points."
        if user is not None:
            self.fields["class_subject"].queryset = available_class_subjects(user)

    def clean(self):
        cleaned = super().clean()
        opens = cleaned.get("available_from")
        closes = cleaned.get("available_until")
        if opens and closes and opens >= closes:
            self.add_error("available_until", "The closing time must be after the opening time.")
        duration = cleaned.get("duration_minutes")
        if duration is not None and duration < 1:
            self.add_error("duration_minutes", "The time limit must be at least 1 minute.")
        return cleaned


class QuestionForm(TenantModelForm):
    class Meta:
        model = Question
        fields = ("section", "text", "points", "order")


class ChoiceForm(TenantModelForm):
    class Meta:
        model = Choice
        fields = ("text", "is_correct", "order")
