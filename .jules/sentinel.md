
## 2026-06-17 - Prevent XXE vulnerabilities in test output parser
**Vulnerability:** standard xml.etree.ElementTree allows XML external entities
**Learning:** JUnit XML loading shouldn't use standard libraries directly as attackers could supply malicious test outputs
**Prevention:** use defusedxml.ElementTree instead
