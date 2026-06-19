## 2025-02-14 - Replace standard xml.etree with defusedxml to prevent XXE vulnerabilities
**Vulnerability:** Found `xml.etree.ElementTree` being used to parse potentially untrusted XML (like JUnit test reports from arbitrary frameworks/users) which is vulnerable to XML External Entity (XXE) and billion laughs attacks.
**Learning:** Python's standard library `xml` module is not secure against maliciously constructed data. It allows expanding external entities and entity bombs which can lead to information disclosure or DoS.
**Prevention:** Always use `defusedxml` packages (like `defusedxml.ElementTree`) when parsing XML data that comes from untrusted sources or across a trust boundary.
