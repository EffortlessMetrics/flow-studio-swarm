## 2026-05-07 - Mitigating XXE in Test Parsers
**Vulnerability:** XML External Entity (XXE) vulnerability via standard `xml.etree.ElementTree` usage in `swarm/runtime/test_parser.py`.
**Learning:** Parsing untrusted XML test reports (like JUnit XML) using the standard library's XML parser can lead to arbitrary file reads or SSRF. The defusedxml package provides secure drop-in replacements.
**Prevention:** Always use `defusedxml` when parsing XML from external sources or test artifacts.
