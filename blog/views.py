from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required, user_passes_test
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST

from .forms import BlogCategoryForm, BlogPostForm, PostPurchaseForm
from .models import BlogCategory, BlogPost, PostPurchase


def is_staff_user(user):
    return user.is_authenticated and user.is_staff


def is_superuser(user):
    return user.is_authenticated and user.is_superuser


def user_has_access(user, post):
    if not post.is_paid:
        return True
    if not user.is_authenticated:
        return False
    if user.is_staff:
        return True
    return PostPurchase.objects.filter(user=user, post=post, status=PostPurchase.APPROVED).exists()


def blog_list(request):
    posts = BlogPost.objects.select_related("category", "created_by")
    if not request.user.is_staff:
        posts = posts.filter(is_published=True, category__active=True)

    q = request.GET.get("q", "").strip()
    category_slug = request.GET.get("category", "").strip()
    sort = request.GET.get("sort", "latest")

    if q:
        posts = posts.filter(Q(title__icontains=q) | Q(summary__icontains=q) | Q(content__icontains=q))
    if category_slug:
        posts = posts.filter(category__slug=category_slug)
    if sort == "most_viewed":
        posts = posts.order_by("-view_count", "-created_at")
    elif sort == "featured":
        posts = posts.order_by("-featured_post", "-created_at")
    else:
        posts = posts.order_by("-created_at")

    categories = BlogCategory.objects.filter(active=True).order_by("name")
    featured_posts = BlogPost.objects.filter(is_published=True, featured_post=True).select_related("category")[:3]
    most_viewed_posts = BlogPost.objects.filter(is_published=True).order_by("-view_count")[:3]

    stats = None
    if request.user.is_staff:
        stats = {
            "total": BlogPost.objects.count(),
            "published": BlogPost.objects.filter(is_published=True).count(),
            "draft": BlogPost.objects.filter(is_published=False).count(),
            "premium": BlogPost.objects.filter(is_paid=True).count(),
            "free": BlogPost.objects.filter(is_paid=False).count(),
            "categories": BlogCategory.objects.count(),
            "pending": PostPurchase.objects.filter(status=PostPurchase.PENDING).count(),
            "approved": PostPurchase.objects.filter(status=PostPurchase.APPROVED).count(),
        }

    from django.core.paginator import Paginator
    paginator = Paginator(posts, 8)
    page_obj = paginator.get_page(request.GET.get("page"))

    return render(request, "blog/post_list.html", {
        "page_obj": page_obj,
        "categories": categories,
        "featured_posts": featured_posts,
        "most_viewed_posts": most_viewed_posts,
        "stats": stats,
        "q": q,
        "selected_category": category_slug,
        "sort": sort,
    })


def post_detail(request, slug):
    post_qs = BlogPost.objects.select_related("category", "created_by")
    if not request.user.is_staff:
        post_qs = post_qs.filter(is_published=True, category__active=True)
    post = get_object_or_404(post_qs, slug=slug)

    BlogPost.objects.filter(pk=post.pk).update(view_count=post.view_count + 1)
    post.view_count += 1

    purchase = None
    access = user_has_access(request.user, post)
    if request.user.is_authenticated:
        purchase = PostPurchase.objects.filter(user=request.user, post=post).first()

    related_posts = BlogPost.objects.filter(
        category=post.category,
        is_published=True,
    ).exclude(pk=post.pk).order_by("-created_at")[:4]

    return render(request, "blog/post_detail.html", {
        "post": post,
        "purchase": purchase,
        "has_access": access,
        "related_posts": related_posts,
    })


@login_required
def buy_post(request, slug):
    post = get_object_or_404(BlogPost, slug=slug, is_published=True, is_paid=True)
    existing = PostPurchase.objects.filter(user=request.user, post=post).first()
    if existing:
        messages.info(request, f"You already have a {existing.get_status_display()} request for this article.")
        return redirect("blog:post_detail", slug=post.slug)

    if request.method == "POST":
        form = PostPurchaseForm(request.POST, request.FILES)
        if form.is_valid():
            purchase = form.save(commit=False)
            purchase.user = request.user
            purchase.post = post
            purchase.status = PostPurchase.PENDING
            purchase.save()
            messages.success(request, "Purchase request submitted. Please wait for approval.")
            return redirect("blog:post_detail", slug=post.slug)
    else:
        form = PostPurchaseForm()
    return render(request, "blog/buy_post.html", {"post": post, "form": form})


