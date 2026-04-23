## 2025-02-27 - [XXE Vulnerability in Test Parser]
**Vulnerability:** Found `xml.etree.ElementTree` being used to parse JUnit XML files, which is vulnerable to XML External Entity (XXE) attacks.
**Learning:** The built-in Python `xml.etree` module does not have protections against XXE injection, making it dangerous when parsing untrusted XML data (like test output artifacts).
**Prevention:** Always use `defusedxml.ElementTree` instead of `xml.etree.ElementTree` when parsing XML data in Python to prevent XXE.
