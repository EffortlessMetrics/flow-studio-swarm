
## 2026-06-12 - Fix XXE Vulnerability in XML Parsing
**Vulnerability:** Found `xml.etree.ElementTree` being used to parse XML test outputs, which is vulnerable to XML External Entity (XXE) injection.
**Learning:** Python's standard library `xml.etree.ElementTree` is vulnerable to XXE by default. Using it to parse un-trusted XML can lead to local file disclosure or denial of service (billion laughs).
**Prevention:** Always use `defusedxml` package (e.g., `import defusedxml.ElementTree as ET`) when parsing XML data.
