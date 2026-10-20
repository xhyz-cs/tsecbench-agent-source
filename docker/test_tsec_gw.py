# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 James and minc
import unittest

import tsec_gw


class GatewayRewriteTests(unittest.TestCase):
    def test_deepseek_anthropic_endpoint_is_allowed_and_rewritten(self):
        self.assertEqual(
            tsec_gw.convert("https://api.deepseek.com/anthropic"),
            "http://api.deepseek.com.tsecbench.gw/anthropic",
        )

    def test_deepseek_official_api_is_validated_without_rewrite(self):
        url = "https://api.deepseek.com/anthropic"
        self.assertEqual(tsec_gw.validate_direct(url), url)

    def test_direct_requires_https_and_rejects_userinfo_or_fragment(self):
        for url in ("http://api.deepseek.com/anthropic", "https://user:pass@api.deepseek.com/anthropic", "https://api.deepseek.com/anthropic#x"):
            with self.subTest(url=url), self.assertRaises(SystemExit):
                tsec_gw.validate_direct(url)

    def test_allowed_gateway_url_is_idempotent(self):
        url = "http://api.deepseek.com.tsecbench.gw/anthropic"
        self.assertEqual(tsec_gw.convert(url), url)
        self.assertTrue(tsec_gw.is_gateway_form(url))

    def test_unlisted_public_host_is_rejected(self):
        with self.assertRaises(SystemExit):
            tsec_gw.convert("https://attacker.example/v1")

    def test_allowlisted_service_requires_documented_path(self):
        with self.assertRaises(SystemExit):
            tsec_gw.convert("https://dashscope.aliyuncs.com/v1")
        self.assertIn(
            "dashscope.aliyuncs.com.tsecbench.gw/compatible-mode",
            tsec_gw.convert("https://dashscope.aliyuncs.com/compatible-mode/v1"),
        )

    def test_userinfo_and_fragments_are_rejected(self):
        with self.assertRaises(SystemExit):
            tsec_gw.convert("https://user:pass@api.deepseek.com/anthropic")
        with self.assertRaises(SystemExit):
            tsec_gw.convert("https://api.deepseek.com/anthropic#secret")


if __name__ == "__main__":
    unittest.main()
