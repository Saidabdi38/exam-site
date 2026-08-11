from django.conf import settings
from django.db import models
from django.utils import timezone
import html
from django.utils.html import strip_tags
from django.utils.text import slugify


class BlogCategory(models.Model):
    name = models.CharField(max_length=150, unique=True)
    slug = models.SlugField(max_length=170, unique=True, blank=True)
    description = models.TextField(blank=True)
    active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]
        verbose_name_plural = "Blog categories"

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            base = slugify(self.name) or "category"
            slug = base
            counter = 2
            while BlogCategory.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f"{base}-{counter}"
                counter += 1
            self.slug = slug
        super().save(*args, **kwargs)


class BlogPost(models.Model):
    category = models.ForeignKey(BlogCategory, on_delete=models.PROTECT, related_name="posts")
    title = models.CharField(max_length=220)
    slug = models.SlugField(max_length=240, unique=True, blank=True)
    summary = models.TextField(blank=True)
    content = models.TextField()
    featured_image = models.ImageField(upload_to="blog/images/", blank=True, null=True)
    price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    is_paid = models.BooleanField(default=False)
    is_published = models.BooleanField(default=True)
    featured_post = models.BooleanField(default=False)
    seo_title = models.CharField(max_length=220, blank=True)
    seo_description = models.TextField(blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="blog_posts")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    view_count = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if not self.slug:
            base = slugify(self.title) or "post"
            slug = base
            counter = 2
            while BlogPost.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f"{base}-{counter}"
                counter += 1
            self.slug = slug
        if not self.summary and self.content:
            clean = html.unescape(" ".join(strip_tags(self.content).replace("\xa0", " ").split()))
            self.summary = clean[:250]
        if not self.seo_title:
            self.seo_title = self.title
        if not self.seo_description:
            self.seo_description = self.summary[:160]
        super().save(*args, **kwargs)



    def premium_preview(self, length=450):
        """Return a clean text-only preview for users without premium access."""
        clean = html.unescape(strip_tags(self.content or "").replace("\xa0", " "))
        clean = " ".join(clean.split())
        if len(clean) <= length:
            return clean
        return clean[:length].rsplit(" ", 1)[0] + "..."


class PostPurchase(models.Model):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    STATUS_CHOICES = [
        (PENDING, "Pending"),
        (APPROVED, "Approved"),
        (REJECTED, "Rejected"),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="post_purchases")
    post = models.ForeignKey(BlogPost, on_delete=models.CASCADE, related_name="purchases")
    payment_reference = models.CharField(max_length=255)
    payment_screenshot = models.ImageField(upload_to="blog/payments/", blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=PENDING)
    notes = models.TextField(blank=True)
    request_date = models.DateTimeField(auto_now_add=True)
    approved_date = models.DateTimeField(blank=True, null=True)
    approved_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="approved_post_purchases")

    class Meta:
        ordering = ["-request_date"]
        constraints = [
            models.UniqueConstraint(fields=["user", "post"], name="unique_user_post_purchase")
        ]

    def __str__(self):
        return f"{self.user} - {self.post} - {self.status}"

    def approve(self, user=None):
        self.status = self.APPROVED
        self.approved_by = user
        self.approved_date = timezone.now()
        self.save(update_fields=["status", "approved_by", "approved_date"])

    def reject(self, user=None):
        self.status = self.REJECTED
        self.approved_by = user
        self.approved_date = timezone.now()
        self.save(update_fields=["status", "approved_by", "approved_date"])
