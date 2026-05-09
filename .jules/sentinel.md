## 2026-05-09 - XML External Entity (XXE) Vulnerability
**Vulnerability:** The test_parser.py used the standard xml.etree.ElementTree library to parse XML output, which is vulnerable to XXE injection.
**Learning:** Standard library XML parsers in Python are vulnerable to XXE by default. Using them to parse potentially untrusted test output files introduces a security risk.
**Prevention:** Always use the defusedxml library as a drop-in replacement when parsing XML from external sources or files.
