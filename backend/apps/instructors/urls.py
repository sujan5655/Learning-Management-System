from django.urls import path
from .views import (
    instructor_course_progress_view,
    instructor_course_students_view,
    instructor_dashboard_view,
    instructor_courses_view,
    instructor_course_detail_view,
)

urlpatterns = [
    path("dashboard/", instructor_dashboard_view, name="instructor-dashboard"),

    path("courses/", instructor_courses_view, name="instructor-courses"),

    path(
        "courses/<int:course_id>/",
        instructor_course_detail_view,
        name="instructor-course-detail"
    ),
    path(
    "courses/<int:course_id>/students/",
    instructor_course_students_view,
    name="instructor-course-students"
),

path(
    "courses/<int:course_id>/progress/",
    instructor_course_progress_view,
    name="instructor-course-progress"
),

]