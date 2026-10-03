from django.urls import path

from . import views

app_name = "accounts"

urlpatterns = [
    path("login/", views.AppLoginView.as_view(), name="login"),
    path("logout/", views.AppLogoutView.as_view(), name="logout"),
    path("signup/", views.signup, name="signup"),
    path("password-reset/", views.AppPasswordResetView.as_view(), name="password_reset"),
    path(
        "password-reset/done/",
        views.AppPasswordResetDoneView.as_view(),
        name="password_reset_done",
    ),
    path(
        "password-reset/complete/",
        views.AppPasswordResetCompleteView.as_view(),
        name="password_reset_complete",
    ),
    path(
        "password-reset/<uidb64>/<token>/",
        views.AppPasswordResetConfirmView.as_view(),
        name="password_reset_confirm",
    ),
    path("password-change/", views.AppPasswordChangeView.as_view(), name="password_change"),
    path(
        "password-change/done/",
        views.AppPasswordChangeDoneView.as_view(),
        name="password_change_done",
    ),
    path("school/", views.school_profile, name="school_profile"),
    path("staff/", views.staff_list, name="staff_list"),
    path("staff/new/", views.staff_create, name="staff_create"),
    path("parents/", views.parent_list, name="parent_list"),
    path("parents/new/", views.parent_create, name="parent_create"),
    path("users/<int:pk>/toggle/", views.user_toggle_active, name="user_toggle_active"),
    path("users/<int:pk>/delete/", views.user_delete, name="user_delete"),
]
