
## 2024-05-24 - Mitigate XXE in XML Parsing
**Vulnerability:** XML External Entity (XXE) vulnerabilities found in `swarm/runtime/test_parser.py` and `docs/ADOPTING_SELFTEST_CORE.md` due to the use of the standard library's `xml.etree.ElementTree` to parse untrusted XML data (JUnit test results).
**Learning:** The default Python `xml.etree.ElementTree` library is vulnerable to XXE attacks when parsing XML from untrusted sources. This application processes test reports which could be manipulated by an attacker to include external entities, potentially leading to information disclosure or denial of service.
**Prevention:** Always use the `defusedxml` package as a drop-in replacement when parsing XML data from untrusted sources or uploaded files to prevent XXE vulnerabilities.
