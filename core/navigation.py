"""Build the two-pane navigation for the signed-in account.

The first pane lists the top level sections; the second lists the pages inside
the section the current URL belongs to. Keeping this in one place means a new
page is added to the menu by adding it here, and the active state is worked out
from the URL rather than repeated in every template.
"""

from django.urls import reverse


def _item(label, url_name, icon, roles, names=None):
    return {
        "label": label,
        "url": reverse(url_name),
        "icon": icon,
        "roles": set(roles),
        "namespace": url_name.split(":")[0],
        "names": set(names) if names else None,
        "active": False,
    }


def _section(key, label, icon, roles, items, requires_school=True):
    return {
        "key": key,
        "label": label,
        "icon": icon,
        "roles": set(roles),
        "items": items,
        "requires_school": requires_school,
        "namespaces": {item["namespace"] for item in items},
        "active": False,
    }


def _sections(role):
    from accounts.models import User

    admin = {User.Role.SUPER_ADMIN, User.Role.SCHOOL_ADMIN}
    teaching = {User.Role.SUPER_ADMIN, User.Role.SCHOOL_ADMIN, User.Role.TEACHER}
    everyone = {
        User.Role.SUPER_ADMIN,
        User.Role.SCHOOL_ADMIN,
        User.Role.TEACHER,
        User.Role.PARENT_STUDENT,
    }

    return [
        _section(
            "dashboard",
            "Dashboard",
            "bi-house-door",
            everyone,
            [
                _item("Overview", "dashboard:home", "bi-house-door", everyone, {"home"}),
            ],
        ),
        _section(
            "announcements",
            "Announcements",
            "bi-megaphone",
            everyone,
            [
                _item("All announcements", "announcements:list", "bi-megaphone", everyone, {"list"}),
                _item(
                    "New announcement",
                    "announcements:create",
                    "bi-plus-circle",
                    teaching,
                    {"create", "edit", "delete"},
                ),
            ],
        ),
        _section(
            "classes",
            "Classes",
            "bi-collection",
            teaching,
            [
                _item(
                    "My classes",
                    "dashboard:class_list",
                    "bi-collection",
                    teaching,
                    {"class_list", "class_detail"},
                ),
                _item(
                    "Attendance",
                    "attendance:register",
                    "bi-calendar2-check",
                    teaching,
                    {"register", "record_list"},
                ),
            ],
        ),
        _section(
            "students",
            "Students",
            "bi-people",
            teaching,
            [
                _item(
                    "All students",
                    "students:student_list",
                    "bi-people",
                    teaching,
                    {"student_list", "student_detail", "student_edit", "student_delete"},
                ),
                _item("Add student", "students:student_create", "bi-person-plus", admin, {"student_create"}),
                _item(
                    "Enrollment",
                    "students:enrollment_list",
                    "bi-journal-check",
                    admin,
                    {"enrollment_list", "enrollment_create", "enrollment_delete"},
                ),
                _item(
                    "Guardians",
                    "students:guardian_list",
                    "bi-person-hearts",
                    admin,
                    {"guardian_list", "guardian_create", "guardian_delete"},
                ),
                _item(
                    "Discipline",
                    "students:discipline_list",
                    "bi-shield-exclamation",
                    admin,
                    {"discipline_list", "discipline_create"},
                ),
            ],
        ),
        _section(
            "academics",
            "Academics",
            "bi-book",
            admin,
            [
                _item(
                    "Terms",
                    "academics:term_list",
                    "bi-calendar3",
                    admin,
                    {"term_list", "term_create", "term_edit", "term_delete"},
                ),
                _item(
                    "Subjects",
                    "academics:subject_list",
                    "bi-book",
                    admin,
                    {"subject_list", "subject_create", "subject_edit", "subject_delete"},
                ),
                _item(
                    "Classes",
                    "academics:class_list",
                    "bi-collection",
                    admin,
                    {"class_list", "class_create", "class_edit", "class_delete"},
                ),
                _item(
                    "Teacher assignments",
                    "academics:assignment_list",
                    "bi-person-video3",
                    admin,
                    {"assignment_list", "assignment_create", "assignment_edit", "assignment_delete"},
                ),
            ],
        ),
        _section(
            "results",
            "Results",
            "bi-clipboard2-data",
            teaching,
            [
                _item(
                    "Assessments",
                    "results:assessment_list",
                    "bi-clipboard2-data",
                    teaching,
                    {
                        "assessment_list",
                        "assessment_create",
                        "assessment_edit",
                        "assessment_delete",
                        "assessment_questions",
                        "question_create",
                        "question_edit",
                        "question_delete",
                        "choice_create",
                        "choice_delete",
                        "score_entry",
                        "submission_list",
                        "submission_mark",
                        "submission_reset",
                    },
                ),
                _item(
                    "Report cards",
                    "results:report_card_select",
                    "bi-file-earmark-text",
                    teaching,
                    {"report_card_select", "report_card", "email_report", "report_card_download"},
                ),
            ],
        ),
        _section(
            "accounts",
            "Accounts",
            "bi-person-badge",
            admin,
            [
                _item(
                    "Staff",
                    "accounts:staff_list",
                    "bi-person-badge",
                    admin,
                    {"staff_list", "staff_create"},
                ),
                _item(
                    "Parents and students",
                    "accounts:parent_list",
                    "bi-people",
                    admin,
                    {"parent_list", "parent_create"},
                ),
            ],
        ),
        _section(
            "schools",
            "Schools",
            "bi-buildings",
            {User.Role.SUPER_ADMIN},
            [
                _item(
                    "All schools",
                    "tenancy:school_list",
                    "bi-buildings",
                    {User.Role.SUPER_ADMIN},
                    {"school_list"},
                ),
            ],
            requires_school=False,
        ),
        _section(
            "portal",
            "My portal",
            "bi-mortarboard",
            {User.Role.PARENT_STUDENT},
            [
                _item("Overview", "portal:home", "bi-mortarboard", {User.Role.PARENT_STUDENT}, {"home"}),
            ],
        ),
        _section(
            "support",
            "Help and support",
            "bi-life-preserver",
            everyone,
            [
                _item(
                    "Help centre",
                    "support:help",
                    "bi-book",
                    everyone,
                    {"help", "article"},
                ),
                _item(
                    "Contact support",
                    "support:contact",
                    "bi-envelope",
                    everyone,
                    {"contact", "contact_done"},
                ),
                _item(
                    "Support inbox",
                    "support:message_list",
                    "bi-inbox",
                    {User.Role.SUPER_ADMIN},
                    {"message_list", "message_resolve"},
                ),
            ],
            requires_school=False,
        ),
    ]


