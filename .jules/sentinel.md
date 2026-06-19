
## 2026-06-19 - Prevent XXE Vulnerabilities
**Vulnerability:** Found use of standard xml.etree.ElementTree in test_parser.py which is vulnerable to XXE and billion laughs attacks when parsing untrusted JUnit XML.
**Learning:** Test parsers often process externally generated files, requiring the same security scrutiny as user input.
**Prevention:** Always use defusedxml.ElementTree instead of xml.etree.ElementTree when parsing XML files.
