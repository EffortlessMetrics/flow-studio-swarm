
## 2026-05-05 - Mitigate XXE Vulnerabilities in test_parser.py
**Vulnerability:** The application used standard `xml.etree.ElementTree` for parsing JUnit XML test outputs which is vulnerable to XML External Entity (XXE) processing.
**Learning:** Parsing untrusted XML data (like test output artifacts from agents or user-provided files) using the built-in XML libraries without safe defaults can lead to information disclosure or denial of service if external entities are expanded.
**Prevention:** Use the `defusedxml` package as a secure drop-in replacement for standard XML parsers. It explicitly prevents external entity expansion.
