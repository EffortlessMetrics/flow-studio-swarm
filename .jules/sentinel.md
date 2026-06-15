
## 2025-02-28 - XXE Vulnerability Prevention
**Vulnerability:** Use of xml.etree.ElementTree which is vulnerable to XML External Entity (XXE) injection and billion laughs attacks.
**Learning:** Python's standard xml.etree.ElementTree does not protect against these attacks, making it unsafe for parsing untrusted XML data (like test output files).
**Prevention:** Always use defusedxml.ElementTree when parsing XML files to mitigate XXE and XML bomb vulnerabilities.
