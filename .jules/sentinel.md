
## 2026-06-08 - XXE Vulnerability in JUnit XML Parser
**Vulnerability:** Found `xml.etree.ElementTree` being used to parse potentially untrusted JUnit XML files in `swarm/runtime/test_parser.py` and in documentation examples `docs/ADOPTING_SELFTEST_CORE.md`.
**Learning:** Standard library XML parsers in Python are vulnerable to XML External Entity (XXE) and billion laughs attacks. Even internal testing files shouldn't be parsed with vulnerable libraries to prevent lateral movement or exploitation if test files are modified.
**Prevention:** Always use `defusedxml` package instead of standard library `xml` modules for parsing any XML data.
