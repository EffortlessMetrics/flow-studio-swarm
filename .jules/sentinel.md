## 2026-05-07 - Fix XML External Entity (XXE) injection
**Vulnerability:** Found `xml.etree.ElementTree` being used to parse potentially untrusted XML test results, which is vulnerable to XXE attacks.
**Learning:** Standard library XML parsers are vulnerable by default.
**Prevention:** Always use `defusedxml` as a drop-in replacement when parsing XML from unknown or untrusted sources.
