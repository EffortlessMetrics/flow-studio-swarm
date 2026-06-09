## 2026-06-09 - Fix XXE vulnerability in XML parsing
**Vulnerability:** The application used the standard library `xml.etree.ElementTree` to parse XML test reports, which is vulnerable to XML External Entity (XXE) and billion laughs attacks when processing malicious XML files.
**Learning:** Standard XML libraries in Python are not secure by default. Even for seemingly safe inputs like test reports, processing untrusted XML data using `xml.etree.ElementTree` poses a severe security risk.
**Prevention:** Always use `defusedxml.ElementTree` or similar safe alternatives when parsing XML files, especially when the source of the XML is external or potentially untrusted.
