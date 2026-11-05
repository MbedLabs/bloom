"""The CLI sign-in approval page of the built Bloom UI in Chromium, its API calls answered from fixtures."""

import functools
import json
import os
import threading
from datetime import datetime, timedelta, timezone
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse

from budtestlibrary import BudTestCase
from playwright.sync_api import TimeoutError as PlaywrightTimeout
from playwright.sync_api import sync_playwright

from tests.budtests.config import UiCliAuth as c
from tests.budtests.messages import UiCliAuth as m
from tests.budtests.parameters import UiCliAuth as p


class _BuiltUi(SimpleHTTPRequestHandler):
    """Serves the built UI; a path without a file answers index.html."""

    def send_head(self):
        """The file of the path, or index.html when there is none."""
        if not os.path.isfile(self.translate_path(self.path.split("?", 1)[0])):
            self.path = "/index.html"
        return super().send_head()

    def log_message(self, format, *args):
        """Writes no access log."""


def _iso(moment: datetime) -> str:
    """A UTC moment as ISO 8601."""
    return moment.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


class UiCliAuth(BudTestCase):
    """A signed-in user answers a pending CLI sign-in on Bloom's approval page."""

    def setUpClass(self):
        """Serve the built UI on a free loopback port and start Chromium."""
        handler = functools.partial(_BuiltUi, directory=str(c.DIST))
        self.server = ThreadingHTTPServer((c.HOST, 0), handler)
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        self.base = f"http://{c.HOST}:{self.server.server_address[1]}"
        self.playwright = sync_playwright().start()
        self.browser = self.playwright.chromium.launch()

    def tearDownClass(self):
        """Close Chromium and stop serving the UI."""
        self.browser.close()
        self.playwright.stop()
        self.server.shutdown()
        self.server.server_close()

    def setUp(self):
        """A fresh page with a code-mode session requested a minute ago, expiring in ten minutes, and
        the default answers of every API call."""
        now = datetime.now(timezone.utc)
        self.created_at = _iso(now - timedelta(minutes=p.CREATED_MINUTES_AGO))
        self.expires_at = _iso(now + timedelta(minutes=p.EXPIRES_IN_MINUTES))
        self.session = {
            "session_id": p.SESSION_ID,
            "client_name": p.CLIENT_NAME,
            "mode": "code",
            "redirect_uri": None,
            "created_at": self.created_at,
            "expires_at": self.expires_at,
            "consumed": False,
        }
        self.answers = {
            ("POST", c.REFRESH_PATH): [(p.OK, p.SIGN_IN)],
            ("GET", c.ME_PATH): [(p.OK, p.USER)],
            ("GET", c.SETUP_PATH): [(p.OK, p.SETUP)],
            ("GET", self.session_path()): [(p.OK, self.session)],
            ("POST", c.CHECK_PATH): [(p.OK, p.NOTHING)],
            ("POST", c.APPROVE_PATH): [
                (p.OK, {"exchange_code": p.EXCHANGE_CODE, "expires_at": self.expires_at})
            ],
            ("POST", c.DENY_PATH): [(p.OK, p.NOTHING)],
        }
        self.calls = []
        self.held = []
        self.context = self.browser.new_context(permissions=c.CLIPBOARD)
        self.page = self.context.new_page()
        self.page.set_default_timeout(c.TIMEOUT_MS)
        self.page.route(c.API_PATTERN, self._answer)
        self.page.route(
            c.LOOPBACK_PATTERN,
            lambda route: route.fulfill(status=p.OK, content_type=c.HTML, body=""),
        )

    def tearDown(self):
        """Close the page."""
        self.context.close()

    def _answer(self, route):
        """Record an API call and answer it with the next answer set for it, holding it when that
        answer is p.HOLD, or with 404."""
        request = route.request
        path = urlparse(request.url).path
        self.calls.append(
            (request.method, path, request.post_data_json if request.post_data else None)
        )
        queue = self.answers.get((request.method, path))
        if not queue:
            route.fulfill(status=p.MISSING, content_type=c.JSON, body=json.dumps(p.NOT_FOUND))
            return
        answer = queue.pop(0) if len(queue) > 1 else queue[0]
        if answer == p.HOLD:
            self.held.append(route)
            return
        status, body = answer
        route.fulfill(status=status, content_type=c.JSON, body=json.dumps(body))

    def session_path(self) -> str:
        """The path of the session lookup."""
        return c.SESSION_PATH.format(session_id=p.SESSION_ID)

    def answer(self, method: str, path: str, *answers):
        """Set the answers of an API call, used in order; the last one repeats."""
        self.answers[(method, path)] = list(answers)

    def callback_mode(self, callback: str = p.CALLBACK):
        """Make the session a callback-mode request for a loopback callback."""
        self.answer(
            "GET",
            self.session_path(),
            (p.OK, {**self.session, "mode": "callback", "redirect_uri": callback}),
        )

    def open_request(self):
        """Open the approval page of the pending session and wait for its first box."""
        self.page.goto(self.base + c.PAGE_ROUTE.format(session_id=p.SESSION_ID))
        self.shown(self.box(1))

    def shown(self, locator) -> bool:
        """Whether the locator becomes visible within the timeout."""
        try:
            locator.first.wait_for(state="visible")
            return True
        except PlaywrightTimeout:
            return False

    def text(self, text: str):
        """The element showing exactly a text."""
        return self.page.get_by_text(text, exact=True)

    def alert(self):
        """The alert of the page."""
        return self.page.get_by_role("alert")

    def alert_text(self) -> str:
        """The text of the first alert once one is shown, or an empty text."""
        return self.alert().first.inner_text() if self.shown(self.alert()) else ""

    def box(self, number: int):
        """The request code box at a position."""
        return self.page.get_by_label(m.BOX_NAME.format(number=number, boxes=p.BOXES), exact=True)

    def code_field(self):
        """The one-time sign-in code field."""
        return self.page.get_by_label(m.CODE_LABEL, exact=True)

    def values(self) -> list[str]:
        """The characters in the boxes, in order."""
        return [self.box(number).input_value() for number in range(1, p.BOXES + 1)]

    def button(self, name: str):
        """The button with a name."""
        return self.page.get_by_role("button", name=name, exact=True)

    def type_code(self, text: str):
        """Type text into the boxes from the first one."""
        self.box(1).click()
        self.page.keyboard.type(text)

    def paste(self, text: str):
        """Paste text into the first box the way a browser delivers a clipboard paste."""
        self.box(1).evaluate(
            """(element, text) => {
                const data = new DataTransfer();
                data.setData('text', text);
                element.dispatchEvent(new ClipboardEvent('paste', {clipboardData: data, bubbles: true, cancelable: true}));
            }""",
            text,
        )

    def matching_code(self):
        """Type the matching code and wait for the page to confirm it."""
        self.type_code(p.TYPED)
        self.assertTrue(self.shown(self.text(m.MATCH)), f"{m.MATCH!r} is shown", abort_on_fail=True)

    def approve_matching_code(self):
        """Open the request, type the matching code and press Approve."""
        self.open_request()
        self.matching_code()
        self.button(m.APPROVE).click()

    def bodies(self, method: str, path: str) -> list:
        """The bodies the page sent to an API call, in order."""
        return [body for (sent, to, body) in self.calls if sent == method and to == path]

    def lookups(self) -> int:
        """How often the page looked the session up."""
        return len(
            [to for (sent, to, _) in self.calls if sent == "GET" and to == self.session_path()]
        )

    def local_time(self, value: str) -> str:
        """A time the way the page's browser writes it."""
        return self.page.evaluate("value => new Date(value).toLocaleString()", value)

    def page_text(self) -> str:
        """The text of the whole page."""
        return self.page.inner_text("body")

    def refused_callback(self, target: str):
        """An approval answered with a callback target is refused with the invalid callback alert and
        the browser stays on the page."""
        self.callback_mode()
        self.answer("POST", c.APPROVE_PATH, (p.OK, {"redirect_to": target}))
        self.open_request()
        page = self.page.url
        self.matching_code()
        self.button(m.APPROVE).click()
        self.assertIn(
            member=m.INVALID_CALLBACK, container=self.alert_text(), msg=f"{target!r} is refused"
        )
        self.assertEqual(self.page.url, page, f"the browser stays on the page for {target!r}")

    def bud_shows_the_consent_and_a_copyable_one_time_code(self):
        """The client, the account and the one-time code destination are shown; Approve shows the code,
        Copy code copies it and Approve is gone."""
        self.open_request()
        shown = self.page_text()
        self.assertIn(member=p.CLIENT_NAME, container=shown, msg=f"{p.CLIENT_NAME!r} is shown")
        self.assertIn(
            member=m.CODE_DESTINATION, container=shown, msg=f"{m.CODE_DESTINATION!r} is shown"
        )
        self.assertEqual(self.lookups(), p.ONE, "the session is looked up once")
        self.matching_code()
        self.button(m.APPROVE).click()
        self.assertTrue(
            self.shown(self.code_field()),
            "the one-time sign-in code field is shown",
            abort_on_fail=True,
        )
        self.assertEqual(
            self.code_field().input_value(), p.EXCHANGE_CODE, "the field holds the one-time code"
        )
        self.assertEqual(
            self.bodies("POST", c.APPROVE_PATH),
            [{"session_id": p.SESSION_ID, "request_code": p.CODE}],
            "Approve sends the session and the code",
        )
        self.button(m.COPY).click()
        self.assertTrue(self.shown(self.text(m.COPIED)), f"{m.COPIED!r} is shown")
        self.assertEqual(
            self.page.evaluate("navigator.clipboard.readText()"),
            p.EXCHANGE_CODE,
            "the code is copied",
        )
        self.assertEqual(self.button(m.APPROVE).count(), 0, "Approve is gone")

    def bud_shows_the_unverified_client_name_the_account_the_request_time_and_the_expiry(self):
        """Empty boxes, the help, the unverified client name, the account, both times and the warning,
        without Cancel."""
        self.open_request()
        self.assertEqual(self.values(), p.EMPTY, "the boxes are empty")
        account = m.ACCOUNT.format(name=p.USER["full_name"], email=p.USER["email"])
        times = m.TIMES.format(
            requested=self.local_time(self.created_at), expires=self.local_time(self.expires_at)
        )
        shown = self.page_text()
        for text in (m.HELP, m.UNVERIFIED, account, times, m.WARNING):
            self.assertIn(member=text, container=shown, msg=f"{text!r} is shown")
        self.assertEqual(self.button(m.CANCEL).count(), 0, "no Cancel is shown")

    def bud_warns_before_approving_a_code_request_and_repeats_the_warning_with_the_code(self):
        """A code request shows the code warning; after Approve the code comes with its warning and
        Deny is gone."""
        self.open_request()
        self.assertTrue(self.shown(self.text(m.CODE_WARNING)), "the code warning is shown")
        self.matching_code()
        self.button(m.APPROVE).click()
        self.assertTrue(self.shown(self.text(m.PASTE_ONLY)), f"{m.PASTE_ONLY!r} is shown")
        self.assertEqual(self.button(m.DENY).count(), 0, "Deny is gone")

    def bud_a_callback_request_shows_no_code_warning(self):
        """A callback request shows the boxes and no code warning."""
        self.callback_mode()
        self.open_request()
        self.assertTrue(self.shown(self.box(1)), "the boxes are shown")
        self.assertEqual(self.text(m.CODE_WARNING).count(), 0, "no code warning is shown")

    def bud_a_denial_answer_to_an_approval_is_refused(self):
        """An approval answered with a denial callback is refused."""
        self.refused_callback(p.DENIAL_AS_APPROVAL)

    def bud_a_failed_approval_shows_no_code(self):
        """A failed approval shows the server's alert and no code field."""
        self.answer("POST", c.APPROVE_PATH, (p.SERVER_ERROR, p.ALREADY_APPROVED))
        self.approve_matching_code()
        self.assertIn(
            member=m.NEW_SIGN_IN_LINK,
            container=self.alert_text(),
            msg="the alert asks for a new sign-in link",
        )
        self.assertEqual(self.code_field().count(), 0, "no code field is shown")

    def bud_an_approval_without_a_code_asks_for_a_new_link(self):
        """An approval answer without a code shows the new link alert."""
        self.answer("POST", c.APPROVE_PATH, (p.OK, {"expires_at": self.expires_at}))
        self.approve_matching_code()
        self.assertIn(
            member=m.NEW_LINK, container=self.alert_text(), msg=f"the alert says {m.NEW_LINK!r}"
        )

    def bud_a_failing_clipboard_asks_to_copy_by_hand(self):
        """When the clipboard refuses, Copy code asks to copy the code by hand."""
        self.page.add_init_script(c.FAILING_CLIPBOARD)
        self.approve_matching_code()
        self.button(m.COPY).click()
        self.assertTrue(self.shown(self.text(m.COPY_BY_HAND)), f"{m.COPY_BY_HAND!r} is shown")

    def bud_an_external_callback_is_refused(self):
        """An approval answered with a callback on another host is refused."""
        self.refused_callback(p.EXTERNAL)

    def bud_approved_callbacks_go_to_their_loopback_listener(self):
        """Approve in callback mode goes to the registered loopback callback on 127.0.0.1, localhost and
        [::1]."""
        for callback, shown in p.APPROVED_CALLBACKS.items():
            self.callback_mode(callback)
            self.answer(
                "POST",
                c.APPROVE_PATH,
                (p.OK, {"redirect_to": p.APPROVED.format(callback=callback)}),
            )
            self.approve_matching_code()
            try:
                self.page.wait_for_url(shown)
            except PlaywrightTimeout:
                pass
            self.assertEqual(self.page.url, shown, f"the browser goes to {shown}")

    def bud_invalid_callback_answers_are_refused(self):
        """Every malformed or foreign approval callback is refused."""
        for target in p.INVALID_CALLBACKS:
            self.refused_callback(target)

    def bud_the_session_answer_puts_no_code_in_the_boxes(self):
        """A request code in the session answer appears neither in the boxes nor on the page."""
        self.answer("GET", self.session_path(), (p.OK, {**self.session, "request_code": p.CODE}))
        self.open_request()
        self.assertEqual(self.values(), p.EMPTY, "the boxes are empty")
        self.assertNotIn(member=p.CODE, container=self.page_text(), msg=f"{p.CODE!r} is not shown")

    def bud_a_typed_code_is_checked_once_at_eight_characters(self):
        """Typed lower-case letters fill the boxes in upper case and the complete code is checked once."""
        self.open_request()
        self.matching_code()
        self.assertEqual(self.values(), p.CHARACTERS, f"the boxes hold {p.CHARACTERS}")
        self.assertEqual(
            self.bodies("POST", c.CHECK_PATH),
            [{"session_id": p.SESSION_ID, "request_code": p.CODE}],
            "the code is checked once",
        )

    def bud_a_pasted_code_with_a_space_is_checked(self):
        """A pasted code with a space fills every box and is checked once."""
        self.open_request()
        self.paste(p.PASTED)
        self.assertTrue(self.shown(self.text(m.MATCH)), f"{m.MATCH!r} is shown")
        self.assertEqual(self.values(), p.CHARACTERS, f"the boxes hold {p.CHARACTERS}")
        self.assertEqual(len(self.bodies("POST", c.CHECK_PATH)), p.ONE, "the code is checked once")

    def bud_approve_is_enabled_only_while_the_checked_code_matches(self):
        """Approve is disabled while the code is incomplete, enabled once it matches, and disabled again
        after an edit."""
        self.open_request()
        self.assertTrue(
            self.button(m.APPROVE).is_disabled(), "Approve is disabled with empty boxes"
        )
        self.type_code(p.SEVEN)
        self.assertTrue(
            self.button(m.APPROVE).is_disabled(), "Approve is disabled with seven characters"
        )
        self.page.keyboard.type(p.EIGHTH)
        self.assertTrue(self.shown(self.text(m.MATCH)), f"{m.MATCH!r} is shown")
        self.assertTrue(
            self.button(m.APPROVE).is_enabled(), "Approve is enabled once the code matches"
        )
        self.box(p.BOXES).press("Backspace")
        self.assertTrue(self.button(m.APPROVE).is_disabled(), "Approve is disabled after an edit")
        self.assertEqual(self.text(m.MATCH).count(), 0, f"{m.MATCH!r} is gone after an edit")

    def bud_a_mismatch_hides_the_server_text_and_keeps_approve_disabled(self):
        """A refused check for a pending request shows the mismatch, no new link text, and looks the
        session up again."""
        self.answer("POST", c.CHECK_PATH, (p.BAD_REQUEST, p.REFUSED))
        self.open_request()
        self.type_code(p.WRONG)
        self.assertTrue(self.shown(self.text(m.MISMATCH)), f"{m.MISMATCH!r} is shown")
        self.assertNotIn(
            member=m.NEW_SIGN_IN_LINK, container=self.page_text(), msg="no new link text is shown"
        )
        self.assertTrue(self.button(m.APPROVE).is_disabled(), "Approve stays disabled")
        self.assertEqual(self.lookups(), p.TWO, "the session is looked up again after the refusal")

    def bud_a_refused_check_for_a_gone_request_asks_for_a_new_link(self):
        """A refused check whose second session lookup is refused shows the new link alert and no
        Approve."""
        self.answer("POST", c.CHECK_PATH, (p.BAD_REQUEST, p.REFUSED))
        self.answer("GET", self.session_path(), (p.OK, self.session), (p.BAD_REQUEST, p.REFUSED))
        self.open_request()
        self.type_code(p.WRONG)
        self.assertIn(
            member=m.NEW_SIGN_IN_LINK,
            container=self.alert_text(),
            msg="the alert asks for a new sign-in link",
        )
        self.assertEqual(self.button(m.APPROVE).count(), 0, "no Approve is shown")

    def bud_a_429_on_check_asks_to_wait(self):
        """A check answered 429 asks to wait and keeps Approve disabled."""
        self.answer("POST", c.CHECK_PATH, (p.TOO_MANY, p.LIMITED))
        self.open_request()
        self.type_code(p.TYPED)
        self.assertTrue(self.shown(self.text(m.LIMITED)), f"{m.LIMITED!r} is shown")
        self.assertTrue(self.button(m.APPROVE).is_disabled(), "Approve is disabled")

    def bud_a_429_on_approve_asks_to_wait(self):
        """An approval answered 429 asks to wait and disables Approve."""
        self.answer("POST", c.APPROVE_PATH, (p.TOO_MANY, p.LIMITED))
        self.approve_matching_code()
        self.assertTrue(self.shown(self.text(m.LIMITED)), f"{m.LIMITED!r} is shown")
        self.assertTrue(self.button(m.APPROVE).is_disabled(), "Approve is disabled")

    def bud_a_400_on_approve_for_a_pending_request_shows_the_mismatch(self):
        """An approval answered 400 while the request is still pending shows the mismatch and no alert."""
        self.answer("POST", c.APPROVE_PATH, (p.BAD_REQUEST, p.REFUSED))
        self.approve_matching_code()
        self.assertTrue(self.shown(self.text(m.MISMATCH)), f"{m.MISMATCH!r} is shown")
        self.assertEqual(self.alert().count(), 0, "no alert is shown")

    def bud_a_check_answer_for_an_edited_code_is_ignored(self):
        """A check answer that arrives after the code was edited leaves the page without a match."""
        self.answer("POST", c.CHECK_PATH, p.HOLD)
        self.open_request()
        self.type_code(p.TYPED)
        self.page.wait_for_timeout(c.SETTLE_MS)
        self.box(p.BOXES).press("Backspace")
        for route in self.held:
            route.fulfill(status=p.OK, content_type=c.JSON, body=json.dumps(p.NOTHING))
        self.page.wait_for_timeout(c.SETTLE_MS)
        self.assertEqual(len(self.bodies("POST", c.CHECK_PATH)), p.ONE, "the code was checked once")
        self.assertEqual(self.text(m.MATCH).count(), 0, f"{m.MATCH!r} is not shown")
        self.assertTrue(self.button(m.APPROVE).is_disabled(), "Approve is disabled")

    def bud_deny_with_an_empty_code_field(self):
        """Deny with empty boxes ends the request and sends only the session."""
        self.open_request()
        self.assertEqual(self.values(), p.EMPTY, "the boxes are empty")
        self.button(m.DENY).click()
        self.assertTrue(self.shown(self.text(m.DENIED)), f"{m.DENIED!r} is shown")
        self.assertEqual(
            self.bodies("POST", c.DENY_PATH),
            [{"session_id": p.SESSION_ID}],
            "Deny sends only the session",
        )

    def bud_an_approved_code_is_cleared_when_the_request_expires(self):
        """A one-time code shown for a request about to expire is replaced by the new link alert at the
        expiry."""
        expires = _iso(datetime.now(timezone.utc) + timedelta(seconds=p.EXPIRES_IN_SECONDS))
        self.answer("GET", self.session_path(), (p.OK, {**self.session, "expires_at": expires}))
        self.approve_matching_code()
        self.assertTrue(
            self.shown(self.code_field()),
            "the one-time sign-in code field is shown",
            abort_on_fail=True,
        )
        self.assertEqual(
            self.code_field().input_value(), p.EXCHANGE_CODE, "the field holds the one-time code"
        )
        self.assertIn(
            member=m.NEW_LINK,
            container=self.alert_text(),
            msg=f"at the expiry the alert says {m.NEW_LINK!r}",
        )
        self.assertEqual(self.code_field().count(), 0, "the code field is gone at the expiry")
