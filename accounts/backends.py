from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend


class EmailBackend(ModelBackend):
    """Authenticate by email, allowing suspended and removed accounts through so
    the login form can explain why they cannot sign in.

    Only a correct password reaches this point. Session loading still rejects
    inactive and removed accounts, so an existing session ends on the next
    request.
    """

    def authenticate(self, request, username=None, password=None, **kwargs):
        UserModel = get_user_model()
        if username is None:
            username = kwargs.get(UserModel.USERNAME_FIELD)
        if username is None or password is None:
            return None

        try:
            user = UserModel._default_manager.get_by_natural_key(username)
        except UserModel.DoesNotExist:
            # Run the hasher once so a missing account and a wrong password take
            # a similar amount of time.
            UserModel().set_password(password)
            return None

        if user.check_password(password):
            return user
        return None

    def get_user(self, user_id):
        user = super().get_user(user_id)
        if user is not None and user.removed_at is not None:
            return None
        return user
