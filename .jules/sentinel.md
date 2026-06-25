## 2026-06-25 - Prevent XML Vulnerabilities
**Vulnerability:** The application was using the standard library's `xml.etree.ElementTree` to parse XML files which is vulnerable to XML External Entity (XXE) and billion laughs attacks.
**Learning:** This exposes the application to DoS attacks and potential information disclosure through malicious payloads. Always use a defused library when parsing untrusted XML data.
**Prevention:** Use `defusedxml.ElementTree` instead of `xml.etree.ElementTree` to safely handle XML payloads across the codebase.
