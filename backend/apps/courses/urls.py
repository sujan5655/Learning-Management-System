
from django.urls import path

from .views import (
    category_list_create_view,
    category_detail_view,
    course_list_create_view,
    course_detail_view,
    course_progress_view,
    course_sections_view,
    end_playback_session_view,
    lesson_detail_view,
    my_progress_view,
    section_detail_view,
    section_lessons_view,
)

from .views import (
    enroll_course_view,
    my_enrollments_view,
    unenroll_course_view,
)
from .views import update_lesson_progress_view
from .views import my_progress_view, course_progress_view
from .views import resume_lesson_view
from .views import create_playback_session_view
urlpatterns = [

    # Categories
    path(
        "categories/",
        category_list_create_view,
        name="category-list-create"
    ),

    path(
        "categories/<int:category_id>/",
        category_detail_view,
        name="category-detail"
    ),

    # Courses
    path(
        "courses/",
        course_list_create_view,
        name="course-list-create"
    ),

    path(
        "courses/<slug:slug>/",
        course_detail_view,
        name="course-detail"
    ),


    path(
    "courses/<int:course_id>/sections/",
    course_sections_view,
    name="course-sections"
),

path(
    "sections/<int:section_id>/",
    section_detail_view,
    name="section-detail"
),


path(
    "sections/<int:section_id>/lessons/",
    section_lessons_view,
    name="section-lessons"
),

path(
    "lessons/<int:lesson_id>/",
    lesson_detail_view,
    name="lesson-detail"
),


path(
    "courses/<int:course_id>/enroll/",
    enroll_course_view,
    name="enroll-course"
),

path(
    "my-enrollments/",
    my_enrollments_view,
    name="my-enrollments"
),

path(
    "courses/<int:course_id>/unenroll/",
    unenroll_course_view,
    name="unenroll-course"
),

path(
    "courses/<int:course_id>/lessons/<int:lesson_id>/progress/",
    update_lesson_progress_view,
    name="update-lesson-progress"
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


path(
    "courses/<int:course_id>/lessons/<int:lesson_id>/resume/",
    resume_lesson_view,
    name="resume-lesson"
),

path(
    "courses/<int:course_id>/lessons/<int:lesson_id>/playback-session/",
    create_playback_session_view,
    name="create-playback-session"
),

path(
    "courses/<int:course_id>/lessons/<int:lesson_id>/playback-session/end/",
    end_playback_session_view,
    name="end-playback-session"
),


]