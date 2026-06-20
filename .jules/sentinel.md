
## 2024-05-18 - Prevent XXE Vulnerabilities
**Vulnerability:** Use of insecure xml.etree.ElementTree for parsing XML.
**Learning:** The standard library's ElementTree is vulnerable to XML External Entity (XXE) and billion laughs attacks when parsing untrusted XML.
**Prevention:** Always use defusedxml.ElementTree instead of the standard library when parsing XML files.
