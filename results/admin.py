from django.contrib import admin

from core.admin import TenantModelAdmin

from .models import Answer, Assessment, Choice, Question, Score, Submission


@admin.register(Assessment)
class AssessmentAdmin(TenantModelAdmin):
    list_display = ("name", "class_subject", "term", "mode", "max_score", "is_published", "date")
    list_filter = ("mode", "is_published", "term", "class_subject__school_class")
    list_select_related = ("class_subject", "term")


@admin.register(Question)
class QuestionAdmin(TenantModelAdmin):
    list_display = ("assessment", "section", "order", "points", "text")
    list_filter = ("section",)
    list_select_related = ("assessment",)


@admin.register(Choice)
class ChoiceAdmin(TenantModelAdmin):
    list_display = ("question", "text", "is_correct", "order")
    list_filter = ("is_correct",)
    list_select_related = ("question",)


@admin.register(Submission)
class SubmissionAdmin(TenantModelAdmin):
    list_display = ("assessment", "student", "status", "objective_score", "theory_score")
    list_filter = ("status",)
    list_select_related = ("assessment", "student")


@admin.register(Answer)
class AnswerAdmin(TenantModelAdmin):
    list_display = ("submission", "question", "selected_choice", "awarded_points")
    list_select_related = ("submission", "question", "selected_choice")


@admin.register(Score)
class ScoreAdmin(TenantModelAdmin):
    list_display = ("student", "assessment", "value")
    list_filter = ("assessment__term", "assessment__class_subject")
    search_fields = ("student__first_name", "student__last_name")
    list_select_related = ("student", "assessment")
