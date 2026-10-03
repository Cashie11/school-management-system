"""Written help guides.

The guides are plain data rather than database rows, so they can be written and
reviewed like the rest of the code. Each guide has sections made of paragraphs
and numbered steps; the templates render whichever a section provides.
"""

GUIDES = [
    {
        "slug": "getting-started",
        "title": "Getting started",
        "summary": "Create the school, set up the year, and bring your staff on board.",
        "audience": "School admins",
        "icon": "bi-rocket-takeoff",
        "sections": [
            {
                "heading": "Register the school",
                "steps": [
                    "Choose Register a school and enter the school name, contact email and an"
                    " administrator email.",
                    "Upload a logo if you have one. It appears in the header and on report cards.",
                    "Sign in with the administrator email and the password you chose.",
                ],
            },
            {
                "heading": "Set up the academic year",
                "steps": [
                    "Open Academics and create a term for each period you record results in.",
                    "Add the subjects your school teaches.",
                    "Create the classes, then assign teachers to each class subject.",
                ],
            },
            {
                "heading": "Add people",
                "steps": [
                    "Add your staff from Accounts, then Staff. Each member of staff gets an email address used to sign in.",
                    "Add students from Students, then Add student.",
                    "Link a parent to a student from Parents and students. One parent account can follow several children.",
                ],
            },
        ],
    },
    {
        "slug": "managing-students",
        "title": "Managing student records",
        "summary": "Add students, enroll them in a class for the term, and keep guardians linked.",
        "audience": "School admins",
        "icon": "bi-people",
        "sections": [
            {
                "heading": "Add a student",
                "paragraphs": [
                    "Students, then Add student records the student's name, admission number and"
                    " contact details. The admission number must be unique within your school.",
                ],
            },
            {
                "heading": "Enroll a student in a class",
                "steps": [
                    "Open Students, then Enrollment and choose New enrollment.",
                    "Pick the student, the class and the term.",
                    "Enrollment is recorded per term, so a student's class history is kept.",
                ],
            },
            {
                "heading": "Link a guardian",
                "paragraphs": [
                    "From Students, then Guardians, link a parent account to a student. The parent"
                    " can then see that student's attendance, results and report cards, and"
                    " receives the notifications sent about them.",
                ],
            },
            {
                "heading": "Discipline notes",
                "paragraphs": [
                    "Discipline records capture a category, a date and a note. They are visible to"
                    " the school's management and can notify the family.",
                ],
            },
        ],
    },
    {
        "slug": "recording-attendance",
        "title": "Recording attendance",
        "summary": "Take the register for a class and review the record later.",
        "audience": "Teachers",
        "icon": "bi-calendar2-check",
        "sections": [
            {
                "heading": "Take the register",
                "steps": [
                    "Open Classes, then Attendance.",
                    "Choose the class and the date.",
                    "Set each student to present, absent, late or excused, then save.",
                ],
            },
            {
                "heading": "What families receive",
                "paragraphs": [
                    "An absence sends a notification to the student's own address and to every"
                    " linked guardian, so families learn about it the same day.",
                ],
            },
            {
                "heading": "Review past records",
                "paragraphs": [
                    "Attendance, then Records lists the register entries already taken, filtered"
                    " by class and date.",
                ],
            },
        ],
    },
    {
        "slug": "assessments-and-results",
        "title": "Assessments and results",
        "summary": "Create assessments, enter scores, and run online assessments.",
        "audience": "Teachers",
        "icon": "bi-clipboard2-data",
        "sections": [
            {
                "heading": "Create an assessment",
                "steps": [
                    "Open Results, then Assessments and choose New assessment.",
                    "Choose the class subject, the term and the maximum score.",
                    "Save, then enter scores from the assessment's Scores action.",
                ],
            },
            {
                "heading": "Online assessments",
                "paragraphs": [
                    "An assessment can be sat online by students. Add questions, split between"
                    " objective questions that are marked automatically and theory questions that"
                    " you mark yourself. An assessment can have an opening and closing time and a"
                    " time limit, and each student sits it once.",
                ],
            },
            {
                "heading": "Marking",
                "paragraphs": [
                    "Objective answers are scored as the student submits. Theory answers wait for"
                    " you in the submissions list, where each answer is marked out of the question's"
                    " score. A submission can be reset to let a student sit the assessment again.",
                ],
            },
        ],
    },
    {
        "slug": "report-cards",
        "title": "Report cards",
        "summary": "Generate a report card for a term, and send it to the family.",
        "audience": "School admins",
        "icon": "bi-file-earmark-text",
        "sections": [
            {
                "heading": "Generate a report card",
                "steps": [
                    "Open Results, then Report cards.",
                    "Choose the student and the term.",
                    "The report card shows each subject's total, the grade, the position in the"
                    " class and the attendance summary.",
                ],
            },
            {
                "heading": "Send it to the family",
                "paragraphs": [
                    "From the report card you can download a PDF or email it. Emailing sends it to"
                    " the student's address and every linked guardian, and the send is recorded"
                    " under the student's notifications.",
                ],
            },
        ],
    },
    {
        "slug": "managing-accounts",
        "title": "Managing accounts",
        "summary": "Add staff, reset access, and handle people leaving.",
        "audience": "School admins",
        "icon": "bi-person-badge",
        "sections": [
            {
                "heading": "Add a member of staff",
                "steps": [
                    "Open Accounts, then Staff and choose Add staff.",
                    "Set the email address and the role, then save. The member of staff is emailed"
                    " their account details.",
                ],
            },
            {
                "heading": "Suspend or remove an account",
                "paragraphs": [
                    "An account can be suspended, which blocks signing in while keeping the"
                    " record, or removed. A removed account keeps its history, and adding the same"
                    " email address again restores it.",
                ],
            },
            {
                "heading": "Passwords",
                "paragraphs": [
                    "People can change their own password from the account menu. Anyone who has"
                    " forgotten theirs can use the reset link on the sign-in page.",
                ],
            },
        ],
    },
    {
        "slug": "for-parents",
        "title": "For parents and students",
        "summary": "Follow your child's attendance, results and report cards.",
        "audience": "Parents and students",
        "icon": "bi-mortarboard",
        "sections": [
            {
                "heading": "Your portal",
                "paragraphs": [
                    "My portal lists each student linked to your account. Open a student to see"
                    " their results, any online assessment they can sit, and their attendance.",
                ],
            },
            {
                "heading": "Results and report cards",
                "paragraphs": [
                    "Results shows each subject's total by term. A report card can be downloaded"
                    " as a PDF, and these are also emailed to you when the school releases them.",
                ],
            },
            {
                "heading": "Announcements",
                "paragraphs": [
                    "Announcements collects the notices sent to your family and to your child's"
                    " classes.",
                ],
            },
        ],
    },
]

AUDIENCE_ORDER = ["School admins", "Teachers", "Parents and students"]


def guide_by_slug(slug):
    for guide in GUIDES:
        if guide["slug"] == slug:
            return guide
    return None


def grouped_guides():
    """The guides grouped by audience, in a stable order for the index page."""
    groups = []
    for audience in AUDIENCE_ORDER:
        matching = [guide for guide in GUIDES if guide["audience"] == audience]
        if matching:
            groups.append({"audience": audience, "guides": matching})
    return groups
