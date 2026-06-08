## 2025-02-20 - Prevent XML External Entity (XXE) Vulnerabilities in XML Parsing
**Vulnerability:** The project previously used `xml.etree.ElementTree` to parse JUnit XML test output, which is vulnerable to XML External Entity (XXE) and billion laughs attacks when parsing untrusted XML data.
**Learning:** Python's standard library `xml` module is not secure against maliciously constructed XML data. We must always use a secure alternative when parsing XML from external sources.
**Prevention:** Strictly use `defusedxml.ElementTree` instead of `xml.etree.ElementTree` for all XML parsing within the project to prevent XXE and related XML vulnerabilities.
