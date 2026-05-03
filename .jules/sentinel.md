
## 2025-05-03 - Mitigate XML External Entity (XXE) Vulnerability
**Vulnerability:** Use of `xml.etree.ElementTree` which is vulnerable to XXE attacks.
**Learning:** The built-in XML parsing library `xml.etree.ElementTree` does not adequately protect against malicious XML input containing external entities.
**Prevention:** Always use `defusedxml.ElementTree` as a secure drop-in replacement when parsing XML from untrusted sources.
