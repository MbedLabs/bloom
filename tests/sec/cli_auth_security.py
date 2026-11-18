"""
* @file     ${tests/sec/cli_auth_security.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    This module tests the CLI sign-in against redirect abuse, replay, revoked identities and code sign-in turned off.
* @author   Amine El Omari
* @date     2026-11-16
* @version  1.0.0
* @note     Base class containing the bud methods of the CLI sign-in security; each step starts from a new database.
"""

from datetime import datetime, timedelta

from tests.bloom_api_interface import BloomApiInterface
from tests.bloom_test_base import BloomTestCase


class CliAuthSecurityBase(BloomTestCase):

    interface = BloomApiInterface

    def bud_callback_redirect_abuse_is_rejected(self):
        values, bloom = self.parameters, self.bloom
        world = bloom.bloom_new_cli_world()
        challenge, _ = bloom.bloom_cli_challenge()
        for uri in values.CLIS_BAD_REDIRECTS:
            answer = bloom.bloom_cli_post(
                "start",
                body={
                    "client_name": "Client",
                    "mode": "callback",
                    "redirect_uri": uri,
                    "code_challenge": challenge,
                    "state": "state",
                },
            )
            self.assertEqual(
                answer.status_code,
                values.STATUS_UNPROCESSABLE,
                msg=values.MSG_CLIS_REDIRECT.format(uri=uri),
                abort_on_fail=False,
            )

    def bud_invalid_start_fields_are_rejected(self):
        values, bloom = self.parameters, self.bloom
        world = bloom.bloom_new_cli_world()
        challenge, _ = bloom.bloom_cli_challenge()
        for change in values.CLIS_BAD_STARTS:
            body = {
                "client_name": "Client",
                "mode": "code",
                "code_challenge": challenge,
                "state": "state",
                **change,
            }
            answer = bloom.bloom_cli_post("start", body=body)
            self.assertEqual(
                answer.status_code,
                values.STATUS_UNPROCESSABLE,
                msg=values.MSG_CLIS_START.format(change=change),
                abort_on_fail=False,
            )

    def bud_invalid_pkce_does_not_consume_or_issue_tokens(self):
        values, bloom = self.parameters, self.bloom
        world = bloom.bloom_new_cli_world()
        session_id = bloom.bloom_cli_session()
        code = bloom.bloom_cli_approve(world.headers, session_id).json()["exchange_code"]
        for verifier in values.CLIS_BAD_VERIFIERS:
            answer = bloom.bloom_cli_exchange(session_id, code, verifier)
            successes = [
                e
                for e in bloom.bloom_list_audit_events("auth.cli_exchange")
                if e.outcome == "success"
            ]
            self.assertEqual(
                (
                    answer.status_code in (values.STATUS_BAD_REQUEST, values.STATUS_UNPROCESSABLE),
                    bloom.bloom_count_user_tokens(),
                    successes,
                ),
                (True, 0, []),
                msg=values.MSG_CLIS_PKCE.format(verifier=verifier),
                abort_on_fail=False,
            )
        self.assertEqual(
            bloom.bloom_cli_exchange(session_id, code).status_code,
            values.STATUS_OK,
            msg=values.MSG_CLIS_PKCE_KEPT,
            abort_on_fail=False,
        )

    def bud_exchange_code_and_refresh_token_lengths_are_bounded(self):
        values, bloom = self.parameters, self.bloom
        world = bloom.bloom_new_cli_world()
        session_id = bloom.bloom_cli_session()
        bloom.bloom_cli_approve(world.headers, session_id)
        statuses = (
            bloom.bloom_cli_exchange(session_id, "c" * 257).status_code,
            bloom.bloom_cli_exchange(session_id, "c" * 256).status_code,
            bloom.bloom_cli_refresh({"refresh_token": "r" * 257}).status_code,
            bloom.bloom_cli_refresh({"refresh_token": "r" * 256}).status_code,
        )
        self.print_variables({"statuses": statuses})
        self.assertEqual(
            statuses,
            (
                values.STATUS_UNPROCESSABLE,
                values.STATUS_BAD_REQUEST,
                values.STATUS_UNPROCESSABLE,
                values.STATUS_UNAUTHORIZED,
            ),
            msg=values.MSG_CLIS_LENGTHS,
            abort_on_fail=False,
        )

    def bud_wrong_code_and_unapproved_or_unknown_sessions_reject(self):
        values, bloom = self.parameters, self.bloom
        world = bloom.bloom_new_cli_world()
        session_id = bloom.bloom_cli_session()
        unapproved = bloom.bloom_cli_exchange(session_id, "unapproved").status_code
        code = bloom.bloom_cli_approve(world.headers, session_id).json()["exchange_code"]
        wrong = bloom.bloom_cli_exchange(session_id, "wrong-code").status_code
        unknown = bloom.bloom_unknown_session()
        missing = bloom.bloom_cli_exchange(unknown, code).status_code
        lookup = bloom.bloom_cli_lookup(world.headers, bloom.bloom_unknown_session()).status_code
        self.assertEqual(
            (unapproved, wrong, missing, lookup),
            (values.STATUS_BAD_REQUEST,) * 4,
            msg=values.MSG_CLIS_REJECTED,
            abort_on_fail=False,
        )
        failures = bloom.bloom_list_audit_events("auth.cli_exchange")
        self.print_variables({"failures": [(e.outcome, e.target_id, e.details) for e in failures]})
        self.assertEqual(
            [
                (e.outcome, e.target_id, e.details, e.actor_user_id, code in str(e.details))
                for e in failures
            ],
            [
                ("failure", session_id, {"reason": "unknown_or_unapproved_session"}, None, False),
                ("failure", session_id, {"reason": "code_or_verifier_mismatch"}, None, False),
                ("failure", unknown, {"reason": "unknown_or_unapproved_session"}, None, False),
            ],
            msg=values.MSG_CLIS_REJECTED_AUDIT,
            abort_on_fail=False,
        )
        self.assertEqual(
            bloom.bloom_cli_exchange(session_id, code).status_code,
            values.STATUS_OK,
            msg=values.MSG_CLIS_STILL,
            abort_on_fail=False,
        )

    def bud_an_expired_session_cannot_be_approved_or_exchanged(self):
        values, bloom = self.parameters, self.bloom
        world = bloom.bloom_new_cli_world()
        for state in ("pending", "approved"):
            session_id = bloom.bloom_cli_session()
            code = (
                bloom.bloom_cli_approve(world.headers, session_id).json()["exchange_code"]
                if state == "approved"
                else "unused"
            )
            bloom.bloom_cli_expire(session_id)
            statuses = (
                bloom.bloom_cli_lookup(world.headers, session_id).status_code,
                bloom.bloom_cli_approve(world.headers, session_id).status_code,
                bloom.bloom_cli_exchange(session_id, code).status_code,
            )
            self.assertEqual(
                statuses,
                (values.STATUS_BAD_REQUEST,) * 3,
                msg=values.MSG_CLIS_EXPIRED.format(state=state),
                abort_on_fail=False,
            )

    def bud_a_disabled_account_rejects_approval_exchange_and_refresh(self):
        values, bloom = self.parameters, self.bloom
        world = bloom.bloom_new_cli_world()
        tokens = bloom.bloom_cli_signed_in(world.headers)
        pending = bloom.bloom_cli_session()
        waiting = bloom.bloom_cli_session()
        code = bloom.bloom_cli_approve(world.headers, waiting).json()["exchange_code"]
        bloom.bloom_deactivate(world.user_id)
        statuses = (
            bloom.bloom_cli_approve(world.headers, pending).status_code,
            bloom.bloom_cli_exchange(waiting, code).status_code,
            bloom.bloom_cli_refresh({"refresh_token": tokens["refresh_token"]}).status_code,
        )
        self.assertEqual(
            statuses,
            (values.STATUS_FORBIDDEN, values.STATUS_BAD_REQUEST, values.STATUS_UNAUTHORIZED),
            msg=values.MSG_CLIS_DISABLED,
            abort_on_fail=False,
        )
        failure = bloom.bloom_list_audit_events("auth.cli_refresh")[-1]
        self.assertEqual(
            (failure.outcome, failure.target_type, failure.target_id, failure.details),
            ("failure", "user", str(world.user_id), {"reason": "inactive_or_missing_user"}),
            msg=values.MSG_CLIS_DISABLED_AUDIT,
            abort_on_fail=False,
        )

    def bud_approval_rereads_and_rejects_a_changed_account(self):
        values, bloom = self.parameters, self.bloom
        world = bloom.bloom_new_cli_world()
        result = bloom.bloom_approve_with_stale_account(world.user_id)
        self.print_variables({"reason, approver, code hash": result})
        self.assertEqual(
            result,
            ("inactive_or_changed_user", None, None),
            msg=values.MSG_CLIS_STALE,
            abort_on_fail=False,
        )

    def bud_cli_access_requires_a_valid_matching_refresh_binding(self):
        values, bloom = self.parameters, self.bloom
        world = bloom.bloom_new_cli_world()
        for binding in values.CLIS_BINDINGS:
            headers = bloom.bloom_token_headers(
                {"sub": str(world.user_id), "type": "user", "ver": 1, "cli_refresh_id": binding}
            )
            status = bloom.bloom_api_send("GET", "/api/auth/me", headers).status_code
            self.assertEqual(
                status,
                values.STATUS_UNAUTHORIZED,
                msg=values.MSG_CLIS_BINDING.format(binding=binding),
                abort_on_fail=False,
            )

    def bud_cli_access_rejects_an_invalidated_binding(self):
        values, bloom = self.parameters, self.bloom
        world = bloom.bloom_new_cli_world()
        for mutation in values.CLIS_MUTATIONS:
            world = bloom.bloom_new_cli_world()
            tokens = bloom.bloom_cli_signed_in(world.headers)
            if mutation == "version":
                bloom.bloom_set_session_version(world.user_id, 2)
            else:
                bloom.bloom_change_refresh_rows(
                    **{
                        "expired": {"expires_at": datetime.utcnow() - timedelta(seconds=1)},
                        "purpose": {"purpose": bloom.bloom_password_reset_purpose()},
                        "user": {"user_id": world.other_id},
                    }[mutation]
                )
            headers = {"Authorization": "Bearer " + tokens["access_token"]}
            status = bloom.bloom_api_send("GET", "/api/auth/me", headers).status_code
            self.assertEqual(
                status,
                values.STATUS_UNAUTHORIZED,
                msg=values.MSG_CLIS_MUTATION.format(mutation=mutation),
                abort_on_fail=False,
            )

    def bud_missing_and_unknown_refresh_tokens_reject(self):
        values, bloom = self.parameters, self.bloom
        world = bloom.bloom_new_cli_world()
        unknown = bloom.bloom_cli_refresh({"refresh_token": "unknown"}).status_code
        missing = bloom.bloom_cli_refresh({}).status_code
        failure = bloom.bloom_list_audit_events("auth.cli_refresh")[-1]
        self.assertEqual(
            (
                unknown,
                missing,
                failure.outcome,
                failure.target_type,
                failure.details,
                "unknown" in str(failure.details),
            ),
            (
                values.STATUS_UNAUTHORIZED,
                values.STATUS_UNPROCESSABLE,
                "failure",
                None,
                {"reason": "invalid_token"},
                False,
            ),
            msg=values.MSG_CLIS_REFRESH_REJECT,
            abort_on_fail=False,
        )

    def bud_failure_records_carry_no_secret(self):
        values, bloom = self.parameters, self.bloom
        world = bloom.bloom_new_cli_world()
        session_id = bloom.bloom_cli_session()
        code = bloom.bloom_cli_approve(world.headers, session_id).json()["exchange_code"]
        bloom.bloom_cli_exchange(session_id, code, values.CLIS_WRONG_VERIFIER)
        tokens = bloom.bloom_cli_signed_in(world.headers)
        bloom.bloom_cli_refresh({"refresh_token": tokens["refresh_token"]})
        bloom.bloom_cli_refresh({"refresh_token": tokens["refresh_token"]})
        events = bloom.bloom_list_every_audit_event()
        self.assertEqual(
            {e.outcome for e in events if e.action != "api.request"},
            {"success", "failure"},
            msg=values.MSG_CLIS_OUTCOMES,
            abort_on_fail=False,
        )
        text = " ".join(f"{e.target_id} {e.details}" for e in events)
        for name, secret in (
            ("exchange code", code),
            ("verifier", values.CLIS_VERIFIER),
            ("wrong verifier", values.CLIS_WRONG_VERIFIER),
            ("refresh token", tokens["refresh_token"]),
            ("access token", tokens["access_token"]),
        ):
            self.assertNotIn(
                secret, text, msg=values.MSG_CLIS_NO_SECRET.format(secret=name), abort_on_fail=False
            )

    def bud_public_cli_endpoints_enforce_their_rate_limit(self):
        values, bloom = self.parameters, self.bloom
        world = bloom.bloom_new_cli_world()
        challenge, _ = bloom.bloom_cli_challenge()
        bodies = {
            "start": {
                "client_name": "Rate test",
                "mode": "code",
                "code_challenge": challenge,
                "state": "rate-state",
            },
            "exchange": {
                "session_id": bloom.bloom_unknown_session(),
                "code": "unknown",
                "code_verifier": values.CLIS_VERIFIER,
            },
            "refresh": {"refresh_token": "unknown"},
        }
        for path, limit in values.CLIS_PUBLIC_LIMITS:
            statuses = [
                answer.status_code
                for answer in bloom.bloom_with_login_limit(
                    [lambda: bloom.bloom_cli_post(path, body=bodies[path])] * (limit + 1)
                )
            ]
            self.assertEqual(
                (values.STATUS_TOO_MANY in statuses[:-1], statuses[-1]),
                (False, values.STATUS_TOO_MANY),
                msg=values.MSG_CLIS_LIMIT.format(path=path, limit=limit),
                abort_on_fail=False,
            )

    def bud_code_mode_off_refuses_a_new_code_request_and_keeps_callback(self):
        values, bloom = self.parameters, self.bloom
        world = bloom.bloom_new_cli_world()
        challenge, _ = bloom.bloom_cli_challenge()
        bloom.bloom_set_code_mode(False)
        refused = bloom.bloom_cli_post(
            "start",
            body={
                "client_name": "Client",
                "mode": "code",
                "code_challenge": challenge,
                "state": "s",
            },
        )
        self.assertEqual(
            (refused.status_code, refused.json(), bloom.bloom_cli_stored_ids()),
            (values.STATUS_FORBIDDEN, {"detail": values.CLIS_CODE_MODE_OFF}, set()),
            msg=values.MSG_CLIS_MODE_OFF_START,
            abort_on_fail=False,
        )
        created = bloom.bloom_cli_session(mode="callback", redirect_uri=values.CLIS_CALLBACK)
        lookup = bloom.bloom_cli_lookup(world.headers, created).status_code
        target = bloom.bloom_cli_approve(world.headers, created).json()["redirect_to"]
        code = bloom.bloom_callback_code(target)
        exchanged = bloom.bloom_cli_exchange(created, code).status_code
        denied = bloom.bloom_cli_deny(
            world.headers,
            bloom.bloom_cli_session(mode="callback", redirect_uri=values.CLIS_CALLBACK),
        ).status_code
        self.assertEqual(
            (lookup, exchanged, denied),
            (values.STATUS_OK,) * 3,
            msg=values.MSG_CLIS_MODE_OFF_CALLBACK,
            abort_on_fail=False,
        )

    def bud_code_mode_off_refuses_every_stored_code_request(self):
        values, bloom = self.parameters, self.bloom
        world = bloom.bloom_new_cli_world()
        pending, approved, expired = (bloom.bloom_cli_session() for _ in range(3))
        code = bloom.bloom_cli_approve(world.headers, approved).json()["exchange_code"]
        bloom.bloom_cli_expire(expired)
        bloom.bloom_set_code_mode(False)
        off = (values.STATUS_FORBIDDEN, {"detail": values.CLIS_CODE_MODE_OFF})
        for session_id in (pending, approved, expired):
            lookup = bloom.bloom_cli_lookup(world.headers, session_id)
            refused = bloom.bloom_cli_approve(world.headers, session_id)
            self.assertEqual(
                ((lookup.status_code, lookup.json()), (refused.status_code, refused.json())),
                (off, off),
                msg=values.MSG_CLIS_MODE_OFF_STORED,
                abort_on_fail=False,
            )
        blocked = bloom.bloom_cli_exchange(approved, code)
        self.assertEqual(
            (blocked.status_code, blocked.json(), bloom.bloom_count_user_tokens()),
            (values.STATUS_BAD_REQUEST, {"detail": values.CLIS_INVALID}, 0),
            msg=values.MSG_CLIS_MODE_OFF_EXCHANGE,
            abort_on_fail=False,
        )
        approvals = bloom.bloom_list_audit_events("auth.cli_approve")[1:]
        exchanges = bloom.bloom_list_audit_events("auth.cli_exchange")
        stored = bloom.bloom_cli_get_session(pending)
        self.assertEqual(
            (
                [(e.outcome, e.actor_user_id, e.target_id, e.details) for e in approvals],
                [(e.outcome, e.target_id, e.details) for e in exchanges],
                bloom.bloom_cli_stored_ids(),
                (stored.user_id, stored.exchange_code_hash),
            ),
            (
                [
                    ("failure", world.user_id, s, {"reason": "code_mode_disabled"})
                    for s in (pending, approved, expired)
                ],
                [("failure", approved, {"reason": "code_mode_disabled"})],
                {pending, approved, expired},
                (None, None),
            ),
            msg=values.MSG_CLIS_MODE_OFF_AUDIT,
            abort_on_fail=False,
        )

    def bud_code_mode_off_keeps_the_answers_for_a_missing_request(self):
        values, bloom = self.parameters, self.bloom
        world = bloom.bloom_new_cli_world()
        bloom.bloom_set_code_mode(False)
        unknown = bloom.bloom_unknown_session()
        lookup = bloom.bloom_cli_lookup(world.headers, unknown)
        refused = bloom.bloom_cli_approve(world.headers, unknown)
        exchanged = bloom.bloom_cli_exchange(unknown, "code").status_code
        invalid = (values.STATUS_BAD_REQUEST, {"detail": values.CLIS_INVALID})
        self.assertEqual(
            (
                (lookup.status_code, lookup.json()),
                (refused.status_code, refused.json()),
                exchanged,
                bloom.bloom_list_audit_events("auth.cli_approve")[-1].details,
                bloom.bloom_list_audit_events("auth.cli_exchange")[-1].details,
            ),
            (
                invalid,
                invalid,
                values.STATUS_BAD_REQUEST,
                {"reason": "not_pending"},
                {"reason": "unknown_or_unapproved_session"},
            ),
            msg=values.MSG_CLIS_MODE_OFF_MISSING,
            abort_on_fail=False,
        )

    def bud_code_mode_off_still_allows_denying_a_stored_code_request(self):
        values, bloom = self.parameters, self.bloom
        world = bloom.bloom_new_cli_world()
        pending = bloom.bloom_cli_session()
        bloom.bloom_set_code_mode(False)
        denied = bloom.bloom_cli_deny(world.headers, pending)
        self.assertEqual(
            (
                (denied.status_code, denied.json()),
                bloom.bloom_cli_stored_ids(),
                bloom.bloom_cli_lookup(world.headers, pending).status_code,
                [
                    (e.outcome, e.actor_user_id)
                    for e in bloom.bloom_list_audit_events("auth.cli_deny")
                ],
            ),
            (
                (values.STATUS_OK, {}),
                set(),
                values.STATUS_BAD_REQUEST,
                [("success", world.user_id)],
            ),
            msg=values.MSG_CLIS_MODE_OFF_DENY,
            abort_on_fail=False,
        )

    def bud_deny_requires_a_signed_in_account_and_a_strict_body(self):
        values, bloom = self.parameters, self.bloom
        world = bloom.bloom_new_cli_world()
        session_id = bloom.bloom_cli_session()
        unknown_account = bloom.bloom_token_headers({"sub": "999999", "type": "user", "ver": 1})
        statuses = (
            bloom.bloom_cli_post("deny", body={"session_id": session_id}).status_code,
            bloom.bloom_cli_deny(unknown_account, session_id).status_code,
            bloom.bloom_cli_deny(world.headers, session_id, state="x").status_code,
            bloom.bloom_cli_post("deny", world.headers, {}).status_code,
        )
        self.assertEqual(
            statuses,
            (
                values.STATUS_UNAUTHORIZED,
                values.STATUS_UNAUTHORIZED,
                values.STATUS_UNPROCESSABLE,
                values.STATUS_UNPROCESSABLE,
            ),
            msg=values.MSG_CLIS_DENY_GUARD,
            abort_on_fail=False,
        )
        self.assertEqual(
            (bloom.bloom_cli_stored_ids(), bloom.bloom_list_audit_events("auth.cli_deny")),
            ({session_id}, []),
            msg=values.MSG_CLIS_DENY_GUARD_STATE,
            abort_on_fail=False,
        )

    def bud_deny_refuses_a_request_that_is_not_pending(self):
        values, bloom = self.parameters, self.bloom
        world = bloom.bloom_new_cli_world()
        approved = bloom.bloom_cli_session()
        code = bloom.bloom_cli_approve(world.headers, approved).json()["exchange_code"]
        expired = bloom.bloom_cli_session()
        bloom.bloom_cli_expire(expired)
        unknown = bloom.bloom_unknown_session()
        answers = [bloom.bloom_cli_deny(world.headers, s) for s in (approved, expired, unknown)]
        self.assertEqual(
            [(a.status_code, a.json()) for a in answers],
            [(values.STATUS_BAD_REQUEST, {"detail": values.CLIS_INVALID})] * 3,
            msg=values.MSG_CLIS_DENY_NOT_PENDING,
            abort_on_fail=False,
        )
        self.assertEqual(
            (
                [
                    (e.outcome, e.actor_user_id, e.target_id, e.details)
                    for e in bloom.bloom_list_audit_events("auth.cli_deny")
                ],
                bloom.bloom_cli_stored_ids(),
                bloom.bloom_cli_exchange(approved, code).status_code,
            ),
            (
                [
                    ("failure", world.user_id, s, {"reason": "not_pending"})
                    for s in (approved, expired, unknown)
                ],
                {approved, expired},
                values.STATUS_OK,
            ),
            msg=values.MSG_CLIS_DENY_NOT_PENDING_AUDIT,
            abort_on_fail=False,
        )

    def bud_deny_has_the_audience_of_approve(self):
        values, bloom = self.parameters, self.bloom
        world = bloom.bloom_new_cli_world()
        other = bloom.bloom_token_headers({"sub": str(world.other_id), "type": "user", "ver": 1})
        denied = bloom.bloom_cli_deny(other, bloom.bloom_cli_session()).status_code
        approved = (
            bloom.bloom_cli_approve(other, bloom.bloom_cli_session()).json().get("exchange_code")
        )
        self.assertEqual(
            (
                denied,
                bool(approved),
                bloom.bloom_list_audit_events("auth.cli_deny")[0].actor_user_id,
                bloom.bloom_list_audit_events("auth.cli_approve")[0].actor_user_id,
            ),
            (values.STATUS_OK, True, world.other_id, world.other_id),
            msg=values.MSG_CLIS_DENY_AUDIENCE,
            abort_on_fail=False,
        )

    def bud_deny_refuses_a_stored_callback_that_is_no_longer_valid(self):
        values, bloom = self.parameters, self.bloom
        world = bloom.bloom_new_cli_world()
        session_id = bloom.bloom_cli_session(mode="callback", redirect_uri=values.CLIS_CALLBACK)
        bloom.bloom_cli_change_session(session_id, redirect_uri=values.CLIS_EVIL_CALLBACK)
        self.assertEqual(
            (
                bloom.bloom_cli_deny(world.headers, session_id).status_code,
                bloom.bloom_cli_stored_ids(),
                bloom.bloom_list_audit_events("auth.cli_deny")[-1].details,
            ),
            (values.STATUS_BAD_REQUEST, {session_id}, {"reason": "not_pending"}),
            msg=values.MSG_CLIS_DENY_CALLBACK,
            abort_on_fail=False,
        )

    def bud_deny_has_no_rate_limit(self):
        values, bloom = self.parameters, self.bloom
        world = bloom.bloom_new_cli_world()
        unknown = bloom.bloom_unknown_session()
        answers = bloom.bloom_with_login_limit(
            [lambda: bloom.bloom_cli_deny(world.headers, unknown)] * 12
        )
        self.assertEqual(
            {a.status_code for a in answers},
            {values.STATUS_BAD_REQUEST},
            msg=values.MSG_CLIS_DENY_NO_LIMIT,
            abort_on_fail=False,
        )

    def bud_check_and_approve_enforce_their_rate_limit(self):
        values, bloom = self.parameters, self.bloom
        world = bloom.bloom_new_cli_world()
        unknown = bloom.bloom_unknown_session()
        _, request_code = bloom.bloom_cli_challenge()
        body = {"session_id": unknown, "request_code": request_code}
        for path, limit in values.CLIS_SIGNED_IN_LIMITS:
            answers = bloom.bloom_with_login_limit(
                [lambda: bloom.bloom_cli_post(path, world.headers, body)] * (limit + 1)
            )
            self.assertEqual(
                ({a.status_code for a in answers[:-1]}, answers[-1].status_code),
                ({values.STATUS_BAD_REQUEST}, values.STATUS_TOO_MANY),
                msg=values.MSG_CLIS_LIMIT.format(path=path, limit=limit),
                abort_on_fail=False,
            )

    def bud_a_typed_code_mismatch_is_recorded_on_check_and_approve(self):
        values, bloom = self.parameters, self.bloom
        world = bloom.bloom_new_cli_world()
        session_id = bloom.bloom_cli_session()
        wrong = values.CLIS_WRONG_CODE
        statuses = (
            bloom.bloom_cli_check(world.headers, session_id, wrong).status_code,
            bloom.bloom_cli_approve(world.headers, session_id, wrong).status_code,
            bloom.bloom_cli_check(world.headers, session_id).status_code,
            bloom.bloom_cli_check(world.headers, bloom.bloom_unknown_session(), wrong).status_code,
        )
        self.assertEqual(
            statuses,
            (
                values.STATUS_BAD_REQUEST,
                values.STATUS_BAD_REQUEST,
                values.STATUS_NO_CONTENT,
                values.STATUS_BAD_REQUEST,
            ),
            msg=values.MSG_CLIS_MISMATCH,
            abort_on_fail=False,
        )
        mismatches = bloom.bloom_list_audit_events("auth.cli_code_mismatch")
        before = bloom.bloom_list_audit_events("auth.cli_approve")
        bloom.bloom_cli_approve(world.headers, session_id)
        self.assertEqual(
            (
                [
                    (e.outcome, e.actor_user_id, e.target_type, e.target_id, e.details)
                    for e in mismatches
                ],
                before,
                [e.outcome for e in bloom.bloom_list_audit_events("auth.cli_approve")],
            ),
            (
                [
                    (
                        "failure",
                        world.user_id,
                        "cli_auth_session",
                        session_id,
                        {"reason": "request_code_mismatch"},
                    )
                ]
                * 2,
                [],
                ["success"],
            ),
            msg=values.MSG_CLIS_MISMATCH_AUDIT,
            abort_on_fail=False,
        )

    def bud_approval_refuses_a_request_approved_after_its_code_check(self):
        values, bloom = self.parameters, self.bloom
        world = bloom.bloom_new_cli_world()
        session_id = bloom.bloom_cli_session()
        refused = bloom.bloom_approve_after_concurrent_approval(
            world.headers, session_id, world.user_id
        )
        self.assertEqual(
            (
                (refused.status_code, refused.json()),
                bloom.bloom_list_audit_events("auth.cli_approve")[-1].details,
            ),
            (
                (values.STATUS_BAD_REQUEST, {"detail": values.CLIS_INVALID}),
                {"reason": "not_pending"},
            ),
            msg=values.MSG_CLIS_RACE,
            abort_on_fail=False,
        )
