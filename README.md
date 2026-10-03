# School Management System

Multi-tenant Django application for running schools. Each school is a tenant in a shared
PostgreSQL database. Tenant isolation is enforced at the query layer and covered by tests.

## Stack

- Django 5.2
- PostgreSQL 16 (SQLite is used automatically for local development and tests)
- Django templates with HTMX for interactive tables and forms
- Celery with Redis for background email delivery
- ReportLab for report card PDFs

## Local Setup

Install Python 3.12 or later. You need a PostgreSQL 16 database, or you can run on SQLite
by leaving `POSTGRES_HOST` empty.

Create a database and user, for example in `psql` as a PostgreSQL administrator:

```sql
CREATE USER school_management WITH PASSWORD 'choose-a-private-password';
CREATE DATABASE school_management OWNER school_management;
```

Then, from PowerShell in the project directory:

```powershell
Copy-Item .env.example .env
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
py manage.py migrate
py manage.py test
py manage.py runserver
```

The application is available at `http://localhost:8000/`.

### Running PostgreSQL in Docker

If you do not have PostgreSQL installed, a throwaway instance is enough:

```powershell
docker run -d --name school_pg -e POSTGRES_DB=school_management `
  -e POSTGRES_USER=school_management -e POSTGRES_PASSWORD=school_management `
  -p 5432:5432 postgres:16
```

Remove it later with `docker rm -f school_pg`.

### Full stack with Docker Compose

`docker-compose.yml` runs the application and PostgreSQL together, production-shaped: the
web container collects static files, applies migrations, then serves the app with gunicorn.
`DJANGO_SECRET_KEY` must be set (it reads your `.env`), and uploaded logos live in a named
volume so they survive a rebuild.

```powershell
docker compose up --build
```

The application is then available at `http://localhost:8000/`. Stop it with
`docker compose down`; add `-v` to also delete the database and media volumes.

## Deploying

The image runs `gunicorn` using `gunicorn.conf.py`. Worker count, threads, timeouts and the
log level all come from environment variables.

Static files and uploaded logos are served by **WhiteNoise from the WSGI application**, so
no separate web server is needed for them. `collectstatic` must run before the app starts
(the compose command does this).

```powershell
py manage.py collectstatic --noinput
gunicorn config.wsgi:application -c gunicorn.conf.py
```

Worth knowing before a real deployment:

- **`DJANGO_SECRET_KEY` is required** once `DJANGO_DEBUG` is off; the application refuses to
  start without it.
- **`DJANGO_ALLOWED_HOSTS`** must list your domain, as bare host names with no
  scheme, port or path (`school.example.com`). A full URL is tolerated and
  normalised, and a host added to `DJANGO_CSRF_TRUSTED_ORIGINS` is allowed
  automatically, so the common `DisallowedHost` mistake cannot happen.
- Set **`DJANGO_SECURE_SSL_REDIRECT=1`** and terminate TLS at your proxy once a certificate
  exists, and add the public origin to **`DJANGO_CSRF_TRUSTED_ORIGINS`**. gunicorn trusts
  `X-Forwarded-Proto` from `127.0.0.1`; widen `GUNICORN_FORWARDED_ALLOW_IPS` if your proxy
  runs elsewhere.
- **`DJANGO_MEDIA_ROOT`** can point at a mounted volume or network share. Move it to object
  storage if one disk is not enough.
- Database connections are reused (`POSTGRES_CONN_MAX_AGE`) and health-checked, and the
  queries behind the dashboards and report cards are aggregated instead of per-row.
- **Notifications need a worker**: run `celery -A config worker` alongside gunicorn, with
  `CELERY_BROKER_URL` pointing at Redis. Run `celery -A config beat` too, which triggers the
  scheduled cleanup of expired announcements. The compose stack includes both.
- For a heavier install, raise `GUNICORN_WORKERS` to match the available cores and give
  PostgreSQL its own host.

## Environment Variables

