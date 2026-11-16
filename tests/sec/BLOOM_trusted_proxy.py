"""
* @file     ${tests/sec/BLOOM_trusted_proxy.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    X-Forwarded-For is read only from a network in TRUSTED_PROXY_NETWORKS, through the outer proxy, nginx and uvicorn.
* @author   Amine El Omari
* @date     2026-11-16
* @version  1.0.0
* @note     This module tests the application reached as the image's nginx reaches it, with forged tokens and wrong sign-ins.
"""

from tests.sec.trusted_proxy import TrustedProxyBase


class TrustedProxyTest(TrustedProxyBase):

    def setUpClass(self):
        super().setUpClass()
        self.bloom.bloom_start_full_api()

    def tearDownClass(self):
        super().tearDownClass()


if __name__ == "__main__":
    TrustedProxyTest().run()
