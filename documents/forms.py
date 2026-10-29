from django import forms


class QuestionForm(forms.Form):
    question = forms.CharField(
        max_length=1000,
        strip=True,
        widget=forms.TextInput(
            attrs={
                "placeholder": "Ask a question about your documents…",
                "autocomplete": "off",
                "maxlength": "1000",
            }
        ),
    )
