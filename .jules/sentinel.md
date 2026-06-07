
## 2026-06-07 - Mitigate XXE Vulnerability in Test Parser
**Vulnerability:** XML External Entity (XXE) vulnerability due to usage of `xml.etree.ElementTree`.
**Learning:** `xml.etree.ElementTree` in Python's standard library is vulnerable to XXE attacks when parsing untrusted XML data (like external JUnit reports).
**Prevention:** Always use `defusedxml.ElementTree` instead of `xml.etree.ElementTree` for parsing XML files to prevent XXE and billion laughs vulnerabilities.
