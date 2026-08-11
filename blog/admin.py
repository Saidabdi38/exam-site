from django.contrib import admin
from django.utils import timezone
from .models import BlogCategory, BlogPost, PostPurchase


@admin.register(BlogCategory)
class BlogCategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "active", "created_at")
    search_fields = ("name", "description")
    list_filter = ("active",)
    prepopulated_fields = {"slug": ("name",)}


@admin.register(BlogPost)
class BlogPostAdmin(admin.ModelAdmin):
    list_display = ("title", "category", "is_paid", "is_published", "featured_post", "view_count", "created_at")
    search_fields = ("title", "summary", "content")
    list_filter = ("category", "is_paid", "is_published", "featured_post")
    prepopulated_fields = {"slug": ("title",)}


@admin.action(description="Approve selected purchases")
def approve_purchases(modeladmin, request, queryset):
    queryset.update(status=PostPurchase.APPROVED, approved_by=request.user, approved_date=timezone.now())


@admin.action(description="Reject selected purchases")
def reject_purchases(modeladmin, request, queryset):
    queryset.update(status=PostPurchase.REJECTED, approved_by=request.user, approved_date=timezone.now())


@admin.register(PostPurchase)
class PostPurchaseAdmin(admin.ModelAdmin):
    list_display = ("user", "post", "status", "payment_reference", "request_date", "approved_by")
    search_fields = ("user__username", "user__email", "post__title", "payment_reference")
    list_filter = ("status", "request_date")
    actions = [approve_purchases, reject_purchases]
