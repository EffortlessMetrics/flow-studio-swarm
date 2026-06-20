
## 2024-06-20 - Replace standard XML parser with defusedxml
**Vulnerability:** The standard library `xml.etree.ElementTree` was used for XML parsing, which is vulnerable to XML External Entity (XXE) and billion laughs attacks.
**Learning:** The built-in XML parser is insecure by default. It's critical to use secure alternatives when parsing potentially untrusted XML files.
**Prevention:** Always use `defusedxml` instead of the standard library `xml` module when parsing XML files in this repository.
