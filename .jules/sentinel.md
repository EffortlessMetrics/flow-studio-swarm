
## 2024-06-21 - Fix XXE vulnerability in XML parser
**Vulnerability:** Used standard xml.etree.ElementTree to parse XML files which is vulnerable to XXE (XML External Entity) attacks and billion laughs.
**Learning:** Python standard library XML parsers are vulnerable by default and should not be used on untrusted input like JUnit XML files. The memory also specifically mentioned to always use `defusedxml.ElementTree` instead of the standard library.
**Prevention:** Always use `defusedxml` package when parsing XML data, especially for files that might come from external sources.
