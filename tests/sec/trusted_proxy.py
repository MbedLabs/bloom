"""
* @file     ${tests/sec/trusted_proxy.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    This module tests the client address of audit records and rate limits behind a reverse proxy.
* @author   Amine El Omari
* @date     2026-11-16
* @version  1.0.0
* @note     Base class containing the bud methods of the trusted proxy handling.
"""

from tests.bloom_api_interface import BloomApiInterface
from tests.bloom_test_base import BloomTestCase


class TrustedProxyBase(BloomTestCase):

    interface = BloomApiInterface

    def bud_a_trusted_proxy_forwards_the_callers_address(self):
        values = self.parameters
        proxy, caller = values.TPX_FORWARD
        send = lambda forwarded: self.bloom.bloom_api_send_through_image(
            proxy, forwarded, [values.TPX_NETWORK], headers=values.TPX_FORGED_TOKEN
        )
        for what, forwarded in (("plain", caller), ("forged", f"{values.TPX_FORGED}, {caller}")):
            answer = send(forwarded)
            records = self.bloom.bloom_request_records(answer)
            self.print_variables({"forwarded": forwarded, "recorded": [r.ip for r in records]})
            self.assertEqual(
                (answer.status_code, [r.ip for r in records]),
                (values.STATUS_UNAUTHORIZED, [caller]),
                msg=values.MSG_TPX_FORWARDED.format(what=what),
                abort_on_fail=False,
            )

    def bud_a_forged_header_from_an_untrusted_sender_is_ignored(self):
        values = self.parameters
        trusted, outsider, forged = [values.TPX_NETWORK], values.TPX_OUTSIDER, values.TPX_FORGED
        token = values.TPX_FORGED_TOKEN
        answers = {
            "through nginx": self.bloom.bloom_api_send_through_image(
                outsider, forged, trusted, headers=token
            ),
            "posing as a proxy": self.bloom.bloom_api_send_through_image(
                outsider, f"{forged}, {values.TPX_POSING_HOP}", trusted, headers=token
            ),
            "direct": self.bloom.bloom_api_send_direct(outsider, forged, trusted, headers=token),
        }
        for what, answer in answers.items():
            records = self.bloom.bloom_request_records(answer)
            self.assertEqual(
                [r.ip for r in records],
                [outsider],
                msg=values.MSG_TPX_IGNORED.format(what=what),
                abort_on_fail=False,
            )

    def bud_the_empty_default_records_the_direct_peer(self):
        values = self.parameters
        proxy, caller = values.TPX_DEFAULT
        loaded, _ = self.bloom.bloom_load_trusted_proxies(values.TPX_SECRET)
        self.assertEqual(
            (loaded, self.bloom.bloom_trusted_proxy_setting()),
            ([], []),
            msg=values.MSG_TPX_EMPTY,
            abort_on_fail=False,
        )
        token = values.TPX_FORGED_TOKEN
        answers = {
            "proxied": (
                self.bloom.bloom_api_send_through_image(proxy, caller, headers=token),
                proxy,
            ),
            "direct": (
                self.bloom.bloom_api_send_direct(
                    values.TPX_OUTSIDER, values.TPX_FORGED, headers=token
                ),
                values.TPX_OUTSIDER,
            ),
        }
        for what, (answer, peer) in answers.items():
            self.assertEqual(
                [r.ip for r in self.bloom.bloom_request_records(answer)],
                [peer],
                msg=values.MSG_TPX_DIRECT.format(what=what),
                abort_on_fail=False,
            )

    def bud_repeated_refusals_are_counted_by_the_forwarded_address(self):
        values = self.parameters
        proxy, caller, other = values.TPX_COUNTED
        sends = [
            (
                lambda forwarded=forwarded: self.bloom.bloom_api_send_through_image(
                    proxy, forwarded, [values.TPX_NETWORK], headers=values.TPX_FORGED_TOKEN
                )
            )
            for forwarded in [caller, caller, other, other, caller]
        ]
        self.bloom.bloom_with_refusal_threshold(values.TPX_THRESHOLD, sends)
        detected = [
            (event.ip, event.details["address"], event.details["count"])
            for event in self.bloom.bloom_list_audit_events("security.repeated_refusals")
            if event.ip in (proxy, caller, other)
        ]
        self.print_variables({"detected": detected})
        self.assertEqual(
            detected,
            [(caller, caller, values.TPX_THRESHOLD)],
            msg=values.MSG_TPX_COUNTED,
            abort_on_fail=False,
        )

    def bud_without_trusted_proxies_refusals_are_counted_by_the_proxy(self):
        values = self.parameters
        proxy, caller, other = values.TPX_UNCOUNTED
        sends = [
            (
                lambda forwarded=forwarded: self.bloom.bloom_api_send_through_image(
                    proxy, forwarded, None, headers=values.TPX_FORGED_TOKEN
                )
            )
            for forwarded in [caller, other, caller]
        ]
        self.bloom.bloom_with_refusal_threshold(values.TPX_THRESHOLD, sends)
        detected = [
            (event.ip, event.details["address"], event.details["count"])
            for event in self.bloom.bloom_list_audit_events("security.repeated_refusals")
            if event.ip in (proxy, caller, other)
        ]
        self.print_variables({"detected": detected})
        self.assertEqual(
            detected,
            [(proxy, proxy, values.TPX_THRESHOLD)],
            msg=values.MSG_TPX_UNCOUNTED,
            abort_on_fail=False,
        )

    def bud_callers_behind_a_trusted_proxy_each_have_their_own_login_limit(self):
        values = self.parameters
        proxy, caller, other = values.TPX_OWN_LIMITS
        login = lambda forwarded: self.bloom.bloom_api_send_through_image(
            proxy,
            forwarded,
            [values.TPX_NETWORK],
            method="POST",
            path="/api/auth/login",
            json=values.TPX_WRONG_LOGIN,
        ).status_code
        for who, forwarded in (("first", caller), ("second", other)):
            statuses = self.bloom.bloom_with_login_limit(
                [lambda: login(forwarded)] * (values.TPX_LOGIN_LIMIT + 1)
            )
            self.print_variables({who: statuses})
            self.assertEqual(
                statuses,
                values.TPX_LIMITED,
                msg=values.MSG_TPX_OWN_LIMIT.format(who=who),
                abort_on_fail=False,
            )

    def bud_a_forged_header_from_an_untrusted_sender_does_not_escape_the_login_limit(self):
        values = self.parameters
        trusted, outsider, body = [values.TPX_NETWORK], values.TPX_OUTSIDER, values.TPX_WRONG_LOGIN
        forged = [f"198.51.100.{n}" for n in range(values.TPX_LOGIN_LIMIT + 1)]
        image = self.bloom.bloom_api_send_through_image
        sends = (
            [
                lambda a=a: image(
                    outsider, a, trusted, method="POST", path="/api/auth/login", json=body
                )
                for a in forged[:4]
            ]
            + [
                lambda a=a: image(
                    outsider,
                    f"{a}, {values.TPX_POSING_HOP}",
                    trusted,
                    method="POST",
                    path="/api/auth/login",
                    json=body,
                )
                for a in forged[4:8]
            ]
            + [
                lambda a=a: self.bloom.bloom_api_send_direct(
                    outsider, a, trusted, method="POST", path="/api/auth/login", json=body
                )
                for a in forged[8:]
            ]
        )
        statuses = [answer.status_code for answer in self.bloom.bloom_with_login_limit(sends)]
        self.print_variables({"statuses": statuses})
        self.assertEqual(
            statuses, values.TPX_LIMITED, msg=values.MSG_TPX_NO_ESCAPE, abort_on_fail=False
        )

    def bud_without_trusted_proxies_callers_behind_a_proxy_share_the_login_limit(self):
        values = self.parameters
        proxy, caller, other = values.TPX_SHARED
        image = lambda received_from, forwarded=None: self.bloom.bloom_api_send_through_image(
            received_from,
            forwarded,
            method="POST",
            path="/api/auth/login",
            json=values.TPX_WRONG_LOGIN,
        ).status_code
        sends = [lambda: image(proxy, caller)] * values.TPX_LOGIN_LIMIT + [
            lambda: image(proxy, other),
            lambda: image(values.TPX_OUTSIDER),
        ]
        statuses = self.bloom.bloom_with_login_limit(sends)
        self.print_variables({"statuses": statuses})
        self.assertEqual(
            statuses[:-1], values.TPX_LIMITED, msg=values.MSG_TPX_SHARED, abort_on_fail=False
        )
        self.assertEqual(
            statuses[-1],
            values.STATUS_UNAUTHORIZED,
            msg=values.MSG_TPX_ELSEWHERE,
            abort_on_fail=False,
        )

    def bud_the_client_address_is_the_right_most_untrusted_hop(self):
        values = self.parameters
        for (peer, *forwarded), expected in values.TPX_ADDRESS_CASES:
            self.assertEqual(
                self.bloom.bloom_client_address([values.TPX_NETWORK], peer, *forwarded),
                expected,
                msg=values.MSG_TPX_ADDRESS.format(peer=peer, forwarded=forwarded),
                abort_on_fail=False,
            )

    def bud_the_empty_default_keys_rate_limits_on_the_direct_peer(self):
        values = self.parameters
        for scope in values.TPX_DEFAULT_KEY_SCOPES:
            key, remote = self.bloom.bloom_rate_limit_keys([], *scope)
            self.assertEqual(
                key, remote, msg=values.MSG_TPX_DEFAULT_KEY.format(scope=scope), abort_on_fail=False
            )

    def bud_rate_limits_are_keyed_on_the_resolved_client_address(self):
        values = self.parameters
        for scope, expected in values.TPX_KEY_CASES:
            key, _ = self.bloom.bloom_rate_limit_keys([values.TPX_NETWORK], *scope)
            self.assertEqual(
                key, expected, msg=values.MSG_TPX_KEY.format(scope=scope), abort_on_fail=False
            )

    def bud_the_setting_reads_a_json_array_of_networks(self):
        values = self.parameters
        loaded = self.bloom.bloom_load_trusted_proxies(
            values.TPX_SECRET, env_value=values.TPX_ENV_NETWORKS
        )
        self.print_variables({"loaded": loaded})
        self.assertEqual(
            loaded,
            (values.TPX_LOADED_NETWORKS, None),
            msg=values.MSG_TPX_LOADED,
            abort_on_fail=False,
        )

    def bud_the_setting_refuses_an_entry_that_is_not_a_network(self):
        values = self.parameters
        loaded = self.bloom.bloom_load_trusted_proxies(
            values.TPX_SECRET, networks=values.TPX_NOT_A_NETWORK
        )
        self.print_variables({"loaded": loaded})
        self.assertEqual(
            loaded, (None, "ValidationError"), msg=values.MSG_TPX_REFUSED, abort_on_fail=False
        )
