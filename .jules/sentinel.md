
## 2026-05-05 - Mitigated XXE vulnerability in XML parser
**Vulnerability:** Standard `xml.etree.ElementTree` parsing is vulnerable to XML External Entity (XXE) attacks if handling un-trusted or potentially malicious XML documents.
**Learning:** `test_parser.py` was utilizing the built-in XML module for parsing test outputs. Since test outputs can theoretically be manipulated by bad actors to exfiltrate files or trigger DoS via entity expansion, relying on `defusedxml` is necessary.
**Prevention:** Always default to `defusedxml` over standard XML parsing modules when dealing with external XML to ensure safety against entity expansion and external entity inclusion.
