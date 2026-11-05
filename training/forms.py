from django import forms
from django.core.validators import MinValueValidator
from django.utils import timezone

from .models import Plan


class StartSessionForm(forms.Form):
    date = forms.DateField(widget=forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"))
    plan = forms.ModelChoiceField(queryset=Plan.objects.none(), required=False)

    def __init__(self, *args, user, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["date"].initial = timezone.localdate
        self.fields["plan"].queryset = Plan.objects.visible_to(user).filter(is_active=True)

    def clean_date(self):
        date = self.cleaned_data["date"]
        if date > timezone.localdate():
            raise forms.ValidationError("The date cannot be in the future.")
        return date


class WeightField(forms.DecimalField):
    """Phones with a German keyboard type 62,5 instead of 62.5."""

    widget = forms.TextInput

    def to_python(self, value):
        if isinstance(value, str):
            value = value.replace(",", ".")
        return super().to_python(value)


class SetForm(forms.Form):
    weight_kg = WeightField(
        label="Weight (kg)",
        max_digits=6,
        decimal_places=2,
        validators=[MinValueValidator(0)],
        widget=forms.TextInput(attrs={"inputmode": "decimal", "autocomplete": "off"}),
    )
    reps = forms.IntegerField(
        label="Reps",
        min_value=1,
        max_value=32767,
        widget=forms.TextInput(attrs={"inputmode": "numeric", "pattern": "[0-9]*", "autocomplete": "off"}),
    )
