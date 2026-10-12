"""Automated tests for BankSim Authentication and RBAC (Phase 3)."""

from datetime import timedelta
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from database import Base, get_db, set_sqlite_pragma, seed_demo_data
from main import app
from models import User, UserRole
from security.login_tracker import login_tracker
from security.passwords import hash_password
from security.tokens import create_access_token
from services.verification_service import otp_provider


@pytest.fixture
def auth_fixture():
    """Isolated in-memory test database and TestClient with session dependency override."""
    test_engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        future=True,
    )
    event.listen(test_engine, "connect", set_sqlite_pragma)
    Base.metadata.create_all(bind=test_engine)

    TestingSession = sessionmaker(
        autocommit=False, autoflush=False, bind=test_engine
    )

    def override_get_db():
        session = TestingSession()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = override_get_db
    login_tracker.reset()

    session = TestingSession()
    client = TestClient(app)

    yield client, session

    session.close()
    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=test_engine)
    test_engine.dispose()
    login_tracker.reset()


def test_login_successful(auth_fixture):
    """Test mandatory OTP flow: credentials return challenge, OTP verification issues token."""
    client, session = auth_fixture
    password_plain = "CorrectHorseBatteryStaple99!"
    user = User(
        username="alice_auth",
        email="alice.auth@banksim.local",
        password_hash=hash_password(password_plain),
        role=UserRole.USER.value,
        is_active=True,
    )
    session.add(user)
    session.commit()

    # Step 1: Submit credentials -> returns OTP_REQUIRED challenge, NO access_token
    response = client.post(
        "/api/v1/auth/login",
        json={"username": "alice_auth", "password": password_plain},
    )
    assert response.status_code == 200
    challenge_data = response.json()
    assert challenge_data["status"] == "OTP_REQUIRED"
    assert "challenge_id" in challenge_data
    assert "access_token" not in challenge_data
    # Password hash must NEVER appear in API response
    assert "password_hash" not in challenge_data
    assert user.password_hash not in response.text

    # Step 2: Retrieve delivered OTP and verify
    ch_id = challenge_data["challenge_id"]
    code = otp_provider.get_dev_otp(ch_id)
    assert code is not None

    verify_resp = client.post(
        "/api/v1/auth/verify-otp",
        json={"challenge_id": ch_id, "verification_code": code},
    )
    assert verify_resp.status_code == 200
    token_data = verify_resp.json()
    assert "access_token" in token_data
    assert token_data["token_type"] == "bearer"
    assert token_data["role"] == "USER"
    assert token_data["user_id"] == user.id


def test_login_incorrect_password_generic_error(auth_fixture):
    """Test incorrect password returns generic 401 error."""
    client, session = auth_fixture
    user = User(
        username="bob_auth",
        email="bob.auth@banksim.local",
        password_hash=hash_password("ValidPassword123!"),
        role=UserRole.USER.value,
        is_active=True,
    )
    session.add(user)
    session.commit()

    response = client.post(
        "/api/v1/auth/login",
        json={"username": "bob_auth", "password": "WrongPassword999!"},
    )
    assert response.status_code == 401
    data = response.json()
    assert data["detail"] == "Invalid username or password."
    assert "WWW-Authenticate" in response.headers


def test_login_nonexistent_user_generic_error(auth_fixture):
    """Test nonexistent username returns identical generic 401 error (no user enumeration)."""
    client, session = auth_fixture
    response = client.post(
        "/api/v1/auth/login",
        json={"username": "ghost_user_999", "password": "AnyPassword123!"},
    )
    assert response.status_code == 401
    data = response.json()
    assert data["detail"] == "Invalid username or password."