| Variable | Purpose |
| --- | --- |
| `DJANGO_SECRET_KEY` | Signing key. Set a private value outside development. |
| `DJANGO_DEBUG` | `1` enables debug mode. Defaults to off. |
| `DJANGO_ALLOWED_HOSTS` | Comma separated host names. Bare hosts; URLs are normalised. |
| `DJANGO_USE_SQLITE` | `1` forces SQLite even when `POSTGRES_HOST` is set. |
| `POSTGRES_DB` | Database name. |
| `POSTGRES_USER` | Database user. |
| `POSTGRES_PASSWORD` | Database password. |
| `POSTGRES_HOST` | Database host. Leave empty to use SQLite. |
| `POSTGRES_PORT` | Database port. Defaults to `5432`. |
| `POSTGRES_CONN_MAX_AGE` | Seconds to reuse a database connection. Defaults to `60`. |
| `DJANGO_MEDIA_ROOT` | Where uploaded logos are stored. Defaults to `media/`. |
| `DJANGO_CSRF_TRUSTED_ORIGINS` | Comma separated origins for CSRF over HTTPS. Their hosts are added to `DJANGO_ALLOWED_HOSTS`. |
| `DJANGO_LOG_LEVEL` | Root log level. Defaults to `INFO`. |
| `GUNICORN_WORKERS` / `GUNICORN_THREADS` | gunicorn process and thread counts. |
| `CELERY_BROKER_URL` | Redis broker for background email. |
| `CELERY_TASK_ALWAYS_EAGER` | `1` runs tasks inline instead of queueing them. Defaults to on while `DEBUG` is on or during tests. |
| `EMAIL_BACKEND` | Django email backend. Defaults to the console backend. |
| `EMAIL_HOST` / `EMAIL_PORT` | SMTP server. |
| `EMAIL_HOST_USER` / `EMAIL_HOST_PASSWORD` | SMTP credentials. |
| `EMAIL_USE_TLS` | Use TLS for SMTP. Defaults to on. |
| `DEFAULT_FROM_EMAIL` | Sender address for notifications. |

To run the suite against SQLite on a machine where `.env` points at PostgreSQL:

```powershell
$env:DJANGO_USE_SQLITE="1"; py manage.py test
```

## Architecture

### Tenancy

- `School` is the tenant record. Its slug is unique and it is not tenant-owned.
- `TenantModel` is the abstract base for every school-owned model. It adds the `school`
  foreign key and a scoped default manager.
- `TenantManager` limits every read to the active school and returns no rows when no
  school context is active. `base_manager_name` points at the same manager so
  related-object access (`school.enrollments`) is scoped too.
- Writes require a matching context: `TenantModel.save` fills the school from the active
  context or raises when the record belongs to another school.
- `TenantContextMiddleware` resolves the active school from the authenticated user. Super
  Admins have no school of their own and establish one by selecting it; the choice is kept
  on the session.
- `TenantModelForm` assigns the school before validation, so per-school uniqueness is
  reported as a form error rather than a database error, and re-scopes tenant foreign-key
  choices on every request.
- `school_context` is available for controlled operations such as onboarding, background
  work and tests.

### Roles

The custom `User` authenticates by unique email. Email login is case-insensitive.

| Role | Can do |
| --- | --- |
| Super Admin | Manage the platform and open any school workspace. |
| School Admin | Everything inside one school: academics, students, accounts, attendance, results. |
| Teacher | Their own classes only: view students, take attendance, author assessments, enter scores and mark theory, view report cards. |
| Parent/Student | See the students linked to their account, sit online assessments, and view results and attendance. |

A database constraint requires school accounts to belong to exactly one school and
requires Super Admin accounts to have no school.

## Applications

| App | Responsibility |
| --- | --- |
| `tenancy` | `School`, tenant context, manager and middleware. |
| `accounts` | Custom user, roles, authentication, school onboarding and account management. |
| `academics` | Academic terms, subjects, classes and teacher assignments. |
| `students` | Student records, per-term enrollment history and guardians. |
| `attendance` | Daily attendance register and records. |
| `results` | Assessments, scores, online questions and report cards. |
| `portal` | Parent/Student facing views: assessments, results and attendance. |
| `announcements` | Notices shown to staff, families or a single class. |
| `notifications` | Email notifications and the outbound email log. |
| `dashboard` | Role-based dashboards and class workspace. |
| `core` | Shared templates, design system, permissions and CRUD helpers. |

## Using the system

A typical setup order for a new school:

1. **Academics** — add terms, subjects and classes, then assign a teacher to each class
   subject under **Teacher assignments**.
2. **Accounts** — add staff (School Admin or Teacher) and parent accounts. Creating a
   parent account also links it to a student.
