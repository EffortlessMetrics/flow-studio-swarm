
## 2024-05-24 - Fix XXE in JUnit XML parsing
**Vulnerability:** Found `xml.etree.ElementTree` being used to parse potentially untrusted JUnit XML output in test runners.
**Learning:** Standard XML parsing in Python is vulnerable to XML External Entity (XXE) attacks, which can lead to local file disclosure or Denial of Service (Billion Laughs attack). Test output from third-party frameworks can be a vector.
**Prevention:** Always use `defusedxml` as a drop-in replacement for standard library XML parsing when handling any XML that could be influenced by external output or user input.
