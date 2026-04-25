## 2026-04-25 - XXE Vulnerability in Test Parser
**Vulnerability:** XML External Entity (XXE) vulnerability in `swarm/runtime/test_parser.py` due to parsing untrusted XML data with `xml.etree.ElementTree`.
**Learning:** Using the standard library `xml.etree.ElementTree` is insecure for parsing untrusted XML because it is vulnerable to XXE attacks. The `defusedxml` package provides safe alternative parsers.
**Prevention:** Always use `defusedxml.ElementTree` instead of `xml.etree.ElementTree` when parsing XML data to prevent XXE vulnerabilities.