3. **Students** — add student records and enroll each student in a class for a term.
4. **Attendance** — open **Daily register**, choose a class (or *All classes*) and a date,
   mark each student and save.
5. **Results** — create assessments, then either enter marks directly or let students sit
   them online, and produce report cards.

### Online assessments

An assessment has a **mode**:

- **Teacher enters marks** — you type each student's score on the **Scores** screen.
- **Students answer online** — you author questions, publish, and students sit it.

For online assessments:

1. Create the assessment with mode *Students answer online*, and set the availability
   window and optional time limit.
2. Add an **Objective** question, then add its options and tick the correct one.
3. Optionally add a **Theory** question (free text).
4. **Publish**. Total question points become the assessment's maximum score.
5. Students start it from **My portal**, answer, and submit. Objective answers are marked
   automatically; the attempt auto-submits when the time limit expires.
6. Under **Submissions**, mark the theory answers. Saving completes the attempt and writes
   the total to the report card. **Reset** lets a student sit it again.

Grade scale: A 80+, B 70+, C 60+, D 50+, E 40+, F below.

### Announcements

Notices are shown in the app rather than emailed, which suits things that are useful but not
urgent.

| Audience | Who sees it |
| --- | --- |
| **Everyone** | The whole school |
| **Teachers** | Staff only |
| **Parents and Students** | Families only |
| A **class** | The families of that class, and its teachers |

- School Admins can address any audience, with or without a class.
- **Teachers can only post to their own classes**, and only to that class's families. They
  cannot broadcast to the whole school, and the form enforces it rather than the template.
- A teacher can only edit or delete notices they created for their own classes.
- **Pinned** notices sort first. An optional **expiry** hides a notice immediately, and a
  scheduled task (**`purge_expired_announcements`**, hourly) then **deletes** it. Run the
  same cleanup on demand with `py manage.py purge_expired_announcements`.
- Announcements appear on the Super Admin, School Admin, teacher and parent dashboards, and
  on their own page from the navigation.

### Notifications

Emails are **queued through Celery**, so a slow or unreachable mail server never holds up
the request that triggered the message. Each notification is a task in
`notifications/tasks.py`; the worker loads the record, sets the school context and sends.

Without a broker configured the tasks run **inline**, which is what development and the
test suite use — no Redis needed locally. In production set `CELERY_BROKER_URL` and run a
worker:

```powershell
celery -A config worker --loglevel=info --concurrency=4
```

The school emails families automatically. Every message is sent as plain text with an HTML
alternative, and a record is kept in `notifications.EmailLog` and shown on the student's
page.

| Email | Sent when | Recipients |
| --- | --- | --- |
| Student welcome | A student record is created | The student's email, otherwise linked guardians |
| Account welcome | A staff account is created | That account |
| Guardian linked | A parent account is linked to a student | The guardian's account |
| Enrollment | A student is enrolled in a class | The student and all guardians |
| Absence alert | A student is first marked absent for a day | The student and all guardians |
| Assessment published | An online assessment is published | Every enrolled student |
| Assessment result | An online assessment is fully marked | The student and all guardians |
| Results | A staff member clicks **Email results** on a report card | The student and all guardians |
| Disciplinary notice | A sanction is recorded (warning, suspension, expulsion) | The student and all guardians |

Student mail goes to the student's own address when one is on file, and always copies
linked guardians. If no address exists anywhere, nothing is sent and the request is
unaffected. Absence alerts are only sent when a day first becomes absent, so re-saving a
register does not resend them.

Out of the box the console backend is used, so messages print to the server log. To send
real mail, set `EMAIL_BACKEND` to `django.core.mail.backends.smtp.EmailBackend` and fill in
the `EMAIL_*` settings.

Disciplinary records are managed under **Students -> Discipline** and appear on the
student's page.

### Health check

`/health` and `/health/` return `{"status": "ok"}` with a database round trip, or a `503`
when the database is unreachable.

### School logo and brand

A school can upload a logo while registering, and change it later from the account menu
(**School profile**), which also edits the school name and contact email.

Accepted files:

- **PNG, JPEG or WEBP**
- A **square** image works best (it is displayed in a rounded 32 x 32 square)
- At least **64 x 64 pixels**, at most **2 MB**
- **SVG is rejected**, because it can carry scripts

