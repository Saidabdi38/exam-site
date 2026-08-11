from decimal import Decimal
from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from django.urls import reverse


class VideoCategory(models.Model):
    name = models.CharField(max_length=120, unique=True)
    slug = models.SlugField(max_length=140, unique=True)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    sequence = models.PositiveIntegerField(default=10)

    class Meta:
        ordering = ("sequence", "name")
        verbose_name_plural = "Video categories"

    def __str__(self):
        return self.name


class Video(models.Model):
    class AccessType(models.TextChoices):
        FREE = "free", "Free"
        PAID = "paid", "Paid"

    category = models.ForeignKey(
        VideoCategory,
        on_delete=models.PROTECT,
        related_name="videos",
    )

    title = models.CharField(max_length=220)
    slug = models.SlugField(max_length=240, unique=True)
    description = models.TextField()

    thumbnail = models.ImageField(
        upload_to="videos/thumbnails/",
        blank=True,
        null=True,
    )

    video_file = models.FileField(
        upload_to="videos/files/",
        blank=True,
        null=True
    )

    access_type = models.CharField(
        max_length=10,
        choices=AccessType.choices,
        default=AccessType.FREE,
    )

    price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0.00"))],
    )

    duration_minutes = models.PositiveIntegerField(default=0)
    is_published = models.BooleanField(default=False)
    is_featured = models.BooleanField(default=False)
    published_at = models.DateTimeField(blank=True, null=True)
    views_count = models.PositiveIntegerField(default=0, editable=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-is_featured", "-published_at", "-created_at")

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse("videos:detail", kwargs={"slug": self.slug})

    @property
    def is_free(self):
        return self.access_type == self.AccessType.FREE

    def user_has_access(self, user):
        if self.is_free:
            return True

        if not getattr(user, "is_authenticated", False):
            return False

        return self.purchases.filter(
            user=user,
            status=VideoPurchase.Status.APPROVED,
        ).exists()

    def clean(self):
        if self.access_type == self.AccessType.PAID and self.price <= 0:
            raise ValidationError(
                {"price": "A paid video must have a price greater than 0."}
            )

        if self.access_type == self.AccessType.FREE:
            self.price = Decimal("0.00")

class VideoPurchase(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="video_purchases",
    )
    video = models.ForeignKey(
        Video, on_delete=models.CASCADE, related_name="purchases"
    )
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    payment_reference = models.CharField(max_length=120, blank=True)
    payment_note = models.TextField(blank=True)
    status = models.CharField(
        max_length=12, choices=Status.choices, default=Status.PENDING
    )
    requested_at = models.DateTimeField(auto_now_add=True)
    approved_at = models.DateTimeField(blank=True, null=True)
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="approved_video_purchases",
    )

    class Meta:
        ordering = ("-requested_at",)
        constraints = [
            models.UniqueConstraint(
                fields=("user", "video"), name="unique_user_video_purchase"
            )
        ]

    def __str__(self):
        return f"{self.user} - {self.video} - {self.status}"


class VideoView(models.Model):
    video = models.ForeignKey(
        Video, on_delete=models.CASCADE, related_name="view_records"
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="video_views",
    )
    viewed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-viewed_at",)
