## 2025-01-23 - Prevent XXE Vulnerabilities in XML Parsing
**Vulnerability:** The test parser was using the standard library `xml.etree.ElementTree` to parse JUnit XML files, which is vulnerable to XML External Entity (XXE) attacks.
**Learning:** When parsing test reports or any XML data from external sources, using the standard Python XML library can expose the system to arbitrary file reads or DoS via malicious entities.
**Prevention:** Always use `defusedxml.ElementTree` instead of `xml.etree.ElementTree` for parsing XML data. The standard library should only be used if it is strictly generating XML.
