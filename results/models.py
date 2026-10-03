from django.db import models
from django.utils import timezone

from tenancy.models import TenantModel


class Assessment(TenantModel):
    """A graded piece of work for one class-subject within a term.

    In ``manual`` mode the teacher types each student's mark. In ``online`` mode
    the teacher writes questions and students answer them in the app.
    """

    class Mode(models.TextChoices):
        MANUAL = "manual", "Teacher enters marks"
        ONLINE = "online", "Students answer online"

    class_subject = models.ForeignKey(
        "academics.ClassSubject", on_delete=models.CASCADE, related_name="assessments"
    )
    term = models.ForeignKey(
        "academics.AcademicTerm", on_delete=models.CASCADE, related_name="assessments"
    )
    name = models.CharField(max_length=120)
    max_score = models.DecimalField(max_digits=6, decimal_places=2, default=100)
    date = models.DateField(null=True, blank=True)
    mode = models.CharField(max_length=10, choices=Mode.choices, default=Mode.MANUAL)
    is_published = models.BooleanField(default=False)
    available_from = models.DateTimeField(null=True, blank=True)
    available_until = models.DateTimeField(null=True, blank=True)
    duration_minutes = models.PositiveIntegerField(null=True, blank=True)

    class Meta:
        base_manager_name = "objects"
        ordering = ["term__start_date", "class_subject__school_class__level", "name"]
        constraints = [
            models.UniqueConstraint(
                fields=["school", "class_subject", "term", "name"], name="uniq_assessment_per_term"
            )
        ]

    @property
    def is_online(self):
        return self.mode == self.Mode.ONLINE

    def opens_at(self, now=None):
        """Return (is_open, reason) for student access."""
        if not self.is_online:
            return False, "This assessment is marked by the teacher."
        if not self.is_published:
            return False, "This assessment has not been published yet."
        now = now or timezone.now()
        if self.available_from and now < self.available_from:
            return False, "This assessment is not open yet."
        if self.available_until and now > self.available_until:
            return False, "This assessment has closed."
        return True, ""

    def total_points(self):
        return self.questions.aggregate(total=models.Sum("points"))["total"] or 0

    def sync_max_score(self):
        total = self.total_points()
        if total:
            self.max_score = total
            self.save(update_fields=["max_score"])
        return self.max_score

    def __str__(self):
        return f"{self.name} ({self.class_subject})"


class Question(TenantModel):
    class Section(models.TextChoices):
        OBJECTIVE = "objective", "Objective"
        THEORY = "theory", "Theory"

    assessment = models.ForeignKey(Assessment, on_delete=models.CASCADE, related_name="questions")
    section = models.CharField(max_length=10, choices=Section.choices)
    text = models.TextField()
    points = models.DecimalField(max_digits=6, decimal_places=2, default=1)
    order = models.PositiveIntegerField(default=1)

    class Meta:
        base_manager_name = "objects"
        ordering = ["section", "order", "id"]

    @property
    def is_objective(self):
        return self.section == self.Section.OBJECTIVE

    def __str__(self):
        return self.text[:60]


class Choice(TenantModel):
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name="choices")
    text = models.CharField(max_length=300)
    is_correct = models.BooleanField(default=False)
    order = models.PositiveIntegerField(default=1)

    class Meta:
        base_manager_name = "objects"
        ordering = ["order", "id"]

    def __str__(self):
        return self.text[:60]


class Submission(TenantModel):
    """A student's attempt at an online assessment."""

    class Status(models.TextChoices):
        IN_PROGRESS = "in_progress", "In progress"
        SUBMITTED = "submitted", "Awaiting marking"
        MARKED = "marked", "Marked"

    assessment = models.ForeignKey(Assessment, on_delete=models.CASCADE, related_name="submissions")
    student = models.ForeignKey("students.Student", on_delete=models.CASCADE, related_name="submissions")
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.IN_PROGRESS)
    started_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    submitted_at = models.DateTimeField(null=True, blank=True)
    objective_score = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    theory_score = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)

    class Meta:
        base_manager_name = "objects"
        ordering = ["student__last_name", "student__first_name"]
        constraints = [
            models.UniqueConstraint(
                fields=["school", "assessment", "student"], name="uniq_submission_per_student"
            )
        ]

    @property
    def total_score(self):
        objective = self.objective_score or 0
        theory = self.theory_score or 0
        return objective + theory

    @property
    def is_submitted(self):
        return self.status != self.Status.IN_PROGRESS

    def __str__(self):
        return f"{self.student} - {self.assessment}"


class Answer(TenantModel):
    submission = models.ForeignKey(Submission, on_delete=models.CASCADE, related_name="answers")
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name="answers")
    selected_choice = models.ForeignKey(
        Choice, null=True, blank=True, on_delete=models.SET_NULL, related_name="answers"
    )
    text_answer = models.TextField(blank=True)
    awarded_points = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)

    class Meta:
        base_manager_name = "objects"
        ordering = ["question__section", "question__order", "id"]
        constraints = [
            models.UniqueConstraint(
                fields=["school", "submission", "question"], name="uniq_answer_per_question"
            )
        ]

    def __str__(self):
        return f"{self.question}"


class Score(TenantModel):
    assessment = models.ForeignKey(Assessment, on_delete=models.CASCADE, related_name="scores")
    student = models.ForeignKey("students.Student", on_delete=models.CASCADE, related_name="scores")
    value = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)

    class Meta:
        base_manager_name = "objects"
        ordering = ["student__last_name", "student__first_name"]
        constraints = [
            models.UniqueConstraint(
                fields=["school", "assessment", "student"], name="uniq_score_per_assessment"
            )
        ]
        indexes = [models.Index(fields=["school", "student"], name="score_school_student_idx")]

    @property
    def percentage(self):
        if self.value is None or not self.assessment.max_score:
            return None
        return (self.value / self.assessment.max_score) * 100

    def __str__(self):
        return f"{self.student} {self.assessment}: {self.value}"
