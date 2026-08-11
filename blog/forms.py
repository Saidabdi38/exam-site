from django import forms
from .models import BlogCategory, BlogPost, PostPurchase


class BlogCategoryForm(forms.ModelForm):
    class Meta:
        model = BlogCategory
        fields = ["name", "slug", "description", "active"]
        widgets = {
            "description": forms.Textarea(attrs={"rows": 4}),
        }


class BlogPostForm(forms.ModelForm):
    class Meta:
        model = BlogPost
        fields = [
            "category", "title", "slug", "summary", "content", "featured_image",
            "price", "is_paid", "is_published", "featured_post", "seo_title", "seo_description",
        ]
        widgets = {
            "summary": forms.Textarea(attrs={"rows": 4, "placeholder": "Optional. If empty, it will be generated from content."}),
            "content": forms.Textarea(attrs={"rows": 10, "class": "blog-hidden-content"}),
            "seo_description": forms.Textarea(attrs={"rows": 3}),
        }

    def clean_content(self):
        content = self.cleaned_data.get("content", "").strip()
        if not content:
            raise forms.ValidationError("Content is required. Please type or paste the article content.")
        return content


class PostPurchaseForm(forms.ModelForm):
    class Meta:
        model = PostPurchase
        fields = ["payment_reference", "payment_screenshot"]
