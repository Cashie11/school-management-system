from django import forms

from .models import SupportMessage


class SupportMessageForm(forms.ModelForm):
    """The public support form.

    ``website`` is a honeypot: it is hidden from people and left empty by them,
    so anything in it came from a bot. The view discards those submissions.
    """

    website = forms.CharField(
        required=False,
        label="Website",
        widget=forms.TextInput(attrs={"autocomplete": "off", "tabindex": "-1"}),
    )

    class Meta:
        model = SupportMessage
        fields = ["name", "email", "subject", "body"]
        widgets = {
            "body": forms.Textarea(attrs={"rows": 7}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["name"].widget.attrs.update({"autocomplete": "name"})
        self.fields["email"].widget.attrs.update({"autocomplete": "email"})
        self.fields["name"].label = "Your name"
        self.fields["subject"].label = "Subject"
        self.fields["body"].label = "How can we help?"
        self.fields["body"].help_text = (
            "Include the page you were on and what you expected to happen."
        )

    def clean_body(self):
        body = (self.cleaned_data.get("body") or "").strip()
        if len(body) < 10:
            raise forms.ValidationError("Please describe the problem in a little more detail.")
        if len(body) > 5000:
            raise forms.ValidationError("Please keep the message under 5000 characters.")
        return body
