## 2024-05-18 - XXE Vulnerability in XML Parsing
**Vulnerability:** The application was using the standard `xml.etree.ElementTree` module to parse XML, which is vulnerable to XML External Entity (XXE) attacks.
**Learning:** The built-in XML parser in Python does not protect against external entity expansion by default. The standard library explicitly warns about this.
**Prevention:** Always use `defusedxml` as a drop-in replacement for standard XML parsers when dealing with potentially untrusted XML input.