def test_login_inactive_user_rejected(auth_fixture):
    """Test inactive account cannot authenticate."""
    client, session = auth_fixture
    password_plain = "ActivePassword123!"
    user = User(
        username="disabled_user",
        email="disabled@banksim.local",
        password_hash=hash_password(password_plain),
        role=UserRole.USER.value,
        is_active=False,
    )
    session.add(user)
    session.commit()

    response = client.post(
        "/api/v1/auth/login",
        json={"username": "disabled_user", "password": password_plain},
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid username or password."


def test_login_rate_limiting_lockout(auth_fixture):
    """Test repeated failed attempts trigger brute-force lockout (429)."""
    client, session = auth_fixture
    username = "target_account"
    user = User(
        username=username,
        email="target@banksim.local",
        password_hash=hash_password("RealPassword123!"),
        role=UserRole.USER.value,
    )
    session.add(user)
    session.commit()

    # Fail 5 consecutive times
    for _ in range(5):
        resp = client.post(
            "/api/v1/auth/login",
            json={"username": username, "password": "BadPassword!"},
        )
        assert resp.status_code == 401

    # 6th attempt must be locked out
    lockout_resp = client.post(
        "/api/v1/auth/login",
        json={"username": username, "password": "BadPassword!"},
    )
    assert lockout_resp.status_code == 429
    assert "too many failed login attempts" in lockout_resp.json()["detail"].lower()


def test_unauthenticated_access_rejected(auth_fixture):
    """Test unauthenticated access to protected user and admin endpoints returns 401."""
    client, _ = auth_fixture
    # Protected user endpoint
    resp_user = client.get("/api/v1/users/me")
    assert resp_user.status_code == 401
    assert "authentication required" in resp_user.json()["detail"].lower()

    # Protected admin endpoint
    resp_admin = client.get("/api/v1/admin/dashboard")
    assert resp_admin.status_code == 401
    assert "authentication required" in resp_admin.json()["detail"].lower()


def test_invalid_and_tampered_token_rejected(auth_fixture):
    """Test invalid or tampered JWT token returns 401."""
    client, _ = auth_fixture

    # Garbage token
    resp_garbage = client.get(
        "/api/v1/users/me",
        headers={"Authorization": "Bearer not-a-valid-token-string"},
    )
    assert resp_garbage.status_code == 401

    # Tampered token
    valid_token = create_access_token({"sub": "1", "username": "alice", "role": "USER"})
    tampered_token = valid_token[:-4] + "xxxx"
    resp_tampered = client.get(
        "/api/v1/users/me",
        headers={"Authorization": f"Bearer {tampered_token}"},
    )
    assert resp_tampered.status_code == 401


def test_expired_token_rejected(auth_fixture):
    """Test expired token returns 401."""
    client, session = auth_fixture
    user = User(
        username="timetravel_user",
        email="timetravel@banksim.local",
        password_hash=hash_password("Pass123!"),
        role=UserRole.USER.value,
    )
    session.add(user)
    session.commit()

    # Token with negative lifetime (already expired)
    expired_token = create_access_token(
        {"sub": str(user.id), "username": user.username, "role": user.role},
        expires_delta=timedelta(seconds=-30),
    )
    response = client.get(
        "/api/v1/users/me",
        headers={"Authorization": f"Bearer {expired_token}"},
    )
    assert response.status_code == 401
    assert "expired" in response.json()["detail"].lower()


def test_user_ownership_boundaries(auth_fixture):
    """Test user can access their own data, but is forbidden (403) from accessing another user's data."""
    client, session = auth_fixture
    user1 = User(
        username="customer_one",
        email="one@banksim.local",
        password_hash=hash_password("Pass1!"),
        role=UserRole.USER.value,
    )
    user2 = User(
        username="customer_two",
        email="two@banksim.local",
        password_hash=hash_password("Pass2!"),
        role=UserRole.USER.value,
    )
    session.add_all([user1, user2])
    session.commit()

    token_user1 = create_access_token(
        {"sub": str(user1.id), "username": user1.username, "role": user1.role}
    )
    headers1 = {"Authorization": f"Bearer {token_user1}"}

    # User 1 accesses /me -> succeeds
    me_resp = client.get("/api/v1/users/me", headers=headers1)
    assert me_resp.status_code == 200
    assert me_resp.json()["username"] == "customer_one"
    assert "password_hash" not in me_resp.json()

    # User 1 accesses /users/1 -> succeeds
    own_resp = client.get(f"/api/v1/users/{user1.id}", headers=headers1)
    assert own_resp.status_code == 200
    assert own_resp.json()["id"] == user1.id

    # User 1 accesses /users/2 -> 403 Forbidden!
    foreign_resp = client.get(f"/api/v1/users/{user2.id}", headers=headers1)
    assert foreign_resp.status_code == 403
    assert "forbidden" in foreign_resp.json()["detail"].lower()


def test_user_denied_admin_access(auth_fixture):
    """Test regular USER receives 403 Forbidden when accessing admin endpoints."""
    client, session = auth_fixture
    user = User(
        username="regular_user",
        email="regular@banksim.local",
        password_hash=hash_password("Pass123!"),
        role=UserRole.USER.value,
    )
    session.add(user)
    session.commit()

    token = create_access_token(
        {"sub": str(user.id), "username": user.username, "role": user.role}
    )
    headers = {"Authorization": f"Bearer {token}"}

    # Attempt to access admin dashboard
    dash_resp = client.get("/api/v1/admin/dashboard", headers=headers)
    assert dash_resp.status_code == 403
    assert "requires admin privileges" in dash_resp.json()["detail"].lower()

    # Attempt to access security events log
    events_resp = client.get("/api/v1/admin/security-events", headers=headers)
    assert events_resp.status_code == 403
    assert "requires admin privileges" in events_resp.json()["detail"].lower()


def test_admin_permitted_admin_access(auth_fixture):
    """Test ADMIN role user successfully accesses admin endpoints."""
    client, session = auth_fixture
    admin = User(
        username="sec_admin",
        email="admin@banksim.local",
        password_hash=hash_password("AdminSecurePass999!"),
        role=UserRole.ADMIN.value,
    )
    session.add(admin)
    session.commit()

    token = create_access_token(
        {"sub": str(admin.id), "username": admin.username, "role": admin.role}
    )
    headers = {"Authorization": f"Bearer {token}"}

    # Access admin dashboard
    dash_resp = client.get("/api/v1/admin/dashboard", headers=headers)
    assert dash_resp.status_code == 200
    data = dash_resp.json()
    assert data["status"] == "operational"
    assert data["admin_username"] == "sec_admin"
    assert data["role"] == "ADMIN"
    assert "metrics" in data

    # Access security events list
    events_resp = client.get("/api/v1/admin/security-events", headers=headers)
    assert events_resp.status_code == 200
    assert isinstance(events_resp.json(), list)


def test_admin_cannot_access_other_users_account_boundary(auth_fixture):
    """Test ADMIN privileges do not bypass user ownership boundary on user endpoints."""
    client, session = auth_fixture
    admin = User(
        username="super_admin",
        email="super.admin@banksim.local",
        password_hash=hash_password("SuperAdmin123!"),
        role=UserRole.ADMIN.value,
    )
    customer = User(
        username="innocent_customer",
        email="customer@banksim.local",
        password_hash=hash_password("Customer123!"),
        role=UserRole.USER.value,
    )
    session.add_all([admin, customer])
    session.commit()

    admin_token = create_access_token(
        {"sub": str(admin.id), "username": admin.username, "role": admin.role}
    )
    headers = {"Authorization": f"Bearer {admin_token}"}

    # Admin trying to inspect customer via user profile endpoint is rejected (403)
    resp = client.get(f"/api/v1/users/{customer.id}", headers=headers)
    assert resp.status_code == 403
    assert "forbidden" in resp.json()["detail"].lower()


def test_seeded_demo_accounts_login(auth_fixture):
    """Regression Test: Seeded demo accounts (sec_admin, alice, bob) authenticate successfully."""
    client, session = auth_fixture

    # Execute idempotent seed
    seed_result = seed_demo_data(session)
    assert "sec_admin" in seed_result["users_created"]
    assert "alice" in seed_result["users_created"]
    assert "bob" in seed_result["users_created"]

    # 1. Login as sec_admin (ADMIN role requires mandatory OTP)
    admin_login = client.post(
        "/api/v1/auth/login",
        json={"username": "sec_admin", "password": "AdminSecurePass999!"},
    )
    assert admin_login.status_code == 200
    admin_ch = admin_login.json()
    assert admin_ch["status"] == "OTP_REQUIRED"
    assert "access_token" not in admin_ch
    admin_code = otp_provider.get_dev_otp(admin_ch["challenge_id"])
    assert admin_code is not None

    admin_verify = client.post(
        "/api/v1/auth/verify-otp",
        json={"challenge_id": admin_ch["challenge_id"], "verification_code": admin_code},
    )
    assert admin_verify.status_code == 200
    admin_data = admin_verify.json()
    assert admin_data["role"] == "ADMIN"
    assert "access_token" in admin_data

    # 2. Login as alice (USER role requires mandatory OTP)
    alice_login = client.post(
        "/api/v1/auth/login",
        json={"username": "alice", "password": "SecurePass123!"},
    )
    assert alice_login.status_code == 200
    alice_ch = alice_login.json()
    assert alice_ch["status"] == "OTP_REQUIRED"
    assert "access_token" not in alice_ch
    alice_code = otp_provider.get_dev_otp(alice_ch["challenge_id"])
    assert alice_code is not None

    alice_verify = client.post(
        "/api/v1/auth/verify-otp",
        json={"challenge_id": alice_ch["challenge_id"], "verification_code": alice_code},
    )
    assert alice_verify.status_code == 200
    alice_data = alice_verify.json()
    assert alice_data["role"] == "USER"
    assert "access_token" in alice_data

    # 3. Running seed a second time is non-destructive
    second_seed = seed_demo_data(session)
    assert "sec_admin" in second_seed["users_preserved"]
    assert "alice" in second_seed["users_preserved"]


def test_unseeded_user_login_returns_401_not_500(auth_fixture):
    """Regression Test: Initialized database with missing user returns 401, never 500 error."""
    client, _ = auth_fixture

    # Request with non-existent credentials against initialized tables
    resp = client.post(
        "/api/v1/auth/login",
        json={"username": "non_existent_user", "password": "AnyPassword123!"},
    )
    assert resp.status_code == 401
    assert resp.json()["detail"] == "Invalid username or password."

