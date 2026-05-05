## 2026-05-05 - Fix XXE in JUnit Parser
**Vulnerability:** Found `xml.etree.ElementTree` being used to parse JUnit XML files without entity resolution disabled in `swarm/runtime/test_parser.py`. This exposes the application to XML External Entity (XXE) vulnerabilities.
**Learning:** Python's default `xml.etree.ElementTree` is vulnerable to XXE. Any code parsing external XML files must use secure parsers.
**Prevention:** Always use `defusedxml` instead of `xml.etree` or `lxml` for parsing arbitrary XML input to prevent entity expansion attacks.
