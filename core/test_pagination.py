from django.test import TestCase
from django.urls import reverse

from accounts.models import User
from students.models import Student
from tenancy.context import school_context
from tenancy.models import School


class PaginationTests(TestCase):
    def setUp(self):
        self.school = School.objects.create(name="North School", slug="north", email="north@example.test")
        self.admin = User.objects.create_user(
            email="admin@north.example.test",
            password="a-strong-test-password",
            school=self.school,
            role=User.Role.SCHOOL_ADMIN,
        )
        with school_context(self.school):
            Student.objects.bulk_create(
                [
                    Student(
                        school=self.school,
                        admission_number=f"A-{index:03d}",
                        first_name=f"Student{index:03d}",
                        last_name="Test",
                    )
                    for index in range(30)
                ]
            )

    def test_long_lists_are_paginated(self):
        self.client.force_login(self.admin)
        first = self.client.get(reverse("students:student_list"))
        self.assertContains(first, "Page 1 of 2")

        second = self.client.get(reverse("students:student_list"), {"page": 2})
        self.assertContains(second, "Page 2 of 2")

    def test_out_of_range_and_junk_pages_are_safe(self):
        self.client.force_login(self.admin)
        for value in ("999", "abc", "-1", "0"):
            response = self.client.get(reverse("students:student_list"), {"page": value})
            self.assertEqual(response.status_code, 200, value)

    def test_search_survives_paging(self):
        self.client.force_login(self.admin)
        response = self.client.get(reverse("students:student_list"), {"q": "Student00"})
        self.assertContains(response, "Student000")
