## 2025-02-24 - Replace standard xml.etree with defusedxml to prevent XXE
**Vulnerability:** Use of the standard `xml.etree.ElementTree` library for parsing untrusted JUnit XML files poses a risk of XML External Entity (XXE) injection vulnerabilities.
**Learning:** The default XML parser in Python (`xml.etree`) is vulnerable to XXE attacks. When parsing test result artifacts from external sources, this could be exploited.
**Prevention:** Always use `defusedxml` as a drop-in replacement when parsing XML files, especially from potentially untrusted sources or uploaded artifacts.
