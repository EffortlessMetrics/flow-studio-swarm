## 2025-05-24 - Mitigation of XML External Entity (XXE) Vulnerability
**Vulnerability:** XML External Entity (XXE) risk from using standard `xml.etree.ElementTree`.
**Learning:** Python's standard `xml.etree.ElementTree` modules are vulnerable to malicious XML payloads containing external entities, which can lead to information disclosure or denial-of-service.
**Prevention:** Always use `defusedxml` package as a drop-in replacement for standard library XML parsers when parsing untrusted XML data.
