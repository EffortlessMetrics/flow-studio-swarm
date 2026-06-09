
## 2024-06-09 - XXE Vulnerability
**Vulnerability:** XML External Entity (XXE) vulnerability in test_parser.py caused by using the standard library xml.etree.ElementTree.
**Learning:** Parsing XML test outputs (e.g. from JUnit) with the standard library can allow attackers to read arbitrary files or cause denial of service if the XML file is maliciously crafted.
**Prevention:** Always use defusedxml.ElementTree instead of xml.etree.ElementTree when parsing XML files to prevent XXE and billion laughs vulnerabilities.
