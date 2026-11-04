from django.contrib import admin

from .models import Category, Exercise, ExerciseSet, Session, SessionExercise


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    search_fields = ("name",)


@admin.register(Exercise)
class ExerciseAdmin(admin.ModelAdmin):
    list_display = ("name", "category", "method")
    list_filter = ("category", "method")
    search_fields = ("name",)


class ExerciseSetInline(admin.TabularInline):
    model = ExerciseSet
    extra = 0


@admin.register(SessionExercise)
class SessionExerciseAdmin(admin.ModelAdmin):
    list_display = ("session", "order", "exercise")
    list_select_related = ("session__athlete", "exercise")
    inlines = [ExerciseSetInline]


class SessionExerciseInline(admin.TabularInline):
    model = SessionExercise
    extra = 0
    show_change_link = True


@admin.register(Session)
class SessionAdmin(admin.ModelAdmin):
    list_display = ("date", "athlete", "label", "finished_at")
    list_filter = ("athlete", "categories", "date")
    date_hierarchy = "date"
    list_select_related = ("athlete",)
    inlines = [SessionExerciseInline]


@admin.register(ExerciseSet)
class ExerciseSetAdmin(admin.ModelAdmin):
    list_display = ("session_exercise", "number", "weight_kg", "reps")
    list_select_related = ("session_exercise__exercise", "session_exercise__session__athlete")
