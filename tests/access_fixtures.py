"""Explicit custom project policies for independently specified test scenarios."""

import asyncio
import json
import os

import asyncpg

from app.core.permissions import (
    APPROVE_ACTIONS,
    DOC_TYPE_RESOURCES,
    READ_ACTIONS,
    RESOURCE_ACTIONS,
    RESOURCES,
    VISIBILITIES,
    actions_on,
)
from app.models.groups import Policy
from app.models.project_membership import ProjectAccess
from tests.conftest import unique_name


def scenario_permissions(name):
    """Explicit matrices used by the retained author, reader and signoff scenarios."""
    if name == "Read Only":
        return {resource: ["view"] for resource in RESOURCES}
    if name == "External Reader":
        return {
            resource: [
                action for action in ["view", "comment"] if action in RESOURCE_ACTIONS[resource]
            ]
            for resource in RESOURCES
            if resource != "parameter"
        }
    matrix = {
        resource: [action for action in ["view", "comment"] if action in RESOURCE_ACTIONS[resource]]
        for resource in RESOURCES
    }
    author = ["view", "comment", "create", "edit", "delete"]
    if name == "Test Author":
        matrix.update(
            {
                "CPT": author,
                "TC": author + ["import", "export"],
                "TS": ["view", "create", "edit", "delete", "plan"],
                "CMP": ["view", "create", "edit", "delete", "plan"],
                "DEF": ["view", "comment", "create"],
                "parameter": ["view", "create", "edit", "delete"],
                "link": ["view", "create", "delete"],
            }
        )
    elif name == "Requirements Author":
        matrix.update(
            {
                "REQ": author + ["import", "export"],
                "SPEC": author + ["import"],
                "STD": author + ["import"],
                "RPT": author + ["import"],
                "PRT": author + ["import"],
                "RSK": author,
                "parameter": ["view", "create", "edit", "delete"],
                "link": ["view", "create", "delete"],
            }
        )
    elif name == "Design Author":
        matrix.update({"DES": author, "DEF": author, "link": ["view", "create", "delete"]})
    elif name == "Approver":
        return {
            resource: [
                action
                for action in ["view", "comment", "review", "approve"]
                if action in RESOURCE_ACTIONS[resource]
            ]
            for resource in RESOURCES
        }
    elif name == "Project Administrator":
        return {"*": ["*"]}
    else:
        raise AssertionError("Unknown test scenario: " + name)
    return matrix


def scenario_type_tags(permissions, visibility="internal", doc_types=None) -> dict:
    """The tags a scenario policy covers: Internal and Customer, or Customer alone, on each
    document type it grants actions on, all of them (None) or the given ones."""
    shown = ["customer"] if visibility == "customer" else list(VISIBILITIES)
    return {
        resource: {"visibility": shown, "tags": []}
        for resource in DOC_TYPE_RESOURCES
        if actions_on(permissions, resource) and (doc_types is None or resource in doc_types)
    }


def allow_doc_types(policy, doc_types, visibility="customer") -> None:
    """Let the policy cover the document types too, with the visibility's tags."""
    shown = ["customer"] if visibility == "customer" else list(VISIBILITIES)
    policy.type_tags = {
        **(policy.type_tags or {}),
        **{doc_type: {"visibility": shown, "tags": []} for doc_type in doc_types},
    }


def project_access_fixture(
    *, user_id, project_id, permissions, visibility="internal", doc_types=None
):
    """Build a direct entry with the scenario's explicit policy matrix and tags."""
    policy = Policy(
        name=unique_name("Fixture policy"),
        permissions=permissions,
        type_tags=scenario_type_tags(permissions, visibility, doc_types),
        is_default=False,
    )
    return ProjectAccess(user_id=user_id, project_id=project_id, owner=False, policies=[policy])


def scenario_rules(permissions, visibility="internal", doc_types=None) -> dict:
    """Convert scenario actions and document tags into independent policy rule fields."""
    tags = scenario_type_tags(permissions, visibility, doc_types)
    rules = {}
    for resource in RESOURCES:
        actions = actions_on(permissions, resource)
        if not actions or (resource in DOC_TYPE_RESOURCES and resource not in tags):
            continue
        rules[resource] = {
            "read": bool(actions & READ_ACTIONS),
            "write": bool(actions - READ_ACTIONS - APPROVE_ACTIONS - {"delete"}),
            "review": "review" in actions,
            "approve": "approve" in actions,
            "delete": "delete" in actions,
            **tags.get(resource, {}),
        }
    return rules


def add_policy_member(
    client, *, headers, url, user_id, permissions, visibility="internal", doc_types=None
):
    """Create the scenario policy and assign it through the real HTTP API."""
    response = client.post(
        "/api/policies",
        headers=headers,
        json={
            "name": unique_name("Fixture policy"),
            "rules": scenario_rules(permissions, visibility, doc_types),
        },
    )
    assert response.status_code == 201, response.text
    return client.post(
        url, headers=headers, json={"user_id": user_id, "policy_ids": [response.json()["id"]]}
    )


def keep_matrix(policy_id: int, permissions: dict) -> None:
    """Store the action matrix on the policy row directly."""

    async def store() -> None:
        database_url = (os.environ.get("DATABASE_URL") or os.environ["BLOOM_DATABASE_URL"]).replace(
            "postgresql+asyncpg://", "postgresql://", 1
        )
        connection = await asyncpg.connect(database_url)
        try:
            await connection.execute(
                "UPDATE policies SET permissions = $1::json WHERE id = $2",
                json.dumps(permissions),
                policy_id,
            )
        finally:
            await connection.close()

    asyncio.run(store())
