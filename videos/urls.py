from django.urls import path
from . import views

app_name = "videos"

urlpatterns = [
    # Public videos
    path("", views.video_list, name="list"),

    # Staff management
    path("manage/", views.manage_videos, name="manage"),
    path("create/", views.create_video, name="create"),
    path("edit/<int:pk>/", views.edit_video, name="edit"),
    path("delete/<int:pk>/", views.delete_video, name="delete"),

    # Categories
    path("categories/", views.category_list, name="categories"),
    path("categories/create/", views.create_category, name="category_create"),
    path(
        "categories/<int:pk>/edit/",
        views.edit_category,
        name="category_edit",
    ),

    # Staff purchase management
    path(
        "purchase-requests/",
        views.purchase_requests,
        name="purchase_requests",
    ),
    path(
        "purchase-requests/<int:pk>/approve/",
        views.approve_purchase,
        name="approve_purchase",
    ),
    path(
        "purchase-requests/<int:pk>/reject/",
        views.reject_purchase,
        name="reject_purchase",
    ),

    # Student purchased videos
    path("my-videos/", views.my_videos, name="my_videos"),

    # Individual video
    path("<slug:slug>/", views.video_detail, name="detail"),
    path("<slug:slug>/watch/", views.watch_video, name="watch"),

    # Buy one particular paid video
    path(
        "<slug:slug>/buy/",
        views.request_purchase,
        name="request_purchase",
    ),
]