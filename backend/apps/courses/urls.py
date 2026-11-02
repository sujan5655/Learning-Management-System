
from django.urls import path

from .views import (
    category_list_create_view,
    category_detail_view,
    course_list_create_view,
    course_detail_view,
)

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

]