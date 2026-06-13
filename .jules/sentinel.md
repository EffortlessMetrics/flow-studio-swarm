
## 2026-06-13 - Prevent XXE Vulnerabilities in XML Parsers
**Vulnerability:** XML External Entity (XXE) injection and Billion Laughs vulnerabilities when using the standard library `xml.etree.ElementTree` to parse untrusted XML documents.
**Learning:** The Python standard library `xml` modules are vulnerable by default to malicious entity expansion which can lead to denial of service, local file reading, or server-side request forgery (SSRF).
**Prevention:** Always use `defusedxml` packages like `defusedxml.ElementTree` which automatically defend against these malicious XML payloads instead of the standard library modules.
