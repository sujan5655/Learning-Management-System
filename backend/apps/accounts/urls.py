
from django.urls import path

from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)

from .views import (
    edit_instructor_application_view,
    register_view,
    user_profile_view,
    instructor_application_view,
    admin_instructor_applications_view,
    review_instructor_application_view,
)


urlpatterns = [
    # Authentication
    path("register/", register_view, name="register"),
    path("login/", TokenObtainPairView.as_view(), name="login"),
    path("refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("me/", user_profile_view, name="user_profile"),

    # Instructor applications
    path(
        "instructor/apply/",
        instructor_application_view,
        name="instructor_application"
    ),
    path(
    "instructor/applications/<int:application_id>/",
    edit_instructor_application_view,
    name="edit-instructor-application"
),

    # Admin application management
    path(
        "admin/instructor-applications/",
        admin_instructor_applications_view,
        name="admin_instructor_applications"
    ),

    path(
        "admin/instructor-applications/<int:application_id>/review/",
        review_instructor_application_view,
        name="review_instructor_application"
    ),
]
