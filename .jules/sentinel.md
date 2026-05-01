
## 2024-05-24 - Fix XXE Vulnerability in XML parsing
**Vulnerability:** XML External Entity (XXE) vulnerability in `xml.etree.ElementTree`.
**Learning:** Standard XML parsing libraries in Python are vulnerable to XXE by default.
**Prevention:** Always use `defusedxml` as a drop-in replacement for parsing untrusted XML data to prevent XXE.
