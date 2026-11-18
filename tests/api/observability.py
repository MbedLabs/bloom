"""
* @file     ${tests/api/observability.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    This module tests request ids, the request audit event, the metrics page and JSON logs.
* @author   Amine El Omari
* @date     2026-11-16
* @version  1.0.0
* @note     Base class containing the bud methods of the request observability.
"""

import json

from tests.bloom_api_interface import BloomApiInterface
from tests.bloom_test_base import BloomTestCase


class ObservabilityBase(BloomTestCase):

    interface = BloomApiInterface

    def bud_each_request_leaves_one_request_event(self):
        values = self.parameters
        ping = self.bloom.bloom_api_raw("GET", "/api/ping", params={"q": "value"})
        missing = self.bloom.bloom_api_raw("GET", "/api/nowhere")
        first, second = self.bloom.bloom_list_every_audit_event()[-2:]
        self.print_variables({"first": first.details, "second": second.details})
        self.assertEqual(
            (
                first.action,
                first.actor_type,
                first.outcome,
                first.request_id,
                first.details["route"],
            ),
            ("api.request", "anonymous", "success", ping.headers["x-request-id"], "/api/ping"),
            msg=values.MSG_OBS_PING_EVENT,
            abort_on_fail=False,
            method="GET",
            endpoint="/api/ping",
        )
        self.assertEqual(
            (first.details["query"], "value" in json.dumps(first.details)),
            (["q"], False),
            msg=values.MSG_OBS_QUERY,
            abort_on_fail=False,
        )
        self.assertEqual(
            (missing.status, second.details["route"], second.details["status"], second.outcome),
            (values.STATUS_NOT_FOUND, "unmatched", values.STATUS_NOT_FOUND, "denied"),
            msg=values.MSG_OBS_UNMATCHED,
            abort_on_fail=False,
            method="GET",
            endpoint="/api/nowhere",
        )

    def bud_an_answer_carries_a_generated_request_id(self):
        answer = self.bloom.bloom_api_raw("GET", "/api/ping")
        request_id = answer.headers.get("x-request-id") or ""
        self.print_variables({"request id": request_id})
        self.assertEqual(
            (answer.status, len(request_id) >= 16),
            (self.parameters.STATUS_OK, True),
            msg=self.parameters.MSG_OBS_GENERATED,
            abort_on_fail=False,
        )

    def bud_a_sent_request_id_is_returned(self):
        answer = self.bloom.bloom_api_raw(
            "GET", "/api/ping", headers={"X-Request-ID": self.parameters.OBS_TRACE}
        )
        self.assertEqual(
            answer.headers.get("x-request-id"),
            self.parameters.OBS_TRACE,
            msg=self.parameters.MSG_OBS_PROPAGATED,
            abort_on_fail=False,
        )

    def bud_the_metrics_page_uses_the_prometheus_format(self):
        self.bloom.bloom_api_raw("GET", "/api/ping")
        metrics = self.bloom.bloom_api_metrics()
        self.assertEqual(
            (metrics.status, "text/plain" in metrics.headers["content-type"]),
            (self.parameters.STATUS_OK, True),
            msg=self.parameters.MSG_OBS_METRICS,
            abort_on_fail=False,
            method="GET",
            endpoint="/api/metrics",
        )
        for name in self.parameters.OBS_METRICS:
            self.assertIn(
                name,
                metrics.text,
                msg=self.parameters.MSG_OBS_METRIC.format(name=name),
                abort_on_fail=False,
            )

    def bud_metrics_can_be_turned_off_404(self):
        self.assertEqual(
            self.bloom.bloom_api_metrics(enabled=False).status,
            self.parameters.STATUS_NOT_FOUND,
            msg=self.parameters.MSG_OBS_DISABLED,
            abort_on_fail=False,
            method="GET",
            endpoint="/api/metrics",
        )

    def bud_a_log_record_is_formatted_as_json(self):
        payload = self.bloom.bloom_format_log_record("hello %s", ("world",), "req-abc")
        self.print_variables({"payload": payload})
        self.assertEqual(
            (payload["message"], payload["level"], payload["logger"], payload["request_id"]),
            ("hello world", "INFO", "bloom.test", "req-abc"),
            msg=self.parameters.MSG_OBS_JSON,
            abort_on_fail=False,
        )

    def bud_setting_up_logging_twice_keeps_one_handler(self):
        self.assertEqual(
            self.bloom.bloom_set_up_logging_twice(),
            (1, True),
            msg=self.parameters.MSG_OBS_LOGGING,
            abort_on_fail=False,
        )
