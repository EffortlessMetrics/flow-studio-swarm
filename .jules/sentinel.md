
## 2026-06-08 - Use defusedxml for Secure XML Parsing
**Vulnerability:** The standard library `xml.etree.ElementTree` was used to parse external JUnit XML files, which is vulnerable to XXE (XML External Entity) and Billion Laughs attacks.
**Learning:** Python's standard XML libraries are not secure against maliciously constructed data.
**Prevention:** Always use `defusedxml.ElementTree` as a drop-in replacement when parsing untrusted or external XML files to prevent denial of service and data exposure.
