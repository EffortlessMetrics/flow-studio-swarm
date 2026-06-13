
## 2024-05-18 - XXE Vulnerability Prevention
**Vulnerability:** Use of insecure standard library xml.etree.ElementTree parsing untrusted XML.
**Learning:** The xml.etree.ElementTree module is vulnerable to XML External Entity (XXE) and billion laughs attacks when parsing unauthenticated XML files (like JUnit output or trace XMLs). This existed because the standard library defaults are not secure against malicious payloads.
**Prevention:** Always use defusedxml.ElementTree instead of xml.etree.ElementTree to parse XML data securely.
