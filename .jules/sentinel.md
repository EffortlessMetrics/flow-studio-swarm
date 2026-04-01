## 2025-02-12 - Prevent XXE and Entity Expansion in Test Parser
**Vulnerability:** XML External Entity (XXE) and XML bomb vulnerabilities.
**Learning:** The standard xml.etree.ElementTree is vulnerable to XXE and entity expansion by default.
**Prevention:** Always use defusedxml.ElementTree instead of xml.etree.ElementTree when parsing untrusted XML data.
