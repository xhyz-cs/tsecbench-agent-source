#!/usr/bin/env python3
"""Offline integrity checks for vendored reverse-engineering tool releases."""
from pathlib import Path
import hashlib
import unittest
import zipfile

ROOT = Path(__file__).resolve().parents[1]
RELEASES = ROOT / "docker" / "tools" / "releases"
ARCHIVE = RELEASES / "nikto-2.6.1.zip"

class VendoredToolReleaseTests(unittest.TestCase):
    def test_nikto_archive_checksum_and_contents(self):
        records = {}
        for line in (RELEASES / "SOURCES.sha256").read_text().splitlines():
            fields = line.strip().split()
            if len(fields) == 2:
                records[fields[1]] = fields[0]
        self.assertIn(ARCHIVE.name, records)
        self.assertEqual(hashlib.sha256(ARCHIVE.read_bytes()).hexdigest(), records[ARCHIVE.name])
        with zipfile.ZipFile(ARCHIVE) as archive:
            self.assertIsNone(archive.testzip())
            self.assertIn("nikto-2.6.1/program/nikto.pl", archive.namelist())
            self.assertIn("nikto-2.6.1/program/nikto.conf.default", archive.namelist())
            self.assertIn("nikto-2.6.1/COPYING", archive.namelist())

    def test_dockerfile_requires_and_installs_nikto_and_full_symbex(self):
        dockerfile = (ROOT / "docker" / "Dockerfile").read_text()
        self.assertIn("test -f /tmp/rel/nikto-2.6.1.zip", dockerfile)
        self.assertIn("COPY --from=bin-tools /opt/nikto /opt/nikto", dockerfile)
        self.assertIn("ln -sf /opt/nikto/program/nikto.pl /usr/local/bin/nikto", dockerfile)
        self.assertIn("ARG WITH_SYMBEX=1", dockerfile)
        self.assertIn("perl -c /opt/nikto/program/nikto.pl", dockerfile)
        self.assertIn("nikto -Version -nocheck", dockerfile)

if __name__ == "__main__":
    unittest.main()
