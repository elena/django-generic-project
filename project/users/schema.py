from typing import cast

import strawberry
import strawberry_django
from allauth.account import app_settings as allauth_settings
from allauth.account.forms import SignupForm
from allauth.account.internal.flows.signup import complete_signup
from django.contrib import auth
from strawberry.types import Info  # noqa: TC002 (strawberry resolves it at runtime)
from strawberry_django.auth.utils import get_current_user
from strawberry_django.permissions import IsAuthenticated
from strawberry_django.utils.requests import get_request

from .models import User


@strawberry_django.type(User)
class UserType:
    id: strawberry.auto
    username: strawberry.auto
    email: strawberry.auto
    name: strawberry.auto
    is_staff: strawberry.auto


@strawberry.type
class FieldError:
    field: str
    messages: list[str]


@strawberry.type
class AuthPayload:
    user: UserType | None = None
    errors: list[FieldError] = strawberry.field(default_factory=list)


@strawberry.type
class Query:
    @strawberry_django.field(extensions=[IsAuthenticated()])
    def me(self, info: Info) -> UserType:
        return cast("UserType", get_current_user(info))


@strawberry.type
class Mutation:
    @strawberry_django.mutation(handle_django_errors=False)
    def login(self, info: Info, login: str, password: str) -> AuthPayload:
        """Log in with a username or an email address (session auth)."""
        request = get_request(info)
        # allauth's AuthenticationBackend tries email and username for `username`.
        user = auth.authenticate(request, username=login, password=password)
        if user is None:
            return AuthPayload(
                errors=[FieldError(field="login", messages=["Invalid credentials."])],
            )
        auth.login(
            request,
            user,
            backend="allauth.account.auth_backends.AuthenticationBackend",
        )
        return AuthPayload(user=cast("UserType", user))

    @strawberry_django.mutation(handle_django_errors=False)
    def logout(self, info: Info) -> bool:
        request = get_request(info)
        was_authenticated = request.user.is_authenticated
        auth.logout(request)
        return was_authenticated

    @strawberry_django.mutation(handle_django_errors=False)
    def register(
        self,
        info: Info,
        username: str,
        email: str,
        password: str,
    ) -> AuthPayload:
        """Sign up through allauth so validation and email verification apply."""
        request = get_request(info)
        form = SignupForm(
            data={
                "username": username,
                "email": email,
                "password1": password,
                "password2": password,
            },
        )
        if not form.is_valid():
            return AuthPayload(
                errors=[
                    FieldError(field=field, messages=[str(m) for m in messages])
                    for field, messages in form.errors.items()
                ],
            )
        user, _ = form.try_save(request)
        if user is None:
            # Email already registered: allauth mailed the owner instead of
            # creating a duplicate, so don't reveal that the account exists.
            return AuthPayload()
        complete_signup(
            request,
            user=user,
            email_verification=allauth_settings.EMAIL_VERIFICATION,
        )
        return AuthPayload(user=cast("UserType", user))
