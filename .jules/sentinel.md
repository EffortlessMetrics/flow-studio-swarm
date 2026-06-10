
## 2026-06-10 - Prevent XML External Entity (XXE) Vulnerabilities
**Vulnerability:** The standard library xml.etree.ElementTree was used to parse test output XML files, making the application susceptible to XXE and billion laughs attacks if malicious XML is parsed.
**Learning:** Standard library XML parsers in Python are not secure against maliciously constructed data by default.
**Prevention:** Always strictly use defusedxml.ElementTree or similar safe parsers instead of the standard library when processing untrusted XML data.
