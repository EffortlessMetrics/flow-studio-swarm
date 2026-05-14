## 2024-05-14 - Replace vulnerable XML parser
**Vulnerability:** Use of vulnerable standard library xml.etree.ElementTree in swarm/runtime/test_parser.py and docs/ADOPTING_SELFTEST_CORE.md
**Learning:** xml.etree.ElementTree does not protect against XML External Entity (XXE) and billion laughs vulnerabilities. Must use defusedxml.ElementTree instead.
**Prevention:** Use defusedxml.ElementTree for parsing XML.
