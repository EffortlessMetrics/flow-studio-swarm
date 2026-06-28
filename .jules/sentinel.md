
## 2024-05-24 - Fix XML External Entity (XXE) Vulnerability
**Vulnerability:** The codebase was using the built-in `xml.etree.ElementTree` to parse external XML files. This is vulnerable to XML External Entity (XXE) attacks, which could allow arbitrary file reads or Server-Side Request Forgery (SSRF).
**Learning:** The built-in XML libraries in Python are generally not secure against maliciously constructed data. Always use `defusedxml` when parsing untrusted XML.
**Prevention:** Replace `xml.etree.ElementTree` with `defusedxml.ElementTree` for all XML parsing operations in the application.