The header shows the school's logo and name for anyone working inside a school, and falls
back to a neutral mark on platform screens where no school is selected.

### Password reset and change

- **Forgot your password?** on the sign-in page emails a one-time reset link. The link
  expires after three days and cannot be reused.
- Reset mail is only sent to **active** accounts. Suspended and removed accounts receive
  nothing, so a disabled account cannot be recovered this way.
- The form gives the same response for a known and an unknown address, so it cannot be used
  to discover which emails have accounts.
- Signed-in users can change their own password from the account menu.
- With the default console email backend the link is printed to the server log. Configure
  the `EMAIL_*` settings to deliver it for real.

### Admin
The Django admin is a platform-operator tool and the only way to reach it is with a
superuser account (`manage.py createsuperuser`). School Admins are not staff, so they use
the application's own screens instead.

A **Super Admin sees every school's data at once**: lists are unfiltered, there is a school
filter on each list, and the owner is chosen on the form, so records can be created for any
school. Tenant foreign keys (student, class, term and so on) are populated across all
schools.

Any other staff account stays **scoped to the active school**, chosen from
Platform -> Schools. Without one selected they see an explanatory message and cannot add or
edit, so tenant data can never leak between schools.

## Design

The interface follows the reference design at `https://tabella-phenomenon.netlify.app/`:
the Red Hat Display typeface, warm grey surfaces, deep charcoal elements and a single lime
accent. The tokens live in `static/css/app.css`. There are no gradients and no
glassmorphism. HTMX is vendored at `static/vendor/htmx.min.js` so there is no runtime CDN
dependency.

## Security

### Production checklist

- **`DJANGO_SECRET_KEY` is required when `DJANGO_DEBUG` is off.** The application refuses
  to start with the development fallback key, so a deployment cannot silently ship with a
  known signing key.
- The strict HTTPS and cookie settings turn on automatically when `DEBUG` is off:
  `SECURE_SSL_REDIRECT`, `SESSION_COOKIE_SECURE`, `CSRF_COOKIE_SECURE`, HSTS for one year
  including subdomains. Each can be overridden with a `DJANGO_*` environment variable, which
  is what you need behind a proxy or when terminating TLS elsewhere.
- `SECURE_HSTS_PRELOAD` stays off. Submitting to the browser preload list is effectively
  irreversible, so it is opt-in.
- `manage.py check --deploy` reports one remaining warning, the preload setting above.

### Access control

- Every school-owned model is filtered by the active school at the query layer, including
  related-object access.
- The unscoped `all_objects` manager exists for one reason: the platform admin. It is used
  only in `core/admin.py`, and no application code touches it.
- School Admins cannot suspend or remove themselves, and a school can never be left without
  an active School Admin.
- Teachers see only their own classes, students and assessments; the server enforces this,
  not just the templates.
- Parents reach only the students linked to their account; anything else is a 404.

### Input handling

- Values from a query string or form are never passed straight into a numeric lookup; a
  malformed `?school_class=abc` returns the page, not a server error.
- Uploaded logos are validated server-side: real image, PNG/JPEG/WEBP, at least 64 x 64,
  at most 2 MB. SVG is refused because it can carry scripts, and images large enough to
  exhaust memory are rejected rather than decoded.
- Every POST form carries a CSRF token, and state-changing actions are POST-only.

### Accepted trade-offs

- **Registration reveals whether an email is already registered.** This is deliberate: the
  alternative is a confusing signup failure. The password reset form does not leak the same
  information.
- **No rate limiting on the password reset form.** Django has none built in. Add a throttle
  at the web server or a reverse proxy if the site is public.
- Notifications never raise. A failure to render or send one is logged and the request
  continues, so a mail problem cannot block a student being created.

## Testing
Tests live beside each app. They cover the tenant guarantees directly:

- Reads are limited to the active school and return nothing without a context.
- Related-object access is scoped.
- Cross-school writes raise `ValueError`; cross-school reads return 404.
- Uniqueness constraints are per school and surface as form errors.
- Role permissions for staff, teachers and parents.
- The full online assessment flow, including auto-marking and manual theory marking.

```powershell
py manage.py test
```

The suite passes on both SQLite and PostgreSQL 16.

## Notes

Tenant-owned records must not be queried through unscoped managers. Keep tenant
relationships on the same school and add tenant isolation tests whenever tenant-owned
models are introduced.
