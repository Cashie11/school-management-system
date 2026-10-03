from academics.models import ClassSubject

from .models import Enrollment, Student


def students_for(user):
    """Students a user may see. Teachers see only students in the classes they teach."""
    queryset = Student.objects.all()
    if user.is_teacher:
        class_ids = ClassSubject.objects.filter(teacher=user).values_list(
            "school_class_id", flat=True
        )
        student_ids = Enrollment.objects.filter(
            school_class_id__in=class_ids
        ).values_list("student_id", flat=True)
        queryset = queryset.filter(pk__in=student_ids).distinct()
    return queryset
