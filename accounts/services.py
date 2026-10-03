from django.db import transaction
from django.utils.text import slugify

from accounts.models import User
from tenancy.models import School


@transaction.atomic
def register_school(*, school_name, school_email, admin_email, password, logo=None):
    base_slug = slugify(school_name)
    slug = base_slug
    suffix = 2
    while School.objects.filter(slug=slug).exists():
        slug = f"{base_slug}-{suffix}"
        suffix += 1

    school = School.objects.create(name=school_name, slug=slug, email=school_email, logo=logo)
    admin = User.objects.create_user(
        email=admin_email,
        password=password,
        school=school,
        role=User.Role.SCHOOL_ADMIN,
    )
    return school, admin
