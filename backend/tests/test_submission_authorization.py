"""Submission routes enforce user ownership and admin-wide listing."""

from __future__ import annotations

from collections.abc import Iterator
from types import SimpleNamespace
from uuid import uuid4

import pytest
from backend.api.dependencies import get_current_user
from backend.api.main import app
from backend.api.routes import submissions as submission_routes
from backend.common.database import get_session
from fastapi.testclient import TestClient


@pytest.fixture
def client() -> Iterator[TestClient]:
    test_client = TestClient(app)
    try:
        yield test_client
    finally:
        app.dependency_overrides.clear()
        test_client.close()


def test_submission_list_is_scoped_to_regular_user(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    user = SimpleNamespace(id=uuid4(), role="user")

    class FakeService:
        requested_user_id = None

        async def list(self, session: object, **kwargs: object) -> tuple[list[object], int]:
            self.requested_user_id = kwargs["user_id"]
            return [], 0

    service = FakeService()
    monkeypatch.setattr(submission_routes, "submissions_service", service)
    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_session] = lambda: object()

    response = client.get("/submissions")

    assert response.status_code == 200
    assert service.requested_user_id == user.id


def test_admin_submission_list_is_not_user_scoped(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    class FakeService:
        requested_user_id = "unset"

        async def list(self, session: object, **kwargs: object) -> tuple[list[object], int]:
            self.requested_user_id = kwargs["user_id"]
            return [], 0

    service = FakeService()
    monkeypatch.setattr(submission_routes, "submissions_service", service)
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(
        id=uuid4(), role="admin"
    )
    app.dependency_overrides[get_session] = lambda: object()

    response = client.get("/submissions")

    assert response.status_code == 200
    assert service.requested_user_id is None


def test_submission_detail_hides_another_users_record(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    class FakeService:
        async def get(self, session: object, submission_id: object) -> object:
            return SimpleNamespace(user_id=uuid4())

    monkeypatch.setattr(submission_routes, "submissions_service", FakeService())
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(
        id=uuid4(), role="user"
    )
    app.dependency_overrides[get_session] = lambda: object()

    response = client.get(f"/submissions/{uuid4()}")

    assert response.status_code == 404


def test_submission_creation_requires_authentication(client: TestClient) -> None:
    response = client.post(
        "/submissions",
        json={"problem_id": str(uuid4()), "source_code": "print(1)"},
    )

    assert response.status_code == 401


def test_regular_user_cannot_list_administrative_accounts(client: TestClient) -> None:
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(
        id=uuid4(), role="user"
    )
    app.dependency_overrides[get_session] = lambda: object()

    response = client.get("/admin/users")

    assert response.status_code == 403
