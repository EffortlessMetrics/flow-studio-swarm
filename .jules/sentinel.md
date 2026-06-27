
## 2026-06-27 - Prevent XXE vulnerabilities
**Vulnerability:** Used unsafe standard library xml.etree.ElementTree to parse JUnit XML files.
**Learning:** The Python standard XML library is vulnerable to XML External Entity (XXE) injection and Billion Laughs attacks.
**Prevention:** Always use defusedxml.ElementTree instead of the standard library xml.etree.ElementTree when parsing XML files in this repository.
