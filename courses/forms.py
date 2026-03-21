from django import forms
from django.forms import inlineformset_factory
from .models import Lesson, Chapter, LessonQuizQuestion, LessonQuizChoice


class LessonForm(forms.ModelForm):
    class Meta:
        model = Lesson
        fields = ["chapter", "title", "content", "is_published", "allow_students_view"]

    def _init_(self, *args, **kwargs):
        course = kwargs.pop("course", None)
        super()._init_(*args, **kwargs)

        if course:
            self.fields["chapter"].queryset = Chapter.objects.filter(course=course).order_by("order", "id")
        else:
            self.fields["chapter"].queryset = Chapter.objects.none()


class LessonQuizQuestionForm(forms.ModelForm):
    correct_part_a = forms.CharField(
        required=False,
        label="Correct Part A",
        widget=forms.Textarea(attrs={"rows": 2, "class": "form-control"})
    )

    correct_part_b = forms.CharField(
        required=False,
        label="Correct Part B",
        widget=forms.Textarea(attrs={"rows": 2, "class": "form-control"})
    )

    correct_part_c = forms.CharField(
        required=False,
        label="Correct Part C",
        widget=forms.Textarea(attrs={"rows": 2, "class": "form-control"})
    )

    class Meta:
        model = LessonQuizQuestion
        fields = ["text", "qtype", "level", "order", "marking_guide"]
        widgets = {
            "text": forms.Textarea(attrs={"rows": 3, "class": "form-control"}),
            "qtype": forms.Select(attrs={"class": "form-control"}),
            "level": forms.Select(attrs={"class": "form-control"}),
            "order": forms.NumberInput(attrs={"class": "form-control"}),
            "marking_guide": forms.Textarea(attrs={"rows": 3, "class": "form-control"}),
        }

    def save(self, commit=True):
        obj = super().save(commit=False)

        if obj.qtype == LessonQuizQuestion.TYPE_STRUCT:
            a = self.cleaned_data.get("correct_part_a", "")
            b = self.cleaned_data.get("correct_part_b", "")
            c = self.cleaned_data.get("correct_part_c", "")

            obj.expected_answer = f"A) {a}\nB) {b}\nC) {c}"

        if commit:
            obj.save()

        return obj


ChoiceFormSet = inlineformset_factory(
    LessonQuizQuestion,
    LessonQuizChoice,
    fields=("text", "is_correct"),
    extra=4,
    can_delete=True,
    widgets={
        "text": forms.TextInput(attrs={"class": "form-control"}),
    }
)