def build_navigation(request):
    """Return the sections and items the current account may see, with the
    section and item matching the current URL marked active."""

    user = request.user
    school_id = getattr(request, "school_id", None)
    resolver = getattr(request, "resolver_match", None)
    namespace = getattr(resolver, "namespace", "") or ""
    url_name = getattr(resolver, "url_name", "") or ""

    sections = []
    for section in _sections(user.role):
        if user.role not in section["roles"]:
            continue
        if section["requires_school"] and not school_id:
            continue
        items = [item for item in section["items"] if user.role in item["roles"]]
        if not items:
            continue
        for item in items:
            item["active"] = item["namespace"] == namespace and (
                item["names"] is None or url_name in item["names"]
            )
        section["items"] = items
        section["namespaces"] = {item["namespace"] for item in items}
        section["url"] = items[0]["url"]
        section["active"] = any(item["active"] for item in items)
        sections.append(section)

    # Nothing matched an item exactly (a profile or password page, say). Fall
    # back to the first section whose namespace matches, then to the first
    # section, so the second pane is never empty. Using the namespace only as a
    # fallback keeps sections that share a namespace, such as Dashboard and
    # Classes, from both lighting up.
    if sections and not any(section["active"] for section in sections):
        matching = [section for section in sections if namespace in section["namespaces"]]
        (matching[0] if matching else sections[0])["active"] = True

    return {"nav_sections": sections}
