## 2025-02-14 - Replace standard XML parser with defusedxml to prevent XXE
**Vulnerability:** The standard `xml.etree.ElementTree` parser in `swarm/runtime/test_parser.py` is vulnerable to XML External Entity (XXE) attacks when parsing untrusted JUnit XML files.
**Learning:** Python's standard XML parsers are not secure against maliciously constructed data.
**Prevention:** Always use the `defusedxml` package as a secure drop-in replacement for standard XML parsers when handling external or untrusted XML data.
