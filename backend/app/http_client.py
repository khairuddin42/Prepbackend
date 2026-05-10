import httpx

_client: httpx.AsyncClient | None = None


def get_http_client() -> httpx.AsyncClient:
    """Return a shared httpx.AsyncClient that reuses TCP connections."""
    global _client
    if _client is None or _client.is_closed:
        _client = httpx.AsyncClient(
            timeout=30.0,
            limits=httpx.Limits(
                max_connections=20,
                max_keepalive_connections=10,
            ),
        )
    return _client


async def close_http_client():
    """Close the shared client gracefully (called on app shutdown)."""
    global _client
    if _client is not None:
        await _client.aclose()
        _client = None
