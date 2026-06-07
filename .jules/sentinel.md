
## 2025-05-15 - XXE Vulnerability in Test Parser
**Vulnerability:** XML External Entity (XXE) vulnerability due to using standard library `xml.etree.ElementTree` for parsing XML test results.
**Learning:** The built-in XML parser is vulnerable to billion laughs and entity expansion attacks. In contexts where we parse external files (like JUnit results from arbitrary test runs), this is a critical risk.
**Prevention:** Always use `defusedxml.ElementTree` instead of `xml.etree.ElementTree` when parsing untrusted XML data to prevent entity expansion attacks.
