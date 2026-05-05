
## 2026-05-05 - Fix XML External Entity (XXE) vulnerability
**Vulnerability:** XML External Entity (XXE) injection via standard `xml.etree.ElementTree`.
**Learning:** `xml.etree.ElementTree` is vulnerable to XXE attacks.
**Prevention:** Always use `defusedxml.ElementTree` when parsing XML.
