

## 2024-05-01 - Prevent XXE Vulnerabilities in XML Parsing
**Vulnerability:** XML External Entity (XXE) injection vulnerability found due to standard `xml.etree.ElementTree` usage.
**Learning:** The standard library XML parser is inherently vulnerable to XXE attacks and malicious payload execution if parsing untrusted data.
**Prevention:** Always use `defusedxml` instead of the standard library for XML parsing across the codebase.
