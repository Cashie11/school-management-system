from django import forms

from academics.selectors import classes_for
from core.forms import TenantModelForm

from .models import Announcement


class AnnouncementForm(TenantModelForm):
    class Meta:
        model = Announcement
        fields = ("audience", "school_class", "title", "body", "is_pinned", "expires_at")
        widgets = {
            "expires_at": forms.DateTimeInput(
                attrs={"type": "datetime-local"}, format="%Y-%m-%dT%H:%M"
            ),
        }

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user
        self.fields["expires_at"].input_formats = ["%Y-%m-%dT%H:%M"]
        self.fields["expires_at"].help_text = "Optional. The notice stops being shown after this time."
        self.fields["is_pinned"].help_text = "Pinned notices appear at the top."
        self.fields["school_class"].label = "Class"
        self.fields["school_class"].required = False
        self.fields["school_class"].help_text = "Optional. Target one class instead of the whole school."

        if user is not None and user.is_teacher:
            # Teachers address their own classes only.
            self.fields["school_class"].queryset = classes_for(user)
            self.fields["school_class"].required = True
            self.fields["school_class"].help_text = "Choose the class this notice is for."
            self.fields["audience"].choices = [
                (Announcement.Audience.STUDENTS, "Families of this class")
            ]

    def clean(self):
        cleaned = super().clean()
        audience = cleaned.get("audience")
        school_class = cleaned.get("school_class")
        if audience == Announcement.Audience.STUDENTS and school_class is None:
            # Allowed for admins: a school-wide notice for families.
            pass
        if self.user is not None and self.user.is_teacher and school_class is None:
            self.add_error("school_class", "Choose the class this notice is for.")
        return cleaned
