## 2024-05-28 - XXE Vulnerability in Test Parser
**Vulnerability:** XML External Entity (XXE) vulnerability via `xml.etree.ElementTree` in test reporting.
**Learning:** Python's standard `xml.etree.ElementTree` is vulnerable to XXE attacks. When parsing untrusted JUnit XML reports, malicious entities can lead to information disclosure or denial of service.
**Prevention:** Always use `defusedxml.ElementTree` as a secure drop-in replacement when parsing XML files, especially from potentially untrusted sources like test reports.
