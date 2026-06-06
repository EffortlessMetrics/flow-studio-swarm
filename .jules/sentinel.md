
## 2025-02-28 - XXE Vulnerability in JUnit XML Parsing
**Vulnerability:** XML External Entity (XXE) vulnerability via `xml.etree.ElementTree` in `swarm/runtime/test_parser.py`.
**Learning:** The built-in XML library is vulnerable to XXE by default. It was used to parse external JUnit XML files.
**Prevention:** Always use `defusedxml.ElementTree` when parsing XML from potentially untrusted sources.
