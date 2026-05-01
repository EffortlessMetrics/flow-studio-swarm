
## 2025-02-27 - Mitigate XML External Entity (XXE) vulnerability
**Vulnerability:** The standard `xml.etree.ElementTree` parser was used for parsing JUnit XML test outputs, which is vulnerable to XXE attacks.
**Learning:** XML External Entity attacks can lead to arbitrary local file disclosure if the parsed XML is from an untrusted source. Python's default xml library is explicitly vulnerable to this.
**Prevention:** Always use the `defusedxml` library as a secure drop-in replacement when parsing XML data.
