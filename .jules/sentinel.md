## 2024-05-24 - Prevent XXE Vulnerability
**Vulnerability:** XML External Entity (XXE) injection risk due to using standard library `xml.etree.ElementTree`.
**Learning:** Standard XML libraries are vulnerable to XXE by default. In an environment where we parse files from various sources, this could be exploited to read local files or SSRF.
**Prevention:** Always use `defusedxml` or disable external entity resolution when parsing XML.