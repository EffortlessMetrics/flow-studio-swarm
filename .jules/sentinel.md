
## 2026-06-15 - Prevent XML External Entity (XXE) Vulnerability
**Vulnerability:** Found standard `xml.etree.ElementTree` usage which is vulnerable to XXE and billion laughs attacks when parsing untrusted XML.
**Learning:** Python's built-in XML parsers are not secure against maliciously constructed data. Untrusted inputs must be parsed with `defusedxml`.
**Prevention:** Use `defusedxml.ElementTree` as a drop-in replacement whenever parsing XML files.
