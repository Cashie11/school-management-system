from decimal import Decimal

from django.core import mail
from django.test import TestCase
from django.urls import reverse

from academics.models import AcademicTerm, ClassSubject, SchoolClass, Subject
from accounts.models import User
from attendance.models import AttendanceRecord
from results.models import Assessment, Choice, Question, Score
from students.models import DisciplineRecord, Enrollment, Guardian, Student
from tenancy.context import school_context
from tenancy.models import School

from .models import EmailLog
from .services import notify_student_welcome


class NotificationTests(TestCase):
    def setUp(self):
        self.school = School.objects.create(name="North School", slug="north", email="north@example.test")
        self.admin = User.objects.create_user(
            email="admin@north.example.test",
            password="a-strong-test-password",
            school=self.school,
            role=User.Role.SCHOOL_ADMIN,
        )
        with school_context(self.school):
            self.term = AcademicTerm.objects.create(
                name="Term 1", start_date="2026-01-10", end_date="2026-04-10", is_current=True
            )
            self.school_class = SchoolClass.objects.create(name="Grade 6", level=6)
        self.client.force_login(self.admin)

    def test_student_creation_sends_a_welcome_email(self):
        response = self.client.post(
            reverse("students:student_create"),
            {
                "admission_number": "A-1",
                "first_name": "Ada",
                "last_name": "Lovelace",
                "email": "ada@example.test",
                "is_active": "on",
            },
        )
        self.assertRedirects(response, reverse("students:student_list"))
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ["ada@example.test"])
        self.assertIn("Welcome", mail.outbox[0].subject)
        self.assertIn("North School", mail.outbox[0].body)

        with school_context(self.school):
            log = EmailLog.objects.get()
        self.assertEqual(log.kind, EmailLog.Kind.WELCOME)

    def test_student_without_contact_details_sends_nothing(self):
        response = self.client.post(
            reverse("students:student_create"),
            {
                "admission_number": "A-2",
                "first_name": "Alan",
                "last_name": "Turing",
                "is_active": "on",
            },
        )
        self.assertRedirects(response, reverse("students:student_list"))
        self.assertEqual(len(mail.outbox), 0)

    def test_welcome_falls_back_to_linked_guardians(self):
        with school_context(self.school):
            student = Student.objects.create(
                admission_number="A-3", first_name="Grace", last_name="Hopper"
            )
        parent = User.objects.create_user(
            email="parent@north.example.test",
            password="a-strong-test-password",
            school=self.school,
            role=User.Role.PARENT_STUDENT,
        )
        with school_context(self.school):
            Guardian.objects.create(user=parent, student=student)
            notify_student_welcome(student)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ["parent@north.example.test"])

    def test_linking_a_guardian_notifies_the_account(self):
        with school_context(self.school):
            student = Student.objects.create(
                admission_number="A-1", first_name="Ada", last_name="Lovelace"
            )
        response = self.client.post(
            reverse("accounts:parent_create"),
            {
                "first_name": "Mary",
                "last_name": "Lovelace",
                "email": "mary@example.test",
                "student": student.pk,
                "relationship": "Mother",
                "is_primary": "on",
                "password1": "a-strong-test-password",
                "password2": "a-strong-test-password",
            },
        )
        self.assertRedirects(response, reverse("accounts:parent_list"))
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ["mary@example.test"])
        with school_context(self.school):
            log = EmailLog.objects.get()
        self.assertEqual(log.kind, EmailLog.Kind.GUARDIAN_LINK)

    def test_results_email_goes_to_student_and_guardians(self):
        with school_context(self.school):
            subject = Subject.objects.create(name="Mathematics")
            class_subject = ClassSubject.objects.create(
                school_class=self.school_class, subject=subject
            )
            student = Student.objects.create(
                admission_number="A-1",
                first_name="Ada",
                last_name="Lovelace",
                email="ada@example.test",
            )
            Enrollment.objects.create(
                student=student, school_class=self.school_class, term=self.term
            )
            assessment = Assessment.objects.create(
                class_subject=class_subject, term=self.term, name="Midterm", max_score=50
            )
            Score.objects.create(assessment=assessment, student=student, value=Decimal("40"))
        parent = User.objects.create_user(
            email="parent@north.example.test",
            password="a-strong-test-password",
            school=self.school,
            role=User.Role.PARENT_STUDENT,
        )
        with school_context(self.school):
            Guardian.objects.create(user=parent, student=student)

        response = self.client.post(
            reverse("results:email_report", args=[student.pk, self.term.pk])
        )
        self.assertRedirects(
            response, reverse("results:report_card", args=[student.pk, self.term.pk])
        )
        recipients = sorted(recipient for message in mail.outbox for recipient in message.to)
        self.assertEqual(recipients, ["ada@example.test", "parent@north.example.test"])
        self.assertIn("80.00%", mail.outbox[0].body)

    def test_discipline_notice_is_recorded_and_emailed(self):
        with school_context(self.school):
            student = Student.objects.create(
                admission_number="A-1",
                first_name="Ada",
                last_name="Lovelace",
                email="ada@example.test",
            )
        response = self.client.post(
            reverse("students:discipline_create"),
            {
                "student": student.pk,
                "kind": DisciplineRecord.Kind.SUSPENSION,
                "reason": "Repeated lateness",
                "start_date": "2026-02-01",
                "end_date": "2026-02-05",
            },
        )
        self.assertRedirects(response, reverse("students:discipline_list"))
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("Suspension", mail.outbox[0].subject)
        self.assertIn("Repeated lateness", mail.outbox[0].body)

        with school_context(self.school):
            record = DisciplineRecord.objects.get()
            self.assertEqual(record.issued_by, self.admin)
            self.assertEqual(EmailLog.objects.get().kind, EmailLog.Kind.DISCIPLINE)

    def test_records_created_in_the_admin_also_notify(self):
        superuser = User.objects.create_superuser(
            email="root@platform.example.test", password="a-strong-test-password"
        )
        self.client.force_login(superuser)
        self.client.post(
            reverse("admin:students_student_add"),
            {
                "school": self.school.pk,
                "admission_number": "A-9",
                "first_name": "Katherine",
                "last_name": "Johnson",
                "email": "kj@example.test",
                "is_active": "on",
            },
        )
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ["kj@example.test"])
        with school_context(self.school):
            self.assertEqual(EmailLog.objects.get().kind, EmailLog.Kind.WELCOME)

    def test_staff_account_creation_sends_an_account_email(self):
        response = self.client.post(
            reverse("accounts:staff_create"),
            {
                "first_name": "Grace",
                "last_name": "Hopper",
                "email": "grace@north.example.test",
                "role": User.Role.TEACHER,
                "password1": "a-strong-test-password",
                "password2": "a-strong-test-password",
            },
        )
        self.assertRedirects(response, reverse("accounts:staff_list"))
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ["grace@north.example.test"])
        with school_context(self.school):
            self.assertEqual(EmailLog.objects.get().kind, EmailLog.Kind.ACCOUNT)

    def test_enrollment_notifies_the_family(self):
        with school_context(self.school):
            student = Student.objects.create(
                admission_number="A-1",
                first_name="Ada",
                last_name="Lovelace",
                email="ada@example.test",
            )
        response = self.client.post(
            reverse("students:enrollment_create"),
            {"student": student.pk, "school_class": self.school_class.pk, "term": self.term.pk},
        )
        self.assertRedirects(response, reverse("students:enrollment_list"))
        self.assertEqual(len(mail.outbox), 1)
        with school_context(self.school):
            self.assertEqual(EmailLog.objects.get().kind, EmailLog.Kind.ENROLLMENT)

    def test_absence_notifies_the_family_only_once(self):
        with school_context(self.school):
            student = Student.objects.create(
                admission_number="A-1",
                first_name="Ada",
                last_name="Lovelace",
                email="ada@example.test",
            )
            Enrollment.objects.create(
                student=student, school_class=self.school_class, term=self.term
            )
        payload = {
            "action": "save",
            "school_class": self.school_class.pk,
            "term": self.term.pk,
            "date": "2026-02-03",
            f"status_{student.pk}": AttendanceRecord.Status.ABSENT,
        }
        self.client.post(reverse("attendance:register"), payload)
        self.assertEqual(len(mail.outbox), 1)

        mail.outbox.clear()
        self.client.post(reverse("attendance:register"), payload)
        self.assertEqual(len(mail.outbox), 0)

    def test_publishing_an_assessment_notifies_enrolled_students(self):
        with school_context(self.school):
            subject = Subject.objects.create(name="Mathematics")
            class_subject = ClassSubject.objects.create(
                school_class=self.school_class, subject=subject
            )
            student = Student.objects.create(
                admission_number="A-1",
                first_name="Ada",
                last_name="Lovelace",
                email="ada@example.test",
            )
            Enrollment.objects.create(
                student=student, school_class=self.school_class, term=self.term
            )
            assessment = Assessment.objects.create(
                class_subject=class_subject,
                term=self.term,
                name="Quiz",
                mode=Assessment.Mode.ONLINE,
                max_score=10,
            )
        response = self.client.post(
            reverse("results:assessment_publish", args=[assessment.pk])
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(len(mail.outbox), 1)
        with school_context(self.school):
            self.assertEqual(EmailLog.objects.get().kind, EmailLog.Kind.ASSESSMENT)

    def test_online_result_email_is_sent_once_marked(self):
        with school_context(self.school):
            subject = Subject.objects.create(name="Mathematics")
            class_subject = ClassSubject.objects.create(
                school_class=self.school_class, subject=subject
            )
            student = Student.objects.create(
                admission_number="A-1",
                first_name="Ada",
                last_name="Lovelace",
                email="ada@example.test",
            )
            Enrollment.objects.create(
                student=student, school_class=self.school_class, term=self.term
            )
            assessment = Assessment.objects.create(
                class_subject=class_subject,
                term=self.term,
                name="Quiz",
                mode=Assessment.Mode.ONLINE,
                is_published=True,
                max_score=10,
            )
            question = Question.objects.create(
                assessment=assessment,
                section=Question.Section.OBJECTIVE,
                text="2 + 2?",
                points=10,
                order=1,
            )
            choice = Choice.objects.create(
                question=question, text="4", is_correct=True, order=1
            )
        parent = User.objects.create_user(
            email="parent@north.example.test",
            password="a-strong-test-password",
            school=self.school,
            role=User.Role.PARENT_STUDENT,
        )
        with school_context(self.school):
            Guardian.objects.create(user=parent, student=student)

        self.client.force_login(parent)
        self.client.post(
            reverse("portal:exam_take", args=[student.pk, assessment.pk]),
            {f"choice_{question.pk}": choice.pk},
        )
        self.assertTrue(any("result ready" in message.subject.lower() for message in mail.outbox))
