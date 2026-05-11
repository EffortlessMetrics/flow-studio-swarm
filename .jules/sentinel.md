
## 2026-05-11 - Mitigated XXE via defusedxml
**Vulnerability:** Found xml.etree.ElementTree being used to parse JUnit XML, which is susceptible to XML External Entity (XXE) attacks.
**Learning:** Standard library XML parsing does not prevent XXE. Parsing untrusted XML (like test outputs from arbitrary runs) exposes the system.
**Prevention:** Always add and use defusedxml.ElementTree instead of xml.etree.ElementTree as a drop-in replacement. Include # SECURITY: comments to prevent regressions.
