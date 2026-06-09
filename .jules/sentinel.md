
## 2025-06-09 - Fix XXE Vulnerability in JUnit XML Parser
**Vulnerability:** XML External Entity (XXE) vulnerability via `xml.etree.ElementTree` parsing JUnit XML files.
**Learning:** Using the standard library `xml.etree.ElementTree` without disabling entity expansion is vulnerable to XXE. Defusedxml is the safest and recommended way.
**Prevention:** Always use `defusedxml.ElementTree` instead of `xml.etree.ElementTree` when parsing untrusted XML data.
