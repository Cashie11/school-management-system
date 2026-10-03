from .context import school_context


class TenantContextMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        school_id = None
        user = getattr(request, "user", None)
        if user is not None and user.is_authenticated:
            if user.is_super_admin:
                # Super Admins have no school of their own. They opt into a tenant
                # by selecting one, which is stored on the session.
                school_id = request.session.get("active_school_id")
            else:
                school_id = user.school_id
        request.school_id = school_id
        with school_context(school_id):
            return self.get_response(request)
