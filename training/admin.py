from django.contrib import admin

from .models import Category, Exercise, ExerciseSet, Plan, PlanExercise, Session, SessionExercise


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    search_fields = ("name",)


@admin.register(Exercise)
class ExerciseAdmin(admin.ModelAdmin):
    list_display = ("name", "category", "method", "tracking", "is_active")
    list_editable = ("is_active",)
    list_filter = ("category", "method", "tracking", "is_active")
    search_fields = ("name",)


class PlanExerciseInline(admin.TabularInline):
    """Edit a plan in one place: its exercises and their order."""

    model = PlanExercise
    fields = ("position", "exercise")
    autocomplete_fields = ("exercise",)
    extra = 1


@admin.register(Plan)
class PlanAdmin(admin.ModelAdmin):
    list_display = ("name", "owner", "is_active")
    list_filter = ("is_active", ("owner", admin.EmptyFieldListFilter))
    search_fields = ("name",)
    inlines = [PlanExerciseInline]


class ExerciseSetInline(admin.TabularInline):
    model = ExerciseSet
    extra = 0


@admin.register(SessionExercise)
class SessionExerciseAdmin(admin.ModelAdmin):
    list_display = ("session", "order", "exercise", "method")
    readonly_fields = ("method",)
    list_select_related = ("session__athlete", "exercise")
    inlines = [ExerciseSetInline]


class SessionExerciseInline(admin.TabularInline):
    model = SessionExercise
    extra = 0
    readonly_fields = ("method",)
    show_change_link = True


@admin.register(Session)
class SessionAdmin(admin.ModelAdmin):
    list_display = ("date", "athlete", "label", "finished_at")
    list_filter = ("athlete", "date")
    date_hierarchy = "date"
    list_select_related = ("athlete",)
    inlines = [SessionExerciseInline]

    def get_queryset(self, request):
        # label reads every exercise's category; fetch them in one go.
        return super().get_queryset(request).prefetch_related("exercises__exercise__category")


@admin.register(ExerciseSet)
class ExerciseSetAdmin(admin.ModelAdmin):
    list_display = ("session_exercise", "number", "weight_kg", "reps")
    list_select_related = ("session_exercise__exercise", "session_exercise__session__athlete")
