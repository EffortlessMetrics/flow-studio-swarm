## 2024-05-15 - Prevent XXE vulnerabilities during XML parsing
**Vulnerability:** XML External Entity (XXE) vulnerability in `test_parser.py` due to using the standard `xml.etree.ElementTree` library.
**Learning:** The built-in XML libraries in Python are vulnerable to XXE attacks. This codebase needs secure XML parsing.
**Prevention:** Always use `defusedxml.ElementTree` instead of `xml.etree.ElementTree` to prevent XXE vulnerabilities.
