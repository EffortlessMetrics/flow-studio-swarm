
## 2024-05-24 - XML External Entity (XXE) Vulnerability
**Vulnerability:** XML External Entity (XXE) and billion laughs vulnerabilities due to the use of standard library xml.etree.ElementTree when parsing XML files.
**Learning:** The built-in xml.etree.ElementTree library is vulnerable to XXE attacks.
**Prevention:** Always use defusedxml.ElementTree instead of the standard library xml.etree.ElementTree.
