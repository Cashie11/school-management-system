from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from core.permissions import management_required
from students.models import Student

from .models import EmailLog


@management_required
def clear_student_emails(request, student_pk):
    """Remove the notification history for one student."""
    student = get_object_or_404(Student, pk=student_pk)
    back = reverse("students:student_detail", args=[student.pk])
    emails = EmailLog.objects.filter(student=student)

    if request.method == "POST":
        removed = emails.count()
        emails.delete()
        messages.success(
            request,
            f"Cleared {removed} notification{'' if removed == 1 else 's'} for {student.full_name}.",
        )
        return redirect(back)

    return render(
        request,
        "notifications/clear_emails.html",
        {
            "student": student,
            "count": emails.count(),
            "cancel_url": back,
        },
    )
