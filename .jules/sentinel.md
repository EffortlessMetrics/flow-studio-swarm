## 2026-05-07 - 🛡️ Sentinel: [CRITICAL] Fix XML External Entity (XXE) vulnerability
**Vulnerability:** Use of insecure standard library xml.etree.ElementTree parsing in swarm/runtime/test_parser.py.
**Learning:** xml.etree.ElementTree is vulnerable to XML External Entity (XXE) attacks when parsing untrusted inputs.
**Prevention:** Always use the secure defusedxml package as a drop-in replacement for XML parsing.
