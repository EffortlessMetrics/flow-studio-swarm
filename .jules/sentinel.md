
## 2025-02-28 - XXE in XML Parsing
**Vulnerability:** Using the standard `xml.etree.ElementTree` parser for potentially untrusted XML inputs without protection against XXE attacks.
**Learning:** Standard library XML parsers in Python are vulnerable to XXE by default. Relying on them directly in forensic test parsers introduces significant risk when parsing untrusted test traces.
**Prevention:** Always use the `defusedxml` package as a secure drop-in replacement when parsing XML data.
