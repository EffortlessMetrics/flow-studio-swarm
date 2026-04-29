
## 2025-02-18 - Fix XXE Vulnerability in JUnit XML Parsing
**Vulnerability:** XML External Entity (XXE) vulnerability via `xml.etree.ElementTree` parsing untrusted JUnit XML test reports.
**Learning:** Standard library `xml.etree` is unsafe for untrusted input.
**Prevention:** Always use `defusedxml` packages (like `defusedxml.ElementTree`) for parsing XML files to prevent malicious external entity resolution.
