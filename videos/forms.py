from django import forms
from .models import Video, VideoCategory, VideoPurchase


class VideoForm(forms.ModelForm):
    class Meta:
        model = Video
        fields = (
            "category",
            "title",
            "slug",
            "description",
            "thumbnail",
            "video_file",
            "access_type",
            "price",
            "duration_minutes",
            "is_published",
            "is_featured",
        )
        widgets = {
            "description": forms.Textarea(attrs={"rows": 6}),
            "video_url": forms.URLInput(
                attrs={"placeholder": "https://example.com/video.mp4"}
            ),
        }


class VideoCategoryForm(forms.ModelForm):
    class Meta:
        model = VideoCategory
        fields = ("name", "slug", "description", "is_active", "sequence")
        widgets = {"description": forms.Textarea(attrs={"rows": 4})}


class VideoPurchaseRequestForm(forms.ModelForm):
    class Meta:
        model = VideoPurchase
        fields = ("payment_reference", "payment_note")
        widgets = {
            "payment_reference": forms.TextInput(
                attrs={"placeholder": "Payment/reference number"}
            ),
            "payment_note": forms.Textarea(attrs={"rows": 3}),
        }
