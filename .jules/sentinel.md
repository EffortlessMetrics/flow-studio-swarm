
## 2026-06-11 - XXE Vulnerability in XML Parsing
**Vulnerability:** The test parser used the standard library `xml.etree.ElementTree` to parse JUnit XML files, creating an XML External Entity (XXE) vulnerability.
**Learning:** Standard Python XML libraries are insecure against maliciously constructed data. Untrusted inputs like external test reports can exploit this to read local files or cause denial of service.
**Prevention:** Strictly use `defusedxml` for parsing any XML data within the project to prevent entity expansion attacks.
