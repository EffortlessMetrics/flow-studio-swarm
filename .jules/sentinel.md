
## 2024-05-20 - Prevent XXE Vulnerabilities in test parsing
**Vulnerability:** The standard library `xml.etree.ElementTree` is used to parse external XML files. This is vulnerable to XML External Entity (XXE) attacks if the input is untrusted or maliciously crafted.
**Learning:** Even internal tools that parse XML test reports can be vulnerable if those reports are generated from untrusted sources or malicious test outputs.
**Prevention:** Use `defusedxml.ElementTree` instead of `xml.etree.ElementTree` for parsing XML files to mitigate XXE risks.
