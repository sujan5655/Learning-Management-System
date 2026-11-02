from django.db import models

# Create your models here.

from django.db import models
from django.conf import settings
from django.utils.text import slugify


class Category(models.Model):

    name = models.CharField(
        max_length=150,
        unique=True
    )

    slug = models.SlugField(
        max_length=180,
        unique=True,
        blank=True
    )

    description = models.TextField(
        blank=True
    )

    is_active = models.BooleanField(
        default=True
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)

        super().save(*args, **kwargs)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ["name"]


class Course(models.Model):

    class Level(models.TextChoices):
        BEGINNER = "BEGINNER", "Beginner"
        INTERMEDIATE = "INTERMEDIATE", "Intermediate"
        ADVANCED = "ADVANCED", "Advanced"

    class Status(models.TextChoices):
        DRAFT = "DRAFT", "Draft"
        PUBLISHED = "PUBLISHED", "Published"
        ARCHIVED = "ARCHIVED", "Archived"

    instructors = models.ManyToManyField(
    settings.AUTH_USER_MODEL,
    through="CourseInstructor",
    related_name="teaching_courses",
    limit_choices_to={"role": "INSTRUCTOR"}
)

    category = models.ForeignKey(
        Category,
        on_delete=models.PROTECT,
        related_name="courses"
    )

    title = models.CharField(
        max_length=255
    )

    slug = models.SlugField(
        max_length=280,
        unique=True,
        blank=True
    )

    short_description = models.CharField(
        max_length=300
    )

    description = models.TextField()

    thumbnail = models.ImageField(
        upload_to="courses/thumbnails/",
        blank=True,
        null=True
    )

    level = models.CharField(
        max_length=20,
        choices=Level.choices,
        default=Level.BEGINNER
    )

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT
    )

    published_at = models.DateTimeField(
        null=True,
        blank=True
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.title)
            slug = base_slug
            counter = 1

            while Course.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1

            self.slug = slug

        super().save(*args, **kwargs)

    def __str__(self):
        return self.title

    class Meta:
        ordering = ["-created_at"]



class CourseInstructor(models.Model):

    class Role(models.TextChoices):
        LEAD = "LEAD", "Lead Instructor"
        CO_INSTRUCTOR = "CO_INSTRUCTOR", "Co-Instructor"

    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        related_name="course_instructors"
    )

    instructor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="instructor_assignments"
    )

    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.CO_INSTRUCTOR
    )

    assigned_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["course", "instructor"],
                name="unique_course_instructor"
            )
        ]

    def __str__(self):
        return f"{self.instructor.email} - {self.course.title}"