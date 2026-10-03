from django.db import models


class SupportMessage(models.Model):
    """A message sent through the support form.

    This is platform level rather than tenant owned: the support team works
    across every school, so the messages are not hidden behind the tenant
    manager. A school is recorded when the sender is signed in, purely so the
    team knows where the request came from.
    """

    class Status(models.TextChoices):
        NEW = "new", "New"
        RESOLVED = "resolved", "Resolved"

    name = models.CharField(max_length=150)
    email = models.EmailField()
    school = models.ForeignKey(
        "tenancy.School",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="support_messages",
    )
    subject = models.CharField(max_length=200)
    body = models.TextField()
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.NEW)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.subject} ({self.email})"
