import uuid

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models, transaction
from django.utils import timezone


class Category(models.Model):
    """Muscle group of an exercise (legs, arms, core). Used to label sessions
    and group the exercise picker; plans are separate (see Plan)."""

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
    # Exercises are never deleted once logged; the coach deactivates them instead.
    is_active = models.BooleanField(default=True, help_text="Inactive exercises are hidden when logging.")

    class Meta:
        ordering = ["category__name", "name"]

    def __str__(self):
        return self.name


class PlanQuerySet(models.QuerySet):
    def visible_to(self, user):
        """Club plans plus the user's own plans. Use for reading."""
        return self.filter(models.Q(owner__isnull=True) | models.Q(owner=user))

    def owned_by(self, user):
        """Only the user's own plans. Use for editing; club plans are changed by the coach in the admin."""
        return self.filter(owner=user)


class Plan(models.Model):
    """A session template: an ordered list of exercises. Club plans have no
    owner and are maintained by the coach; athletes can also build their own."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="plans",
        help_text="Leave empty for a club plan everyone can use.",
    )
    is_active = models.BooleanField(default=True, help_text="Inactive plans cannot be started.")
    exercises = models.ManyToManyField(Exercise, through="PlanExercise", related_name="plans")

    objects = PlanQuerySet.as_manager()

    class Meta:
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(fields=["owner", "name"], name="unique_plan_name_per_owner"),
            models.UniqueConstraint(
                fields=["name"], condition=models.Q(owner__isnull=True), name="unique_club_plan_name"
            ),
        ]

    def __str__(self):
        return self.name if self.owner_id is None else f"{self.name} ({self.owner})"


class PlanExercise(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    plan = models.ForeignKey(Plan, on_delete=models.CASCADE, related_name="plan_exercises")
    exercise = models.ForeignKey(Exercise, on_delete=models.CASCADE, related_name="plan_exercises")
    position = models.PositiveSmallIntegerField()

    class Meta:
        ordering = ["position"]

    def __str__(self):
        return f"{self.plan}: {self.position}. {self.exercise}"


class Session(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    athlete = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="training_sessions"
    )
    date = models.DateField(default=timezone.localdate)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    finished_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-date", "-created_at"]

    def __str__(self):
        return f"{self.athlete} · {self.date} · {self.label}"

    @property
    def label(self):
        """Sessions have no title; they are named after the categories of
        their exercises, in the order they were done."""
        names = []
        for session_exercise in self.exercises.all():
            name = session_exercise.exercise.category.name.capitalize()
            if name not in names:
                names.append(name)
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

    def swap_order_with(self, other):
        """Swap positions with another exercise of the same session."""
        if other.session_id != self.session_id:
            raise ValueError("Can only swap exercises within one session")
        mine, theirs = self.order, other.order
        with transaction.atomic():
            # Orders start at 1, so 0 is free as a temporary slot for the unique constraint.
            self.order = 0
            self.save(update_fields=["order"])
            other.order = mine
            other.save(update_fields=["order"])
            self.order = theirs
            self.save(update_fields=["order"])


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
