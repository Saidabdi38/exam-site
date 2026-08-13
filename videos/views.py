from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.db.models import F, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from .utils import optimize_video_for_streaming

from .forms import VideoCategoryForm, VideoForm, VideoPurchaseRequestForm
from .models import Video, VideoCategory, VideoPurchase, VideoView


def staff_required(view_func):
    return user_passes_test(lambda u: u.is_authenticated and u.is_staff)(view_func)


def video_list(request):
    videos = Video.objects.filter(is_published=True).select_related("category")
    categories = VideoCategory.objects.filter(is_active=True)

    category_slug = request.GET.get("category", "").strip()
    access = request.GET.get("access", "").strip()
    q = request.GET.get("q", "").strip()

    if category_slug:
        videos = videos.filter(category__slug=category_slug)
    if access in {Video.AccessType.FREE, Video.AccessType.PAID}:
        videos = videos.filter(access_type=access)
    if q:
        videos = videos.filter(
            Q(title__icontains=q)
            | Q(description__icontains=q)
            | Q(category__name__icontains=q)
        )

    return render(
        request,
        "videos/video_list.html",
        {
            "videos": videos,
            "categories": categories,
            "selected_category": category_slug,
            "selected_access": access,
            "q": q,
        },
    )


@staff_required
def manage_videos(request):
    videos = Video.objects.select_related("category").all()
    return render(request, "videos/manage_videos.html", {"videos": videos})


@staff_required
def create_video(request):
    if request.method == "POST":
        form = VideoForm(request.POST, request.FILES)
        if form.is_valid():
            video = form.save(commit=False)
            if video.is_published and not video.published_at:
                video.published_at = timezone.now()
            video.save()

            if "video_file" in request.FILES:
                optimize_video_for_streaming(video)
            messages.success(request, "Video created successfully.")
            return redirect("videos:manage")
    else:
        form = VideoForm()
    return render(
        request,
        "videos/video_form.html",
        {"form": form, "page_title": "Create Video"},
    )


@staff_required
def edit_video(request, pk):
    video = get_object_or_404(Video, pk=pk)
    if request.method == "POST":
        form = VideoForm(request.POST, request.FILES, instance=video)
        if form.is_valid():
            video = form.save(commit=False)
            if video.is_published and not video.published_at:
                video.published_at = timezone.now()
            video.save()

            if "video_file" in request.FILES:
                optimize_video_for_streaming(video)
            messages.success(request, "Video updated successfully.")
            return redirect("videos:manage")
    else:
        form = VideoForm(instance=video)

    return render(
        request,
        "videos/video_form.html",
        {"form": form, "page_title": "Edit Video", "video": video},
    )

@staff_required
def delete_video(request, pk):
    video = get_object_or_404(Video, pk=pk)

    if request.method == "POST":
        title = video.title
        video.delete()

        messages.success(
            request,
            f'Video "{title}" deleted successfully.'
        )

        return redirect("videos:manage")

    return render(
        request,
        "videos/video_confirm_delete.html",
        {"video": video},
    )

@staff_required
def category_list(request):
    categories = VideoCategory.objects.all()
    return render(
        request, "videos/category_list.html", {"categories": categories}
    )


@staff_required
def create_category(request):
    if request.method == "POST":
        form = VideoCategoryForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Video category created.")
            return redirect("videos:categories")
    else:
        form = VideoCategoryForm()
    return render(
        request,
        "videos/category_form.html",
        {"form": form, "page_title": "Create Video Category"},
    )


@staff_required
def edit_category(request, pk):
    category = get_object_or_404(VideoCategory, pk=pk)
    if request.method == "POST":
        form = VideoCategoryForm(request.POST, instance=category)
        if form.is_valid():
            form.save()
            messages.success(request, "Video category updated.")
            return redirect("videos:categories")
    else:
        form = VideoCategoryForm(instance=category)
    return render(
        request,
        "videos/category_form.html",
        {"form": form, "page_title": "Edit Video Category"},
    )


def video_detail(request, slug):
    video = get_object_or_404(
        Video.objects.select_related("category"), slug=slug, is_published=True
    )
    purchase = None
    if request.user.is_authenticated and not video.is_free:
        purchase = VideoPurchase.objects.filter(
            user=request.user, video=video
        ).first()

    return render(
        request,
        "videos/video_detail.html",
        {
            "video": video,
            "has_access": video.user_has_access(request.user),
            "purchase": purchase,
        },
    )


