from .models import ClassSubject, SchoolClass


def class_subjects_for(user):
    """Class subjects a user may work with. Teachers see only their own."""
    queryset = ClassSubject.objects.select_related("school_class", "subject", "teacher")
    if user.is_teacher:
        queryset = queryset.filter(teacher=user)
    return queryset


def classes_for(user):
    """Classes a user may work with. Teachers see only the classes they teach."""
    if user.is_teacher:
        class_ids = ClassSubject.objects.filter(teacher=user).values_list(
            "school_class_id", flat=True
        )
        return SchoolClass.objects.filter(pk__in=class_ids).distinct()
    return SchoolClass.objects.all()
