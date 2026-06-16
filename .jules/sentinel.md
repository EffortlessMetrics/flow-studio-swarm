
## 2026-06-16 - Prevent XML External Entity (XXE) Vulnerability
**Vulnerability:** Found standard library 'xml.etree.ElementTree' being used to parse XML test outputs, which is vulnerable to XXE and billion laughs attacks.
**Learning:** The built-in XML parser allows resolving external entities by default. Malicious XML could allow arbitrary local file reads or DOS.
**Prevention:** Always use the 'defusedxml' package for parsing untrusted XML, which disables unsafe entity resolution by default.
