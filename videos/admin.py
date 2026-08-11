from django.contrib import admin
from django.utils import timezone
from .models import Video, VideoCategory, VideoPurchase, VideoView


@admin.register(VideoCategory)
class VideoCategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "sequence", "is_active")
    list_editable = ("sequence", "is_active")
    prepopulated_fields = {"slug": ("name",)}
    search_fields = ("name",)


@admin.register(Video)
class VideoAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "category",
        "access_type",
        "price",
        "is_published",
        "is_featured",
        "views_count",
    )
    list_filter = (
        "category",
        "access_type",
        "is_published",
        "is_featured",
    )
    search_fields = ("title", "description")
    prepopulated_fields = {"slug": ("title",)}
    readonly_fields = ("views_count", "created_at", "updated_at")

    def save_model(self, request, obj, form, change):
        if obj.is_published and not obj.published_at:
            obj.published_at = timezone.now()
        obj.full_clean()
        super().save_model(request, obj, form, change)


@admin.action(description="Approve selected video purchases")
def approve_purchases(modeladmin, request, queryset):
    queryset.update(
        status=VideoPurchase.Status.APPROVED,
        approved_at=timezone.now(),
        approved_by=request.user,
    )


@admin.action(description="Reject selected video purchases")
def reject_purchases(modeladmin, request, queryset):
    queryset.update(
        status=VideoPurchase.Status.REJECTED,
        approved_at=None,
        approved_by=None,
    )


@admin.register(VideoPurchase)
class VideoPurchaseAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "video",
        "amount",
        "status",
        "payment_reference",
        "requested_at",
        "approved_at",
    )
    list_filter = ("status", "requested_at")
    search_fields = (
        "user__username",
        "user__email",
        "video__title",
        "payment_reference",
    )
    actions = (approve_purchases, reject_purchases)


@admin.register(VideoView)
class VideoViewAdmin(admin.ModelAdmin):
    list_display = ("video", "user", "viewed_at")
    readonly_fields = ("video", "user", "viewed_at")

    def has_add_permission(self, request):
        return False
