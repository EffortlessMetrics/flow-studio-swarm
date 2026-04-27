## 2025-03-09 - XXE Vulnerability Mitigation
**Vulnerability:** Found standard xml.etree.ElementTree being used to parse potentially untrusted XML (like JUnit output), leading to XML External Entity (XXE) injection vulnerabilities.
**Learning:** In Python, standard library XML parsers are vulnerable to XXE by default. Using them on external test artifacts exposes the runtime to SSRF or local file disclosure.
**Prevention:** Always add the defusedxml package and use it as a secure drop-in replacement (e.g., import defusedxml.ElementTree as ET).