@login_required
def my_articles(request):
    purchases = PostPurchase.objects.filter(user=request.user, status=PostPurchase.APPROVED).select_related("post", "post__category")
    return render(request, "blog/my_articles.html", {"purchases": purchases})


@login_required
@user_passes_test(is_staff_user)
def category_list(request):
    categories = BlogCategory.objects.annotate(post_count=Count("posts")).order_by("name")
    return render(request, "blog/category_list.html", {"categories": categories})


@login_required
@user_passes_test(is_staff_user)
def category_create(request):
    if request.method == "POST":
        form = BlogCategoryForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Category saved.")
            return redirect("blog:category_list")
    else:
        form = BlogCategoryForm()
    return render(request, "blog/category_form.html", {"form": form, "title": "Create Category"})


@login_required
@user_passes_test(is_staff_user)
def category_edit(request, pk):
    category = get_object_or_404(BlogCategory, pk=pk)
    if request.method == "POST":
        form = BlogCategoryForm(request.POST, instance=category)
        if form.is_valid():
            form.save()
            messages.success(request, "Category updated.")
            return redirect("blog:category_list")
    else:
        form = BlogCategoryForm(instance=category)
    return render(request, "blog/category_form.html", {"form": form, "title": "Edit Category"})


@login_required
@user_passes_test(is_staff_user)
def post_create(request):
    if request.method == "POST":
        form = BlogPostForm(request.POST, request.FILES)
        if form.is_valid():
            post = form.save(commit=False)
            post.created_by = request.user
            post.save()
            messages.success(request, "Post saved.")
            return redirect("blog:post_list")
        messages.error(request, "Please correct the errors below.")
    else:
        form = BlogPostForm(initial={"is_published": True})
    return render(request, "blog/post_form.html", {"form": form, "title": "Create Post"})


@login_required
@user_passes_test(is_staff_user)
def post_edit(request, slug):
    post = get_object_or_404(BlogPost, slug=slug)
    if request.method == "POST":
        form = BlogPostForm(request.POST, request.FILES, instance=post)
        if form.is_valid():
            form.save()
            messages.success(request, "Post updated.")
            return redirect("blog:post_list")
        messages.error(request, "Please correct the errors below.")
    else:
        form = BlogPostForm(instance=post)
    return render(request, "blog/post_form.html", {"form": form, "title": "Edit Post", "post": post})


@login_required
@user_passes_test(is_staff_user)
def purchase_requests(request):
    purchases = PostPurchase.objects.select_related("user", "post").order_by("-request_date")
    status = request.GET.get("status", "")
    if status:
        purchases = purchases.filter(status=status)
    return render(request, "blog/purchase_requests.html", {"purchases": purchases, "status": status})


@login_required
@user_passes_test(is_staff_user)
@require_POST
def purchase_approve(request, pk):
    purchase = get_object_or_404(PostPurchase, pk=pk)
    if purchase.user == request.user:
        messages.error(request, "You cannot approve your own purchase.")
    else:
        purchase.approve(request.user)
        messages.success(request, "Purchase approved.")
    return redirect("blog:purchase_requests")


@login_required
@user_passes_test(is_staff_user)
@require_POST
def purchase_reject(request, pk):
    purchase = get_object_or_404(PostPurchase, pk=pk)
    if purchase.user == request.user:
        messages.error(request, "You cannot reject your own purchase.")
    else:
        purchase.reject(request.user)
        messages.success(request, "Purchase rejected.")
    return redirect("blog:purchase_requests")


@login_required
@user_passes_test(is_superuser)
def staff_access(request):
    User = get_user_model()
    users = User.objects.all().order_by("username")
    return render(request, "blog/staff_access.html", {"users": users})


@login_required
@user_passes_test(is_superuser)
@require_POST
def grant_staff(request, user_id):
    User = get_user_model()
    user = get_object_or_404(User, pk=user_id)
    user.is_staff = True
    user.save(update_fields=["is_staff"])
    messages.success(request, f"Staff access granted to {user.username}.")
    return redirect("blog:staff_access")


@login_required
@user_passes_test(is_superuser)
@require_POST
def remove_staff(request, user_id):
    User = get_user_model()
    user = get_object_or_404(User, pk=user_id)
    if user.is_superuser:
        messages.error(request, "Cannot remove staff access from a superuser here.")
    else:
        user.is_staff = False
        user.save(update_fields=["is_staff"])
        messages.success(request, f"Staff access removed from {user.username}.")
    return redirect("blog:staff_access")