@login_required
def watch_video(request, slug):
    video = get_object_or_404(
        Video,
        slug=slug,
        is_published=True
    )

    if not video.user_has_access(request.user):
        messages.error(
            request,
            "You do not have access to this video."
        )
        return redirect(
            "videos:detail",
            slug=video.slug
        )

    VideoView.objects.create(
        video=video,
        user=request.user
    )

    Video.objects.filter(
        pk=video.pk
    ).update(
        views_count=F("views_count") + 1
    )

    video.refresh_from_db(
        fields=["views_count"]
    )

    published_videos = list(
        Video.objects.filter(
            is_published=True,
            category=video.category
        ).order_by("created_at")
    )

    previous_video = None
    next_video = None

    for index, item in enumerate(published_videos):
        if item.pk == video.pk:

            if index > 0:
                previous_video = published_videos[index - 1]

            if index < len(published_videos) - 1:
                next_video = published_videos[index + 1]

            break

    return render(
        request,
        "videos/watch_video.html",
        {
            "video": video,
            "previous_video": previous_video,
            "next_video": next_video,
        }
    )


@login_required
def request_purchase(request, slug):
    video = get_object_or_404(
        Video,
        slug=slug,
        is_published=True,
        access_type=Video.AccessType.PAID,
    )

    purchase = VideoPurchase.objects.filter(
        user=request.user, video=video
    ).first()

    if purchase and purchase.status == VideoPurchase.Status.APPROVED:
        return redirect("videos:watch", slug=video.slug)

    if request.method == "POST":
        form = VideoPurchaseRequestForm(request.POST, instance=purchase)
        if form.is_valid():
            obj = form.save(commit=False)
            obj.user = request.user
            obj.video = video
            obj.amount = video.price
            obj.status = VideoPurchase.Status.PENDING
            obj.approved_at = None
            obj.approved_by = None
            obj.save()
            messages.success(
                request,
                "Purchase request submitted. Access opens after approval.",
            )
            return redirect("videos:detail", slug=video.slug)
    else:
        form = VideoPurchaseRequestForm(instance=purchase)

    return render(
        request,
        "videos/purchase_request.html",
        {"video": video, "form": form},
    )


@login_required
def my_videos(request):
    approved = VideoPurchase.objects.filter(
        user=request.user,
        status=VideoPurchase.Status.APPROVED,
        video__is_published=True,
    ).select_related("video", "video__category")

    pending = VideoPurchase.objects.filter(
        user=request.user, status=VideoPurchase.Status.PENDING
    ).select_related("video")

    return render(
        request,
        "videos/my_videos.html",
        {
            "approved_purchases": approved,
            "pending_purchases": pending,
        },
    )

@staff_required
def purchase_requests(request):
    purchases = VideoPurchase.objects.select_related(
        "user",
        "video",
    ).order_by("-requested_at")

    return render(
        request,
        "videos/purchase_requests.html",
        {
            "purchases": purchases,
        },
    )


@staff_required
def approve_purchase(request, pk):
    purchase = get_object_or_404(
        VideoPurchase,
        pk=pk,
    )

    if request.method == "POST":
        purchase.status = VideoPurchase.Status.APPROVED
        purchase.approved_by = request.user
        purchase.approved_at = timezone.now()
        purchase.save(
            update_fields=[
                "status",
                "approved_by",
                "approved_at",
            ]
        )

        messages.success(
            request,
            f'Access approved for {purchase.user.username}.',
        )

    return redirect("videos:purchase_requests")


@staff_required
def reject_purchase(request, pk):
    purchase = get_object_or_404(
        VideoPurchase,
        pk=pk,
    )

    if request.method == "POST":
        purchase.status = VideoPurchase.Status.REJECTED
        purchase.approved_by = None
        purchase.approved_at = None
        purchase.save(
            update_fields=[
                "status",
                "approved_by",
                "approved_at",
            ]
        )

        messages.success(
            request,
            f'Purchase request rejected for {purchase.user.username}.',
        )

    return redirect("videos:purchase_requests")