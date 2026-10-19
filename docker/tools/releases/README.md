# Pinned local tool releases

The build consumes these vendored releases and validates each archive against `SOURCES.sha256` before extraction:

- Ghidra 12.1.4 and JADX 1.5.6 (large reverse-engineering packages).
- Nikto 2.6.1 source archive from the upstream `sullo/nikto` release; the build installs it offline with Perl runtime modules.

The source ZIP contains its upstream license files. The build fails on a checksum mismatch or missing required Nikto archive; Ghidra/JADX remain optional because of their size.
