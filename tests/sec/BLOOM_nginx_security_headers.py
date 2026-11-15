"""
* @file     ${tests/sec/BLOOM_nginx_security_headers.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    Every nginx location carries the security headers, including ones with own headers.
* @author   Amine El Omari
* @date     2026-11-11
* @version  1.0.0
* @note     This module tests nginx.conf, security-headers.conf and the Dockerfile.
"""

from tests.sec.nginx_security_headers import NginxSecurityHeadersBase


class NginxSecurityHeadersTest(NginxSecurityHeadersBase):

    def setUpClass(self):
        super().setUpClass()
        self.tc_headers = self.bloom.bloom_read_repo_text(self.parameters.NGINX_HEADERS_CONF)
        self.tc_server_head = self.bloom.bloom_nginx_server_head(self.parameters.NGINX_CONF)
        self.tc_locations = self.bloom.bloom_nginx_locations(self.parameters.NGINX_CONF)
        self.tc_dockerfile = self.bloom.bloom_read_repo_text(self.parameters.DOCKERFILE)

    def tearDownClass(self):
        super().tearDownClass()


if __name__ == "__main__":
    NginxSecurityHeadersTest().run()
