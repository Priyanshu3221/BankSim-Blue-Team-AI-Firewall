"""In-memory login attempt tracker to mitigate brute-force authentication attacks."""

from datetime import datetime, timedelta, timezone
from typing import Dict, List

from config import get_settings


class LoginAttemptTracker:
    """Tracks failed login attempts and applies temporary lockout per username."""

    def __init__(self, lockout_window_minutes: int = 15) -> None:
        self.lockout_window = timedelta(minutes=lockout_window_minutes)
        self._attempts: Dict[str, List[datetime]] = {}

    def _prune(self, username: str, now: datetime) -> None:
        """Remove attempts outside the active lockout window."""
        key = username.strip().lower()
        if key in self._attempts:
            cutoff = now - self.lockout_window
            self._attempts[key] = [t for t in self._attempts[key] if t > cutoff]
            if not self._attempts[key]:
                del self._attempts[key]

    def is_locked(self, username: str) -> bool:
        """Check if a username has exceeded maximum permitted consecutive failures."""
        settings = get_settings()
        now = datetime.now(timezone.utc)
        self._prune(username, now)
        key = username.strip().lower()
        failures = len(self._attempts.get(key, []))
        return failures >= settings.MAX_LOGIN_ATTEMPTS

    def record_failure(self, username: str) -> int:
        """Record a failed login attempt and return total recent failures."""
        now = datetime.now(timezone.utc)
        self._prune(username, now)
        key = username.strip().lower()
        if key not in self._attempts:
            self._attempts[key] = []
        self._attempts[key].append(now)
        return len(self._attempts[key])

    def record_success(self, username: str) -> None:
        """Clear recorded failures upon successful authentication."""
        key = username.strip().lower()
        self._attempts.pop(key, None)

    def reset(self) -> None:
        """Reset all tracked state (useful for test isolation)."""
        self._attempts.clear()


# Global tracker instance
login_tracker = LoginAttemptTracker()
