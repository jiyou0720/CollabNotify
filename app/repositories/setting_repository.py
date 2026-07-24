"""System setting persistence operations."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.setting import Setting


class SettingRepository:
    """Encapsulate global key-value setting access."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def get(self, key: str) -> Setting | None:
        """Find one setting by key."""
        return self._session.scalar(select(Setting).where(Setting.key == key))

    def set(self, key: str, value: str) -> Setting:
        """Create or update one setting."""
        setting = self.get(key)
        if setting is None:
            setting = Setting(key=key, value=value)
            self._session.add(setting)
        else:
            setting.value = value
        self._session.flush()
        return setting

    def delete(self, setting: Setting) -> None:
        """Delete a setting."""
        self._session.delete(setting)
        self._session.flush()
