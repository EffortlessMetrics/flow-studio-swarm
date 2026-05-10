## 2026-05-10 - XXE Vulnerability in XML Parsing
**Vulnerability:** Found standard `xml.etree.ElementTree` being used which is vulnerable to XML External Entity (XXE) attacks when parsing untrusted XML (like test results).
**Learning:** Raw XML parsing can lead to SSRF or file disclosure if test artifacts are maliciously crafted.
**Prevention:** Always use `defusedxml.ElementTree` as a drop-in secure replacement when parsing XML.
