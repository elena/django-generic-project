# ruff: noqa: S105, S106
from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from django.core import mail
from django.urls import reverse

from project.users.models import User
from project.users.tests.factories import UserFactory

if TYPE_CHECKING:
    from django.test import Client

pytestmark = pytest.mark.django_db

PASSWORD = "s3cret-Passw0rd!"

ME = "{ me { username email } }"
LOGIN = """
mutation($login: String!, $password: String!) {
  login(login: $login, password: $password) {
    user { username }
    errors { field messages }
  }
}
"""
REGISTER = """
mutation($username: String!, $email: String!, $password: String!) {
  register(username: $username, email: $email, password: $password) {
    user { username email }
    errors { field messages }
  }
}
"""


def gql(client: Client, query: str, **variables):
    response = client.post(
        reverse("graphql"),
        {"query": query, "variables": variables},
        content_type="application/json",
    )
    assert response.status_code == 200  # noqa: PLR2004
    return response.json()


def test_me_anonymous(client: Client):
    result = gql(client, ME)
    assert result["data"] is None
    assert "not authenticated" in result["errors"][0]["message"].lower()


def test_me_authenticated(client: Client, user: User):
    client.force_login(user)
    assert gql(client, ME)["data"]["me"] == {
        "username": user.username,
        "email": user.email,
    }


@pytest.mark.parametrize("field", ["username", "email"])
def test_login_with_username_or_email(client: Client, field: str):
    user = UserFactory.create(password=PASSWORD)
    result = gql(client, LOGIN, login=getattr(user, field), password=PASSWORD)
    assert result["data"]["login"] == {
        "user": {"username": user.username},
        "errors": [],
    }
    assert gql(client, ME)["data"]["me"]["username"] == user.username


def test_login_bad_password(client: Client, user: User):
    result = gql(client, LOGIN, login=user.username, password="wrong")
    assert result["data"]["login"]["user"] is None
    assert result["data"]["login"]["errors"][0]["field"] == "login"


def test_register(client: Client):
    result = gql(
        client,
        REGISTER,
        username="newbie",
        email="newbie@example.com",
        password=PASSWORD,
    )
    assert result["data"]["register"]["errors"] == []
    assert User.objects.filter(username="newbie").exists()
    # Verification is optional: the user is logged in and a confirmation is mailed.
    assert gql(client, ME)["data"]["me"]["username"] == "newbie"
    assert len(mail.outbox) == 1


def test_register_invalid(client: Client, user: User):
    result = gql(
        client,
        REGISTER,
        username=user.username,
        email="bad",
        password="x",
    )
    fields = {e["field"] for e in result["data"]["register"]["errors"]}
    assert {"username", "email"} <= fields
