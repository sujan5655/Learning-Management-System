from django.urls import path

from .views import (
    course_progress_view,
    my_progress_view,
    student_dashboard_view,
    enroll_course_view,
    my_enrollments_view,
    unenroll_course_view,
)


urlpatterns = [
    # Dashboard
    path(
        "dashboard/",
        student_dashboard_view,
        name="student-dashboard"
    ),

    # Enrollment
    path(
        "courses/<int:course_id>/enroll/",
        enroll_course_view,
        name="enroll-course"
    ),

    path(
        "enrollments/",
        my_enrollments_view,
        name="my-enrollments"
    ),

    path(
        "courses/<int:course_id>/unenroll/",
        unenroll_course_view,
        name="unenroll-course"
    ),
    path(
    "my-progress/",
    my_progress_view,
    name="my-progress"
),

path(
    "courses/<int:course_id>/progress/",
    course_progress_view,
    name="course-progress"
),
]