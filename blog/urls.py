from django.urls import path
from . import views

app_name = "blog"

urlpatterns = [
    path("", views.blog_list, name="post_list"),
    path("my-articles/", views.my_articles, name="my_articles"),
    path("categories/", views.category_list, name="category_list"),
    path("categories/create/", views.category_create, name="category_create"),
    path("categories/<int:pk>/edit/", views.category_edit, name="category_edit"),
    path("posts/create/", views.post_create, name="post_create"),
    path("posts/<slug:slug>/edit/", views.post_edit, name="post_edit"),
    path("purchase-requests/", views.purchase_requests, name="purchase_requests"),
    path("purchase-requests/<int:pk>/approve/", views.purchase_approve, name="purchase_approve"),
    path("purchase-requests/<int:pk>/reject/", views.purchase_reject, name="purchase_reject"),
    path("staff-access/", views.staff_access, name="staff_access"),
    path("staff-access/<int:user_id>/grant/", views.grant_staff, name="grant_staff"),
    path("staff-access/<int:user_id>/remove/", views.remove_staff, name="remove_staff"),
    path("<slug:slug>/buy/", views.buy_post, name="buy_post"),
    path("<slug:slug>/", views.post_detail, name="post_detail"),
]
