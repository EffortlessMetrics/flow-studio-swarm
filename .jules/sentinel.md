## 2025-04-25 - XXE Vulnerability in XML Parsing
**Vulnerability:** The standard library `xml.etree.ElementTree` was used to parse external XML files (JUnit test results) in `swarm/runtime/test_parser.py`, which is vulnerable to XML External Entity (XXE) attacks.
**Learning:** Even internal testing/parsing tools can process externally-provided files (like downloaded CI artifacts), making them susceptible to XXE if standard library parsers are used instead of hardened ones.
**Prevention:** Always use `defusedxml.ElementTree` instead of `xml.etree.ElementTree` when parsing XML data in Python, especially when the source of the XML is untrusted or external.
