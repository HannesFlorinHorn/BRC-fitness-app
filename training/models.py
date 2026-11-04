import uuid

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone


class Category(models.Model):
    name = models.CharField(max_length=50, unique=True)

    class Meta:
        ordering = ["name"]
        verbose_name_plural = "categories"

    def __str__(self):
        return self.name


class Exercise(models.Model):
    """Catalog entry. Athletes pick from this list instead of typing names."""

    class Method(models.IntegerChoices):
        # The rules behind each Methode (target reps, progression) are not
        # implemented yet; see ROADMAP.md.
        METHOD_1 = 1, "Methode 1"
        METHOD_2 = 2, "Methode 2"

    name = models.CharField(max_length=100, unique=True)
    category = models.ForeignKey(Category, on_delete=models.PROTECT, related_name="exercises")
    method = models.PositiveSmallIntegerField(choices=Method.choices)

    class Meta:
        ordering = ["category__name", "name"]

    def __str__(self):
        return self.name


class Session(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    athlete = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="training_sessions"
    )
    date = models.DateField(default=timezone.localdate)
    categories = models.ManyToManyField(Category, blank=True, related_name="sessions")
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    finished_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-date", "-created_at"]

    def __str__(self):
        return f"{self.athlete} · {self.date} · {self.label}"

    @property
    def label(self):
        """Sessions have no title; they are named after their categories."""
        names = [c.name.capitalize() for c in self.categories.all()]
        return " · ".join(names) or "Session"

    @property
    def is_finished(self):
        return self.finished_at is not None


class SessionExercise(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    session = models.ForeignKey(Session, on_delete=models.CASCADE, related_name="exercises")
    exercise = models.ForeignKey(Exercise, on_delete=models.PROTECT, related_name="session_exercises")
    order = models.PositiveSmallIntegerField()
    # Copied from the catalog when the exercise is logged, so changing an
    # exercise's Methode later does not rewrite past sessions.
    method = models.PositiveSmallIntegerField(choices=Exercise.Method.choices, editable=False)

    class Meta:
        ordering = ["order"]
        constraints = [
            models.UniqueConstraint(fields=["session", "order"], name="unique_exercise_order_per_session"),
        ]

    def __str__(self):
        return f"{self.order}. {self.exercise}"

    def save(self, *args, **kwargs):
        if self.method is None:
            self.method = self.exercise.method
        super().save(*args, **kwargs)


class ExerciseSet(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    session_exercise = models.ForeignKey(SessionExercise, on_delete=models.CASCADE, related_name="sets")
    number = models.PositiveSmallIntegerField()
    # 0 kg is allowed for bodyweight exercises.
    weight_kg = models.DecimalField(max_digits=6, decimal_places=2, validators=[MinValueValidator(0)])
    reps = models.PositiveSmallIntegerField(validators=[MinValueValidator(1)])

    class Meta:
        ordering = ["number"]
        constraints = [
            models.UniqueConstraint(fields=["session_exercise", "number"], name="unique_set_number_per_exercise"),
        ]

    def __str__(self):
        return f"Set {self.number}: {self.weight_kg} kg × {self.reps}"
