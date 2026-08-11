from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django import forms
from django_ckeditor_5.widgets import CKEditor5Widget
from .models import BankQuestion, Question

class SignupForm(UserCreationForm):
    class Meta:
        model = User
        fields = ["username", "password1", "password2"]

    def _init_(self, *args, **kwargs):
        super()._init_(*args, **kwargs)

        self.fields["username"].help_text = None
        self.fields["password1"].help_text = None
        self.fields["password2"].help_text = None

        for field in self.fields.values():
            field.widget.attrs.update({
                "class": "form-control"
            })

class BankQuestionForm(forms.ModelForm):
    text = forms.CharField(
        widget=CKEditor5Widget(
            attrs={"class": "django_ckeditor_5"},
            config_name="default"
        )
    )

    class Meta:
        model = BankQuestion
        fields = ["text", "qtype", "points", "correct_part_a", "correct_part_b", "correct_part_c"]

class QuestionForm(forms.ModelForm):
    text = forms.CharField(
        widget=CKEditor5Widget(
            attrs={"class": "django_ckeditor_5"},
            config_name="default"
        )
    )

    class Meta:
        model = Question
        fields = ["text", "qtype", "points", "correct_part_a", "correct_part_b", "correct_part_c"]