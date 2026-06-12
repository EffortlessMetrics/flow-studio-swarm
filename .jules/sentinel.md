
## 2026-06-12 - Prevent XML External Entity (XXE) and Billion Laughs vulnerabilities
**Vulnerability:** Used insecure standard library `xml.etree.ElementTree` for parsing JUnit XML test results.
**Learning:** The built-in XML parser is vulnerable to malicious XML payloads (XXE and billion laughs) which can cause DoS or unauthorized file reading when parsing external input.
**Prevention:** Strictly use `defusedxml.ElementTree` as a drop-in replacement when parsing XML files to prevent these vulnerabilities.
