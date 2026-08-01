"""Admin registrations for the quiz_app app."""

from django.contrib import admin

from .models import Question, Quiz

TIMESTAMP_FIELDS = ("created_at", "updated_at")


class QuestionInline(admin.StackedInline):
    """Edit the questions of a quiz next to the quiz itself."""

    model = Question
    extra = 0
    readonly_fields = TIMESTAMP_FIELDS


@admin.register(Quiz)
class QuizAdmin(admin.ModelAdmin):
    """Admin interface for quizzes and their questions."""

    list_display = ("title", "owner", "video_url", "created_at")
    list_filter = ("owner", "created_at")
    search_fields = ("title", "description", "video_url")
    readonly_fields = TIMESTAMP_FIELDS
    inlines = (QuestionInline,)


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    """Admin interface for single questions, independent of the quiz."""

    list_display = ("__str__", "quiz", "answer", "created_at")
    list_filter = ("quiz", "created_at")
    search_fields = ("question_title", "answer")
    readonly_fields = TIMESTAMP_FIELDS
    autocomplete_fields = ("quiz",)
