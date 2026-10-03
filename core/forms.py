from django import forms

from tenancy.context import get_current_school_id
from tenancy.models import TenantModel


class TenantModelForm(forms.ModelForm):
    """ModelForm for tenant-owned records.

    Two things happen here that plain ModelForms get wrong for multi-tenant data:

    1. The owning school is assigned before validation, so unique constraints that
       include the school are checked by the form rather than failing at the
       database with an IntegrityError.
    2. Foreign keys to tenant models are re-scoped on every request. ModelForm
       builds its fields at import time, when no tenant context exists, so those
       querysets would otherwise be empty forever.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._assign_school()
        self._scope_tenant_querysets()

    def _assign_school(self):
        school_id = get_current_school_id()
        if school_id is not None and self.instance.school_id is None:
            self.instance.school_id = school_id

    def _get_validation_exclusions(self):
        exclude = super()._get_validation_exclusions()
        # ``school`` is not a form field, but it is set on the instance above.
        # Django skips any constraint that mentions an excluded field, so keep it
        # in scope for validation to catch per-school uniqueness.
        exclude.discard("school")
        return exclude

    def _scope_tenant_querysets(self):
        for name, field in self.fields.items():
            queryset = getattr(field, "queryset", None)
            model = getattr(queryset, "model", None)
            if isinstance(model, type) and issubclass(model, TenantModel):
                field.queryset = model._default_manager.all()
