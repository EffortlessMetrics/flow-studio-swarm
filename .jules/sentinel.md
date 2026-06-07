## 2025-02-28 - XXE Vulnerability in Test Parser
**Vulnerability:** XML External Entity (XXE) vulnerability via `xml.etree.ElementTree` in test parsing.
**Learning:** Parsing untrusted test output XMLs can lead to XXE and billion laughs attacks.
**Prevention:** Strictly use `defusedxml.ElementTree` instead of the standard library's `xml.etree.ElementTree`.
