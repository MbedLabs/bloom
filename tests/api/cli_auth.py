"""
* @file     ${tests/api/cli_auth.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    This module tests browser-approved sign-in for command-line clients.
* @author   Amine El Omari
* @date     2026-11-16
* @version  1.0.0
* @note     Base class containing the bud methods of the CLI sign-in.
"""

import hashlib
from datetime import datetime, timedelta
from urllib.parse import parse_qs, urlsplit

from tests.bloom_api_interface import BloomApiInterface
from tests.bloom_test_base import BloomTestCase


class CliAuthBase(BloomTestCase):

    interface = BloomApiInterface

    def bud_a_code_exchange_keeps_the_account_and_stores_hashes_only(self):
        values = self.parameters
        world = self.bloom.bloom_new_cli_world()
        created = self.bloom.bloom_cli_start().json()
        expiry = datetime.fromisoformat(created["expires_at"].replace("Z", "+00:00")).replace(
            tzinfo=None
        )
        address = urlsplit(created["authorize_url"])
        self.assertEqual(
            (
                created["expires_at"].endswith("Z"),
                timedelta(minutes=9) < expiry - datetime.utcnow() <= timedelta(minutes=10),
                address.path,
                parse_qs(address.query),
            ),
            (True, True, "/auth/cli", {"session_id": [created["session_id"]]}),
            msg=values.MSG_CLIA_STARTED,
            abort_on_fail=False,
        )
        lookup = self.bloom.bloom_cli_lookup(world.headers, created["session_id"])
        self.assertEqual(
            (
                lookup.status_code,
                set(lookup.json()),
                lookup.json()["client_name"],
                lookup.headers["cache-control"],
                values.CLIA_HIDDEN_FIELDS & lookup.json().keys(),
            ),
            (values.STATUS_OK, values.CLIA_SESSION_FIELDS, "Example client", "no-store", set()),
            msg=values.MSG_CLIA_LOOKUP,
            abort_on_fail=False,
        )
        approval = self.bloom.bloom_cli_approve(world.headers, created["session_id"]).json()
        self.assertEqual(
            (set(approval), approval["expires_at"].endswith("Z")),
            ({"exchange_code", "expires_at"}, True),
            msg=values.MSG_CLIA_APPROVED,
            abort_on_fail=False,
        )
        exchanged = self.bloom.bloom_cli_exchange(created["session_id"], approval["exchange_code"])
        data = exchanged.json()
        account = self.bloom.bloom_api_call("GET", "/api/auth/me", world.headers).body
        self.assertEqual(
            (
                exchanged.status_code,
                exchanged.headers["cache-control"],
                set(data),
                data["token_type"],
                data["user"] == account,
                data["user"]["application_permissions"],
                self.bloom.bloom_api_call(
                    "GET", "/api/auth/me", {"Authorization": "Bearer " + data["access_token"]}
                ).body
                == data["user"],
            ),
            (
                values.STATUS_OK,
                "no-store",
                values.CLIA_TOKEN_FIELDS,
                "bearer",
                True,
                {"application": ["view"]},
                True,
            ),
            msg=values.MSG_CLIA_EXCHANGED,
            abort_on_fail=False,
        )
        claims = self.bloom.bloom_decode_access_token(data["access_token"])
        self.assertEqual(
            (claims["sub"], claims["type"], claims["ver"]),
            (str(world.user_id), "user", 1),
            msg=values.MSG_CLIA_CLAIMS,
            abort_on_fail=False,
        )
        (code_hash, consumed_at, version), tokens = self.bloom.bloom_cli_secret_state()
        self.assertEqual(
            (
                code_hash,
                consumed_at is not None,
                version,
                [(purpose, token_hash) for _, purpose, token_hash in tokens],
                claims["cli_refresh_id"] == tokens[0][0],
            ),
            (
                hashlib.sha256(approval["exchange_code"].encode()).hexdigest(),
                True,
                1,
                [
                    (
                        self.bloom.bloom_refresh_purpose(),
                        hashlib.sha256(data["refresh_token"].encode()).hexdigest(),
                    )
                ],
                True,
            ),
            msg=values.MSG_CLIA_STORED,
            abort_on_fail=False,
        )
        self.assertTrue(
            self.bloom.bloom_same_project_access(
                world.headers["Authorization"][7:], data["access_token"]
            ),
            msg=values.MSG_CLIA_ACCESS,
            abort_on_fail=False,
        )
        secrets = [
            values.CLIS_VERIFIER,
            approval["exchange_code"],
            data["access_token"],
            data["refresh_token"],
        ]
        for action in ("auth.cli_approve", "auth.cli_exchange"):
            events = self.bloom.bloom_list_audit_events(action)
            self.assertEqual(
                [
                    (
                        e.outcome,
                        e.actor_user_id,
                        e.target_type,
                        e.target_id,
                        any(secret in str(e.details) for secret in secrets),
                    )
                    for e in events
                ],
                [("success", world.user_id, "cli_auth_session", created["session_id"], False)],
                msg=values.MSG_CLIA_AUDIT.format(action=action),
                abort_on_fail=False,
            )
        again = self.bloom.bloom_cli_exchange(
            created["session_id"], approval["exchange_code"]
        ).status_code
        self.assertEqual(
            (
                "set-cookie" in exchanged.headers,
                again,
                [
                    (event.outcome)
                    for event in self.bloom.bloom_list_audit_events("auth.cli_exchange")
                ],
            ),
            (False, values.STATUS_BAD_REQUEST, ["success", "failure"]),
            msg=values.MSG_CLIA_REUSED,
            abort_on_fail=False,
        )

    def bud_a_callback_approval_carries_the_code_and_the_state(self):
        values = self.parameters
        for uri in values.CLIA_CALLBACKS:
            world = self.bloom.bloom_new_cli_world()
            created = self.bloom.bloom_cli_start(
                mode="callback", redirect_uri=uri, state=values.CLIA_STATE
            ).json()
            result = self.bloom.bloom_cli_approve(world.headers, created["session_id"]).json()
            target, given = urlsplit(result["redirect_to"]), urlsplit(uri)
            params = parse_qs(target.query)
            kept = all(params.get(name) == items for name, items in parse_qs(given.query).items())
            usable = (
                self.bloom.bloom_cli_exchange(created["session_id"], params["code"][0]).status_code
                if len(params.get("code", [])) == 1
                else None
            )
            self.assertEqual(
                (
                    set(result),
                    target.scheme,
                    target.netloc,
                    target.path,
                    kept,
                    params["state"],
                    usable,
                ),
                (
                    {"redirect_to"},
                    "http",
                    given.netloc,
                    given.path,
                    True,
                    [values.CLIA_STATE],
                    values.STATUS_OK,
                ),
                msg=values.MSG_CLIA_CALLBACK.format(uri=uri),
                abort_on_fail=False,
            )

    def bud_a_refresh_rotates_and_revokes_the_previous_access(self):
        values = self.parameters
        world = self.bloom.bloom_new_cli_world()
        first = self.bloom.bloom_cli_signed_in(world.headers)
        refreshed = self.bloom.bloom_cli_refresh({"refresh_token": first["refresh_token"]})
        second = refreshed.json()
        self.assertEqual(
            (
                refreshed.status_code,
                set(second),
                second["refresh_token"] != first["refresh_token"],
                "set-cookie" in refreshed.headers,
                [
                    (event.outcome, event.actor_user_id, event.target_id)
                    for event in self.bloom.bloom_list_audit_events("auth.cli_refresh")
                ],
            ),
            (
                values.STATUS_OK,
                values.CLIA_TOKEN_FIELDS,
                True,
                False,
                [("success", world.user_id, str(world.user_id))],
            ),
            msg=values.MSG_CLIA_ROTATED,
            abort_on_fail=False,
        )
        replay = self.bloom.bloom_cli_refresh({"refresh_token": first["refresh_token"]}).status_code
        old_access = self.bloom.bloom_api_call(
            "GET", "/api/auth/me", {"Authorization": "Bearer " + first["access_token"]}
        ).status
        new_access = self.bloom.bloom_api_call(
            "GET", "/api/auth/me", {"Authorization": "Bearer " + second["access_token"]}
        ).status
        self.bloom.bloom_revoke_refresh_tokens(world.user_id)
        self.assertEqual(
            (
                replay,
                old_access,
                new_access,
                self.bloom.bloom_api_call(
                    "GET", "/api/auth/me", {"Authorization": "Bearer " + second["access_token"]}
                ).status,
                self.bloom.bloom_cli_refresh(
                    {"refresh_token": second["refresh_token"]}
                ).status_code,
                self.bloom.bloom_api_call("GET", "/api/auth/me", world.headers).status,
            ),
            (
                values.STATUS_UNAUTHORIZED,
                values.STATUS_UNAUTHORIZED,
                values.STATUS_OK,
                values.STATUS_UNAUTHORIZED,
                values.STATUS_UNAUTHORIZED,
                values.STATUS_OK,
            ),
            msg=values.MSG_CLIA_REVOKED,
            abort_on_fail=False,
        )
        self.assertEqual(
            [(event.outcome) for event in self.bloom.bloom_list_audit_events("auth.cli_refresh")],
            ["success", "failure", "failure"],
            msg=values.MSG_CLIA_REFRESH_AUDIT,
            abort_on_fail=False,
        )

    def bud_the_cli_and_the_browser_share_refresh_tokens(self):
        values = self.parameters
        world = self.bloom.bloom_new_cli_world()
        browser_token = self.bloom.bloom_new_browser_refresh_token(world.user_id)
        from_browser = self.bloom.bloom_cli_refresh({"refresh_token": browser_token})
        cli_token = self.bloom.bloom_cli_signed_in(world.headers)["refresh_token"]
        browser = self.bloom.bloom_browser_refresh(cli_token)
        self.assertEqual(
            (
                from_browser.status_code,
                "cli_refresh_id"
                in self.bloom.bloom_decode_access_token(from_browser.json()["access_token"]),
                browser.status_code,
                "cli_refresh_id"
                in self.bloom.bloom_decode_access_token(browser.json()["access_token"]),
                self.bloom.bloom_cli_refresh({"refresh_token": cli_token}).status_code,
            ),
            (values.STATUS_OK, True, values.STATUS_OK, False, values.STATUS_UNAUTHORIZED),
            msg=values.MSG_CLIA_SHARED,
            abort_on_fail=False,
        )

    def bud_an_approval_happens_once_and_signed_in(self):
        values = self.parameters
        world = self.bloom.bloom_new_cli_world()
        session_id = self.bloom.bloom_cli_session()
        anonymous = (
            self.bloom.bloom_cli_lookup(None, session_id).status_code,
            self.bloom.bloom_cli_approve(None, session_id).status_code,
        )
        self.bloom.bloom_cli_approve(world.headers, session_id)
        again = self.bloom.bloom_cli_approve(world.headers, session_id).status_code
        events = self.bloom.bloom_list_audit_events("auth.cli_approve")
        self.assertEqual(
            (
                anonymous,
                again,
                [(e.outcome, e.actor_user_id, e.target_id) for e in events],
                events[-1].details,
            ),
            (
                (values.STATUS_UNAUTHORIZED, values.STATUS_UNAUTHORIZED),
                values.STATUS_BAD_REQUEST,
                [("success", world.user_id, session_id), ("failure", world.user_id, session_id)],
                {"reason": "not_pending"},
            ),
            msg=values.MSG_CLIA_ONCE,
            abort_on_fail=False,
        )

    def bud_a_changed_session_version_refuses_an_approved_code(self):
        values = self.parameters
        world = self.bloom.bloom_new_cli_world()
        session_id = self.bloom.bloom_cli_session()
        code = self.bloom.bloom_cli_approve(world.headers, session_id).json()["exchange_code"]
        self.bloom.bloom_set_session_version(world.user_id, 2)
        refused = self.bloom.bloom_cli_exchange(session_id, code).status_code
        failure = self.bloom.bloom_list_audit_events("auth.cli_exchange")[-1]
        self.assertEqual(
            (refused, failure.outcome, failure.details, self.bloom.bloom_count_user_tokens()),
            (values.STATUS_BAD_REQUEST, "failure", {"reason": "inactive_or_changed_user"}, 0),
            msg=values.MSG_CLIA_VERSION,
            abort_on_fail=False,
        )

    def bud_a_new_request_deletes_expired_and_consumed_requests(self):
        values = self.parameters
        world = self.bloom.bloom_new_cli_world()
        expired, pending, consumed = (self.bloom.bloom_cli_session() for _ in range(3))
        session = self.bloom.bloom_cli_approve(world.headers, consumed).json()["exchange_code"]
        self.bloom.bloom_cli_exchange(consumed, session)
        self.bloom.bloom_cli_expire(expired)
        before = self.bloom.bloom_cli_stored_ids()
        newest = self.bloom.bloom_cli_session()
        self.assertEqual(
            (
                before,
                self.bloom.bloom_cli_stored_ids(),
                self.bloom.bloom_cli_lookup(world.headers, pending).status_code,
            ),
            ({expired, consumed, pending}, {pending, newest}, values.STATUS_OK),
            msg=values.MSG_CLIA_CLEANUP,
            abort_on_fail=False,
        )

    def bud_the_request_code_matches_the_shared_vector(self):
        values = self.parameters
        challenge, _ = self.bloom.bloom_cli_challenge(values.CLIA_RFC_VERIFIER)
        default_challenge, _ = self.bloom.bloom_cli_challenge()
        self.assertEqual(
            (
                challenge,
                self.bloom.bloom_cli_request_code(values.CLIA_RFC_CHALLENGE),
                self.bloom.bloom_cli_request_code(default_challenge)
                != values.CLIA_RFC_REQUEST_CODE,
            ),
            (values.CLIA_RFC_CHALLENGE, values.CLIA_RFC_REQUEST_CODE, True),
            msg=values.MSG_CLIA_VECTOR,
            abort_on_fail=False,
        )

    def bud_a_request_shows_its_time_without_its_code(self):
        values = self.parameters
        for mode, uri in (("code", None), ("callback", values.CLIS_CALLBACK)):
            world = self.bloom.bloom_new_cli_world()
            before = datetime.utcnow().replace(microsecond=0)
            created = self.bloom.bloom_cli_start(
                mode=mode, redirect_uri=uri, code_challenge=values.CLIA_RFC_CHALLENGE
            ).json()
            shown = self.bloom.bloom_cli_lookup(world.headers, created["session_id"])
            data = shown.json()
            requested = datetime.fromisoformat(data["created_at"][:-1])
            expires = datetime.fromisoformat(data["expires_at"][:-1])
            self.assertEqual(
                (
                    shown.status_code,
                    set(data),
                    values.CLIA_RFC_REQUEST_CODE in shown.text,
                    values.CLIA_RFC_CHALLENGE in shown.text,
                    data["created_at"].endswith("Z") and data["expires_at"].endswith("Z"),
                    before <= requested <= datetime.utcnow(),
                    expires - requested,
                ),
                (
                    values.STATUS_OK,
                    values.CLIA_SESSION_FIELDS,
                    False,
                    False,
                    True,
                    True,
                    timedelta(minutes=10),
                ),
                msg=values.MSG_CLIA_TIMES.format(mode=mode),
                abort_on_fail=False,
            )

    def bud_denying_a_callback_request_redirects_with_access_denied(self):
        values = self.parameters
        for uri in values.CLIA_CALLBACKS[:3]:
            world = self.bloom.bloom_new_cli_world()
            created = self.bloom.bloom_cli_start(
                mode="callback", redirect_uri=uri, state=values.CLIA_STATE
            ).json()
            denied = self.bloom.bloom_cli_deny(world.headers, created["session_id"])
            target, given = urlsplit(denied.json()["redirect_to"]), urlsplit(uri)
            params = parse_qs(target.query, keep_blank_values=True)
            kept = all(params.get(name) == items for name, items in parse_qs(given.query).items())
            self.assertEqual(
                (
                    denied.status_code,
                    denied.headers["cache-control"],
                    set(denied.json()),
                    (target.scheme, target.netloc, target.path),
                    kept,
                    params["error"],
                    params["state"],
                    "code" in params,
                    self.bloom.bloom_cli_stored_ids(),
                    [
                        (e.outcome, e.actor_user_id, e.target_type, e.target_id)
                        for e in self.bloom.bloom_list_audit_events("auth.cli_deny")
                    ],
                ),
                (
                    values.STATUS_OK,
                    "no-store",
                    {"redirect_to"},
                    ("http", given.netloc, given.path),
                    True,
                    ["access_denied"],
                    [values.CLIA_STATE],
                    False,
                    set(),
                    [("success", world.user_id, "cli_auth_session", created["session_id"])],
                ),
                msg=values.MSG_CLIA_DENY_CALLBACK.format(uri=uri),
                abort_on_fail=False,
            )

    def bud_denying_a_code_request_answers_empty(self):
        values = self.parameters
        world = self.bloom.bloom_new_cli_world()
        denied = self.bloom.bloom_cli_deny(world.headers, self.bloom.bloom_cli_session())
        self.assertEqual(
            (
                denied.status_code,
                denied.json(),
                self.bloom.bloom_cli_stored_ids(),
                [
                    (event.outcome, event.actor_user_id)
                    for event in self.bloom.bloom_list_audit_events("auth.cli_deny")
                ],
            ),
            (values.STATUS_OK, {}, set(), [("success", world.user_id)]),
            msg=values.MSG_CLIA_DENY_CODE,
            abort_on_fail=False,
        )

    def bud_a_denied_request_answers_as_a_missing_one_400(self):
        values = self.parameters
        for mode in ("code", "callback"):
            world = self.bloom.bloom_new_cli_world()
            uri = values.CLIS_CALLBACK if mode == "callback" else None
            session_id = self.bloom.bloom_cli_session(mode=mode, redirect_uri=uri)
            self.bloom.bloom_cli_deny(world.headers, session_id)
            answers = (
                self.bloom.bloom_cli_lookup(world.headers, session_id).status_code,
                self.bloom.bloom_cli_approve(world.headers, session_id).status_code,
                self.bloom.bloom_cli_exchange(session_id, "any-code").status_code,
                self.bloom.bloom_cli_deny(world.headers, session_id).status_code,
            )
            self.assertEqual(
                answers,
                (values.STATUS_BAD_REQUEST,) * 4,
                msg=values.MSG_CLIA_DENIED.format(mode=mode),
                abort_on_fail=False,
            )

    def bud_the_check_accepts_the_code_in_any_case_and_spacing(self):
        values = self.parameters
        for typed in values.CLIA_TYPED_RIGHT:
            world = self.bloom.bloom_new_cli_world()
            session_id = self.bloom.bloom_cli_session(code_challenge=values.CLIA_RFC_CHALLENGE)
            checked = self.bloom.bloom_cli_check(world.headers, session_id, typed)
            stored = self.bloom.bloom_cli_get_session(session_id)
            self.assertEqual(
                (
                    checked.status_code,
                    checked.headers["cache-control"],
                    stored.user_id,
                    stored.exchange_code_hash,
                ),
                (values.STATUS_NO_CONTENT, "no-store", None, None),
                msg=values.MSG_CLIA_CHECK_RIGHT.format(typed=typed),
                abort_on_fail=False,
            )

    def bud_the_check_refuses_a_wrong_code_and_keeps_the_request(self):
        values = self.parameters
        for typed in values.CLIA_TYPED_WRONG:
            world = self.bloom.bloom_new_cli_world()
            session_id = self.bloom.bloom_cli_session(code_challenge=values.CLIA_RFC_CHALLENGE)
            checked = self.bloom.bloom_cli_check(world.headers, session_id, typed)
            self.assertEqual(
                (
                    checked.status_code,
                    checked.json(),
                    self.bloom.bloom_cli_lookup(world.headers, session_id).status_code,
                ),
                (values.STATUS_BAD_REQUEST, {"detail": values.CLIS_INVALID}, values.STATUS_OK),
                msg=values.MSG_CLIA_CHECK_WRONG.format(typed=typed),
                abort_on_fail=False,
            )

    def bud_the_check_refuses_a_request_that_is_not_pending(self):
        values = self.parameters
        world = self.bloom.bloom_new_cli_world()
        expired, approved, consumed = (self.bloom.bloom_cli_session() for _ in range(3))
        self.bloom.bloom_cli_approve(world.headers, approved)
        code = self.bloom.bloom_cli_approve(world.headers, consumed).json()["exchange_code"]
        self.bloom.bloom_cli_exchange(consumed, code)
        self.bloom.bloom_cli_expire(expired)
        for what, session_id in (
            ("an unknown", self.bloom.bloom_unknown_session()),
            ("an expired", expired),
            ("an approved", approved),
            ("a consumed", consumed),
        ):
            checked = self.bloom.bloom_cli_check(world.headers, session_id)
            self.assertEqual(
                (checked.status_code, checked.json()),
                (values.STATUS_BAD_REQUEST, {"detail": values.CLIS_INVALID}),
                msg=values.MSG_CLIA_CHECK_STATE.format(what=what),
                abort_on_fail=False,
            )

    def bud_the_check_needs_sign_in_and_code_mode(self):
        values = self.parameters
        world = self.bloom.bloom_new_cli_world()
        session_id = self.bloom.bloom_cli_session()
        anonymous = self.bloom.bloom_cli_check({}, session_id).status_code
        self.bloom.bloom_set_code_mode(False)
        turned_off = self.bloom.bloom_cli_check(world.headers, session_id).status_code
        self.bloom.bloom_set_code_mode(True)
        self.assertEqual(
            (anonymous, turned_off),
            (values.STATUS_UNAUTHORIZED, values.STATUS_FORBIDDEN),
            msg=values.MSG_CLIA_CHECK_GUARD,
            abort_on_fail=False,
        )

    def bud_approving_needs_the_matching_request_code(self):
        values = self.parameters
        world = self.bloom.bloom_new_cli_world()
        session_id = self.bloom.bloom_cli_session()
        missing = self.bloom.bloom_cli_post(
            "approve", world.headers, {"session_id": session_id}
        ).status_code
        wrong = self.bloom.bloom_cli_approve(world.headers, session_id, values.CLIS_WRONG_CODE)
        kept = self.bloom.bloom_cli_lookup(world.headers, session_id).status_code
        code = self.bloom.bloom_cli_approve(world.headers, session_id).json()["exchange_code"]
        self.assertEqual(
            (
                missing,
                wrong.status_code,
                wrong.json(),
                kept,
                self.bloom.bloom_cli_exchange(session_id, code).status_code,
            ),
            (
                values.STATUS_UNPROCESSABLE,
                values.STATUS_BAD_REQUEST,
                {"detail": values.CLIS_INVALID},
                values.STATUS_OK,
                values.STATUS_OK,
            ),
            msg=values.MSG_CLIA_APPROVE_CODE,
            abort_on_fail=False,
        )

    def bud_denying_takes_no_request_code(self):
        values = self.parameters
        world = self.bloom.bloom_new_cli_world()
        session_id = self.bloom.bloom_cli_session()
        _, request_code = self.bloom.bloom_cli_challenge()
        refused = self.bloom.bloom_cli_deny(
            world.headers, session_id, request_code=request_code
        ).status_code
        self.assertEqual(
            (refused, self.bloom.bloom_cli_deny(world.headers, session_id).status_code),
            (values.STATUS_UNPROCESSABLE, values.STATUS_OK),
            msg=values.MSG_CLIA_DENY_NO_CODE,
            abort_on_fail=False,
        )
