## 2026-04-22 - Prevent XXE Vulnerability
**Vulnerability:** Using standard `xml.etree.ElementTree` to parse XML test reports can expose the application to XML External Entity (XXE) injection vulnerabilities if the XML files are untrusted.
**Learning:** `defusedxml.ElementTree` should be used instead of `xml.etree.ElementTree` when parsing XML to prevent XXE attacks.
**Prevention:** Always use `defusedxml` when parsing XML files, avoiding standard library XML parsing functions.
