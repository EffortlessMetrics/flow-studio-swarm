## 2026-05-13 - Mitigated XXE vulnerability in test parser
**Vulnerability:** The `swarm/runtime/test_parser.py` file used `xml.etree.ElementTree` to parse JUnit XML files, which is vulnerable to XML External Entity (XXE) and Billion Laughs attacks.
**Learning:** Standard library XML parsing in Python is generally vulnerable to XXE. Even if test reports are generated locally, they might originate from third-party tools or external systems where malicious XML could be injected.
**Prevention:** Always use `defusedxml` as a drop-in replacement for standard library XML parsers when processing unverified XML input.
