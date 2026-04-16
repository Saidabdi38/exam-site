from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User

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