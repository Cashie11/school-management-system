from django.contrib.auth import authenticate
from django.db import connection, models
from django.test import TestCase

from accounts.models import User

from .context import school_context
from .models import School, TenantModel


class TenantProbe(TenantModel):
    label = models.CharField(max_length=30)

    class Meta:
        app_label = "tenancy"
        managed = False


class TenantIsolationTests(TestCase):
    @classmethod
    def setUpClass(cls):
        with connection.schema_editor() as schema_editor:
            schema_editor.create_model(TenantProbe)
        super().setUpClass()

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        with connection.schema_editor() as schema_editor:
            schema_editor.delete_model(TenantProbe)

    def setUp(self):
        self.school_a = School.objects.create(name="North School", slug="north", email="north@example.test")
        self.school_b = School.objects.create(name="South School", slug="south", email="south@example.test")
        self.user_a = User.objects.create_user(
            email="admin@north.example.test", password="a-strong-test-password", school=self.school_a,
            role=User.Role.SCHOOL_ADMIN,
        )
        self.user_b = User.objects.create_user(
            email="admin@south.example.test", password="a-strong-test-password", school=self.school_b,
            role=User.Role.SCHOOL_ADMIN,
        )

    def test_queries_and_writes_are_limited_to_the_active_school(self):
        with school_context(self.school_a):
            north_record = TenantProbe.objects.create(label="North record")
            self.assertEqual(list(TenantProbe.objects.values_list("label", flat=True)), ["North record"])
            with self.assertRaises(ValueError):
                TenantProbe(school=self.school_b, label="Wrong school").save()

        with school_context(self.school_b):
            self.assertEqual(TenantProbe.objects.count(), 0)
            TenantProbe.objects.create(label="South record")
            self.assertEqual(list(TenantProbe.objects.values_list("label", flat=True)), ["South record"])
            north_record.label = "Modified from South"
            with self.assertRaises(ValueError):
                north_record.save()

        self.assertEqual(TenantProbe.objects.count(), 0)

    def test_user_school_and_role_are_explicit(self):
        self.assertEqual(self.user_a.school, self.school_a)
        self.assertEqual(self.user_a.role, User.Role.SCHOOL_ADMIN)
        self.assertEqual(self.user_b.school, self.school_b)
        self.assertEqual(
            authenticate(email="admin@north.example.test", password="a-strong-test-password"),
            self.user_a,
        )