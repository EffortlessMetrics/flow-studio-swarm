## 2024-05-28 - XXE Vulnerability via xml.etree.ElementTree
**Vulnerability:** Use of standard library `xml.etree.ElementTree` to parse potentially untrusted XML files (JUnit XML reports) in `swarm/runtime/test_parser.py`, which is vulnerable to XML External Entity (XXE) and billion laughs attacks.
**Learning:** Python's standard `xml.etree.ElementTree` is inherently vulnerable to XXE. Any code parsing external XML MUST use `defusedxml.ElementTree` to prevent data exfiltration, denial of service, or server-side request forgery.
**Prevention:** Always use `defusedxml` instead of the standard library `xml` module for parsing XML in this repository, as explicitly stated in the memory rules.
