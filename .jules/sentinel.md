## 2025-02-28 - [XXE Vulnerability in Test Parser]
**Vulnerability:** XML External Entity (XXE) vulnerability via standard library `xml.etree.ElementTree` parsing untrusted XML (e.g. JUnit test output).
**Learning:** The built-in XML parser is vulnerable to XXE attacks. The code used it to parse potentially untrusted `.xml` test results without mitigating the risk.
**Prevention:** Always use `defusedxml.ElementTree` when parsing XML data from external sources instead of the standard library's `xml.etree.ElementTree`.
