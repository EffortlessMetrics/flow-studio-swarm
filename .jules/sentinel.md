## 2026-05-06 - Mitigate XML External Entity (XXE) vulnerability
**Vulnerability:** Found standard `xml.etree.ElementTree` parsing without safeguards.
**Learning:** Standard XML parsing can be vulnerable to XXE attacks.
**Prevention:** Use `defusedxml` as a secure drop-in replacement to mitigate XXE vulnerabilities.
