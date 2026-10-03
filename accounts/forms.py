from django import forms
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError

from core.forms import TenantModelForm
from students.models import Guardian, Student
from tenancy.models import School
from tenancy.validators import validate_logo

from .models import User
from .services import register_school


class EmailAuthenticationForm(AuthenticationForm):
    username = forms.EmailField(
        label="Email",
        widget=forms.EmailInput(attrs={"autofocus": True, "autocomplete": "email"}),
    )

    error_messages = {
        **AuthenticationForm.error_messages,
        "invalid_login": "Enter a correct email address and password.",
    }

    def confirm_login_allowed(self, user):
        if user.removed_at is not None:
            raise ValidationError(
                "This account was removed. Contact your school administrator.",
                code="removed",
            )
        if not user.is_active:
            raise ValidationError(
                "This account has been suspended. Contact your school administrator.",
                code="suspended",
            )


class SchoolSignupForm(forms.Form):
    school_name = forms.CharField(max_length=180, label="School name")
    school_email = forms.EmailField(label="School contact email")
    admin_email = forms.EmailField(label="Administrator email")
    password1 = forms.CharField(label="Password", widget=forms.PasswordInput)
    password2 = forms.CharField(label="Confirm password", widget=forms.PasswordInput)
    logo = forms.ImageField(
        label="School logo",
        required=False,
        validators=[validate_logo],
        help_text="PNG, JPEG or WEBP. A square image works best. At least 64 x 64 pixels, 2 MB or smaller.",
        widget=forms.ClearableFileInput(attrs={"accept": "image/png,image/jpeg,image/webp"}),
    )

    def clean_admin_email(self):
        email = User.objects.normalize_email(self.cleaned_data["admin_email"])
        if User.objects.filter(email__iexact=email).exists():
            raise ValidationError("An account with this email already exists.")
        return email

    def clean_password1(self):
        return validate_password_field(self.cleaned_data.get("password1"))

    def clean(self):
        cleaned = super().clean()
        password1 = cleaned.get("password1")
        password2 = cleaned.get("password2")
        if password1 and password2 and password1 != password2:
            self.add_error("password2", "The two passwords do not match.")
        return cleaned

    def save(self):
        return register_school(
            school_name=self.cleaned_data["school_name"],
            school_email=self.cleaned_data["school_email"],
            admin_email=self.cleaned_data["admin_email"],
            password=self.cleaned_data["password1"],
            logo=self.cleaned_data.get("logo"),
        )


def validate_password_field(password):
    if password:
        try:
            validate_password(password)
        except ValidationError as error:
            raise ValidationError(error.messages)
    return password


class SchoolProfileForm(forms.ModelForm):
    """A School Admin editing their own school's name, contact email and logo."""

    class Meta:
        model = School
        fields = ("name", "email", "logo")
        widgets = {
            "logo": forms.ClearableFileInput(
                attrs={"accept": "image/png,image/jpeg,image/webp"}
            )
        }


class StaffCreateForm(forms.ModelForm):
    """Create a School Admin or Teacher account in the active school."""

    password1 = forms.CharField(label="Password", widget=forms.PasswordInput)
    password2 = forms.CharField(label="Confirm password", widget=forms.PasswordInput)

    class Meta:
        model = User
        fields = ("first_name", "last_name", "email", "role")

    def __init__(self, *args, school=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.school = school
        self.fields["role"].choices = [
            (User.Role.SCHOOL_ADMIN, "School Admin"),
            (User.Role.TEACHER, "Teacher"),
        ]

    def clean_email(self):
        email = User.objects.normalize_email(self.cleaned_data["email"])
        if User.objects.filter(email__iexact=email, removed_at__isnull=True).exists():
            raise ValidationError("An account with this email already exists.")
        return email

    def clean_password1(self):
        return validate_password_field(self.cleaned_data.get("password1"))

    def clean(self):
        cleaned = super().clean()
        password1 = cleaned.get("password1")
        password2 = cleaned.get("password2")
        if password1 and password2 and password1 != password2:
            self.add_error("password2", "The two passwords do not match.")
        return cleaned

    def validate_unique(self):
        email = self.cleaned_data.get("email")
        if email and User.objects.filter(email__iexact=email, removed_at__isnull=False).exists():
            # A removed account is restored, so the email is not a conflict.
            return
        super().validate_unique()

    def save(self, commit=True):
        email = self.cleaned_data["email"]
        # An account that was removed can be restored rather than recreated.
        removed = User.objects.filter(email__iexact=email, removed_at__isnull=False).first()
        if removed is not None:
            removed.removed_at = None
            removed.is_active = True
            removed.school = self.school
            removed.role = self.cleaned_data["role"]
            removed.first_name = self.cleaned_data["first_name"]
            removed.last_name = self.cleaned_data["last_name"]
            removed.set_password(self.cleaned_data["password1"])
            if commit:
                removed.save()
            return removed

        user = super().save(commit=False)
        user.school = self.school
        user.set_password(self.cleaned_data["password1"])
        if commit:
            user.save()
        return user


class ParentCreateForm(TenantModelForm):
    """Create a Parent/Student account and link it to a student in one step."""

    student = forms.ModelChoiceField(queryset=Student.objects.none(), label="Student")
    relationship = forms.CharField(max_length=40, required=False)
    is_primary = forms.BooleanField(required=False, initial=True, label="Primary guardian")
    password1 = forms.CharField(label="Password", widget=forms.PasswordInput)
    password2 = forms.CharField(label="Confirm password", widget=forms.PasswordInput)

    class Meta:
        model = User
        fields = ("first_name", "last_name", "email")

    def __init__(self, *args, school=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.school = school

    def clean_email(self):
        email = User.objects.normalize_email(self.cleaned_data["email"])
        if User.objects.filter(email__iexact=email, removed_at__isnull=True).exists():
            raise ValidationError("An account with this email already exists.")
        return email

    def clean_password1(self):
        return validate_password_field(self.cleaned_data.get("password1"))

    def clean(self):
        cleaned = super().clean()
        password1 = cleaned.get("password1")
        password2 = cleaned.get("password2")
        if password1 and password2 and password1 != password2:
            self.add_error("password2", "The two passwords do not match.")
        return cleaned

    def validate_unique(self):
        email = self.cleaned_data.get("email")
        if email and User.objects.filter(email__iexact=email, removed_at__isnull=False).exists():
            # A removed account is restored, so the email is not a conflict.
            return
        super().validate_unique()

    def save(self, commit=True):
        email = self.cleaned_data["email"]
        removed = User.objects.filter(email__iexact=email, removed_at__isnull=False).first()
        if removed is not None:
            user = removed
            user.removed_at = None
            user.is_active = True
        else:
            user = super().save(commit=False)

        user.school = self.school
        user.role = User.Role.PARENT_STUDENT
        user.first_name = self.cleaned_data["first_name"]
        user.last_name = self.cleaned_data["last_name"]
        user.set_password(self.cleaned_data["password1"])

        if not commit:
            return user
        user.save()

        Guardian.objects.filter(user=user).delete()
        Guardian.objects.create(
            user=user,
            student=self.cleaned_data["student"],
            relationship=self.cleaned_data["relationship"],
            is_primary=self.cleaned_data["is_primary"],
        )
        return user
