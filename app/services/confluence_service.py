"""Outbound Confluence Cloud operations used by the Discord workflow."""

from __future__ import annotations

import html

import httpx

from app.config.settings import ConfluenceConfig


class ConfluenceService:
    """Write audit comments and machine-readable approval state."""

    PROPERTY_KEY = "collabnotify.review"

    def __init__(
        self, config: ConfluenceConfig, client: httpx.AsyncClient | None = None
    ) -> None:
        self._config = config
        self._client = client

    async def add_comment(self, page_id: str, text: str) -> str:
        """Post a safe plain-text message as a Confluence footer comment."""
        payload = {
            "type": "comment",
            "container": {"id": page_id, "type": "page"},
            "body": {
                "storage": {
                    "value": f"<p>{html.escape(text).replace(chr(10), '<br/>')}</p>",
                    "representation": "storage",
                }
            },
        }
        response = await self._request(
            "POST", f"/wiki/rest/api/content/{page_id}/child/comment", json=payload
        )
        return str(response.json().get("id", ""))

    async def mark_approved(self, page_id: str, reviewers: list[str]) -> None:
        """Upsert approval state as a Confluence content property and label."""
        path = f"/wiki/rest/api/content/{page_id}/property/{self.PROPERTY_KEY}"
        value = {"status": "Approved", "reviewers": reviewers}
        async with self._client_context() as client:
            current = await client.get(path)
            if current.status_code == 404:
                response = await client.post(
                    f"/wiki/rest/api/content/{page_id}/property",
                    json={"key": self.PROPERTY_KEY, "value": value},
                )
            else:
                current.raise_for_status()
                version = int(current.json().get("version", {}).get("number", 1)) + 1
                response = await client.put(
                    path,
                    json={
                        "key": self.PROPERTY_KEY,
                        "value": value,
                        "version": {"number": version},
                    },
                )
            response.raise_for_status()
            label = await client.post(
                f"/wiki/rest/api/content/{page_id}/label",
                json=[{"prefix": "global", "name": "approved"}],
            )
            label.raise_for_status()

    async def _request(
        self, method: str, path: str, **kwargs: object
    ) -> httpx.Response:
        async with self._client_context() as client:
            response = await client.request(method, path, **kwargs)
            response.raise_for_status()
            return response

    def _client_context(self):  # type: ignore[no-untyped-def]
        if self._client is not None:
            return _BorrowedClient(self._client)
        return httpx.AsyncClient(
            base_url=self._config.base_url,
            auth=(self._config.email, self._config.api_token),
            headers={"Accept": "application/json", "Content-Type": "application/json"},
            timeout=15,
        )


class _BorrowedClient:
    """Use an injected HTTP client without closing it after each operation."""

    def __init__(self, client: httpx.AsyncClient) -> None:
        self._client = client

    async def __aenter__(self) -> httpx.AsyncClient:
        return self._client

    async def __aexit__(self, *_args: object) -> None:
        return None
