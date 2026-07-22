"""Structural guard against accidentally publishing a Bloom API route."""

from fastapi.dependencies.models import Dependant
from fastapi.routing import APIRoute

from app.main import app

PUBLIC_ENDPOINTS = {
    "health_check",
    "readiness_check",
    "get_version",
    "prometheus_metrics",
    "login",
    "refresh",
    "logout",
    "get_invite_info",
    "accept_invite",
    "verify_email",
    "forgot_password",
    "reset_password",
}

# These endpoints authenticate with provider-specific webhook signatures rather
# than a FastAPI bearer-token dependency. Their security behavior is covered by
# test_defect_webhook_security.py.
SIGNED_WEBHOOK_ENDPOINTS = {"github_webhook", "gitlab_webhook"}

AUTH_DEPENDENCIES = {
    "get_current_user",
    "require_admin",
    "require_bud_sync_token",
    "role_checker",
}


def _dependency_names(dependant: Dependant) -> set[str]:
    names: set[str] = set()
    pending = list(dependant.dependencies)
    while pending:
        dependency = pending.pop()
        call = dependency.call
        name = getattr(call, "__name__", None)
        if name:
            names.add(name)
        pending.extend(dependency.dependencies)
    return names


def _api_routes(router, prefix: str = ""):
    """Yield included routes across both flattened and nested FastAPI routers."""
    for route in router.routes:
        if isinstance(route, APIRoute):
            path = f"{prefix}{route.path}"
            if path.startswith("/api"):
                yield path, route
            continue

        original_router = getattr(route, "original_router", None)
        include_context = getattr(route, "include_context", None)
        if original_router is not None and include_context is not None:
            yield from _api_routes(
                original_router,
                f"{prefix}{include_context.prefix}",
            )


def test_every_non_public_api_route_has_an_authentication_boundary():
    unprotected: list[str] = []
    for path, route in _api_routes(app):
        endpoint_name = route.endpoint.__name__
        if endpoint_name in PUBLIC_ENDPOINTS or endpoint_name in SIGNED_WEBHOOK_ENDPOINTS:
            continue
        dependencies = _dependency_names(route.dependant)
        if dependencies.isdisjoint(AUTH_DEPENDENCIES):
            methods = ",".join(sorted(route.methods or set()))
            unprotected.append(f"{methods} {path} ({endpoint_name})")

    assert not unprotected, "Routes without an authentication boundary:\n" + "\n".join(unprotected)


def test_signed_webhook_allowlist_matches_registered_routes():
    registered = {
        route.endpoint.__name__
        for _, route in _api_routes(app)
        if route.endpoint.__name__ in SIGNED_WEBHOOK_ENDPOINTS
    }

    assert registered == SIGNED_WEBHOOK_ENDPOINTS
