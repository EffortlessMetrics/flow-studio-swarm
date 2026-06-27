
## 2025-02-27 - XML Parsing Vulnerability (XXE)
**Vulnerability:** Use of `xml.etree.ElementTree` which is vulnerable to XML External Entity (XXE) and billion laughs attacks.
**Learning:** The Python standard library `xml` module is not secure against maliciously constructed data. The `test_parser` accepts external files (e.g. from JUnit XML outputs) that could be exploited.
**Prevention:** Always use `defusedxml` packages instead of the standard XML libraries when parsing any externally sourced XML data.
