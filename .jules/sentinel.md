## 2025-02-28 - XXE Vulnerability Mitigation in Test Parser
**Vulnerability:** The test parser (`swarm/runtime/test_parser.py`) used the standard library `xml.etree.ElementTree` to parse external XML files, which is vulnerable to XML External Entity (XXE) injection attacks.
**Learning:** Using standard `xml.etree.ElementTree` directly on untrusted or external XML input can expose the application to XXE. It's critical to use safe alternatives for XML parsing.
**Prevention:** Always use the `defusedxml` package (`defusedxml.ElementTree`) when parsing XML data from external sources, replacing standard library `xml.etree.ElementTree` imports.
