## 2024-05-24 - XML External Entity (XXE) Vulnerability
**Vulnerability:** The test_parser.py file used standard xml.etree.ElementTree to parse XML data which is vulnerable to XXE injection.
**Learning:** Standard library XML parsers are not secure by default.
**Prevention:** Always use defusedxml.ElementTree as a secure drop-in replacement when parsing untrusted XML data.
