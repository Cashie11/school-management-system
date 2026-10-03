from django.db import models
from django.utils.text import slugify

from .context import get_current_school_id
from .validators import validate_logo


class School(models.Model):
    name = models.CharField(max_length=180)
    slug = models.SlugField(max_length=190, unique=True)
    email = models.EmailField()
    logo = models.ImageField(upload_to="school-logos/", blank=True, validators=[validate_logo])
    created_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class TenantQuerySet(models.QuerySet):
    def for_school(self, school):
        school_id = getattr(school, "pk", school)
        return self.filter(school_id=school_id)


class TenantManager(models.Manager.from_queryset(TenantQuerySet)):
    def get_queryset(self):
        queryset = super().get_queryset()
        school_id = get_current_school_id()
        if school_id is None:
            return queryset.none()
        return queryset.filter(school_id=school_id)


class TenantModel(models.Model):
    school = models.ForeignKey(School, on_delete=models.CASCADE)

    objects = TenantManager()
    # Unscoped manager. Reserved for platform administration, where a Super Admin
    # works across every school. Application code must use ``objects``.
    all_objects = models.Manager()

    class Meta:
        abstract = True
        # Related-object access (for example ``school.enrollments``) uses the base
        # manager. Pointing it at the scoped manager keeps those lookups inside the
        # active school rather than silently reading across tenants.
        base_manager_name = "objects"

    def save(self, *args, **kwargs):
        current_school_id = get_current_school_id()
        if self.school_id is None:
            if current_school_id is None:
                raise ValueError("A school context is required to create tenant data.")
            self.school_id = current_school_id
        elif current_school_id != self.school_id:
            raise ValueError("Tenant data can only be written in its school's context.")
        super().save(*args, **kwargs)

    def __str__(self):
        return str(self.pk)
