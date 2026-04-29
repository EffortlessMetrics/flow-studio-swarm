## 2025-02-28 - Mitigate XXE Vulnerabilities in Test Parsing
**Vulnerability:** Standard `xml.etree.ElementTree` parsing used without defense against XML External Entities (XXE).
**Learning:** External or untrusted XML documents (like user-uploaded or externally sourced test results) can contain entities that lead to server-side request forgery (SSRF), local file disclosure, or denial of service when parsed by insecure default parsers.
**Prevention:** Always use secure alternatives like `defusedxml` when parsing XML from potentially untrusted sources. Ensure this package is included in dependencies and use it as a drop-in replacement.
