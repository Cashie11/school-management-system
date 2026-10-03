"""Platform-wide aggregation.

This is the only application module that reads across schools, which is why it
uses the unscoped ``all_objects`` manager. It exists to build the Super Admin
dashboard, where counting every school's records is the point. Everything else
must go through the school-scoped ``objects`` manager.
"""

from django.db.models import Count

from academics.models import SchoolClass
from accounts.models import User
from results.models import Assessment
from students.models import Student

STAFF_ROLES = (User.Role.SCHOOL_ADMIN, User.Role.TEACHER)


def counts_by_school(model):
    """One query returning {school_id: row_count}."""
    return {
        row["school_id"]: row["n"]
        for row in model.all_objects.values("school_id").annotate(n=Count("id"))
    }


def users_by_school(*, role=None, roles=None, removed=False):
    filters = {}
    if role is not None:
        filters["role"] = role
    if roles is not None:
        filters["role__in"] = roles
    if not removed:
        filters["removed_at__isnull"] = True
    return {
        row["school_id"]: row["n"]
        for row in User.objects.filter(**filters).values("school_id").annotate(n=Count("id"))
    }


def platform_rows(schools):
    """Build the per-school rows for the Super Admin dashboard in five queries."""
    students = counts_by_school(Student)
    classes = counts_by_school(SchoolClass)
    assessments = counts_by_school(Assessment)
    staff = users_by_school(roles=STAFF_ROLES)
    parents = users_by_school(role=User.Role.PARENT_STUDENT)

    return [
        {
            "school": school,
            "students": students.get(school.pk, 0),
            "classes": classes.get(school.pk, 0),
            "assessments": assessments.get(school.pk, 0),
            "staff": staff.get(school.pk, 0),
            "parents": parents.get(school.pk, 0),
        }
        for school in schools
    ]
