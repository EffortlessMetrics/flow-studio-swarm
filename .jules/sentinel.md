## 2026-05-08 - XML External Entity (XXE) Vulnerability Mitigation
**Vulnerability:** Found standard xml.etree.ElementTree parsing in swarm/runtime/test_parser.py, which is vulnerable to XXE attacks when parsing untrusted test reports.
**Learning:** The default XML parser in Python does not protect against external entity resolution, posing a critical security risk when handling external or dynamic XML input.
**Prevention:** Always use defusedxml.ElementTree as a secure drop-in replacement for any XML parsing tasks.
