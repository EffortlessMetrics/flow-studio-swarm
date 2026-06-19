
## 2025-03-01 - Fix XXE vulnerability in test_parser.py
**Vulnerability:** Use of insecure xml.etree.ElementTree to parse JUnit XML files in swarm/runtime/test_parser.py
**Learning:** Standard library XML parsing in Python is vulnerable to XML External Entity (XXE) and billion laughs attacks, requiring defusedxml.
**Prevention:** Always use defusedxml instead of standard library xml.etree for untrusted XML parsing.
