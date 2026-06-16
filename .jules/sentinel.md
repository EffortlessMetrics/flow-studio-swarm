
## 2026-06-16 - Prevent XML External Entity (XXE) Vulnerability
**Vulnerability:** XML External Entity (XXE) vulnerability parsing standard python library `xml.etree.ElementTree`.
**Learning:** The default XML parser is vulnerable to entity expansion and XXE attacks; it should be replaced with a secure alternative like `defusedxml`.
**Prevention:** Always rely on secure parsers (e.g., `defusedxml.ElementTree`) when evaluating unverified or external XML files to prevent system exposure or memory exhaustion attacks.
