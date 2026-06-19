import pytest
from pathlib import Path
from swarm.runtime.test_parser import parse_junit_xml

def test_xml_external_entity_protection(tmp_path: Path):
    """Verify that the XML parser is protected against XXE attacks."""

    # Create a malicious XML file with an external entity
    xxe_xml = tmp_path / "xxe_test.xml"
    xxe_xml.write_text("""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE test [
  <!ENTITY xxe SYSTEM "file:///etc/passwd">
]>
<testsuites>
  <testsuite name="&xxe;" tests="1" failures="0" errors="0" skipped="0" time="0.1">
    <testcase name="test_example" classname="example.Test" time="0.05" />
  </testsuite>
</testsuites>
""")

    try:
        parse_junit_xml(xxe_xml)
        pytest.fail("Exception not raised")
    except Exception as e:
        if str(e) == "Exception not raised":
            raise
        assert "Entities" in str(type(e).__name__) or "DTD" in str(type(e).__name__)

def test_billion_laughs_protection(tmp_path: Path):
    """Verify that the XML parser is protected against billion laughs attacks."""

    # Create a malicious XML file with nested entities
    bl_xml = tmp_path / "billion_laughs.xml"
    bl_xml.write_text("""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE lolz [
  <!ENTITY lol "lol">
  <!ENTITY lol1 "&lol;&lol;&lol;&lol;&lol;&lol;&lol;&lol;&lol;&lol;">
  <!ENTITY lol2 "&lol1;&lol1;&lol1;&lol1;&lol1;&lol1;&lol1;&lol1;&lol1;&lol1;">
  <!ENTITY lol3 "&lol2;&lol2;&lol2;&lol2;&lol2;&lol2;&lol2;&lol2;&lol2;&lol2;">
  <!ENTITY lol4 "&lol3;&lol3;&lol3;&lol3;&lol3;&lol3;&lol3;&lol3;&lol3;&lol3;">
  <!ENTITY lol5 "&lol4;&lol4;&lol4;&lol4;&lol4;&lol4;&lol4;&lol4;&lol4;&lol4;">
  <!ENTITY lol6 "&lol5;&lol5;&lol5;&lol5;&lol5;&lol5;&lol5;&lol5;&lol5;&lol5;">
  <!ENTITY lol7 "&lol6;&lol6;&lol6;&lol6;&lol6;&lol6;&lol6;&lol6;&lol6;&lol6;">
  <!ENTITY lol8 "&lol7;&lol7;&lol7;&lol7;&lol7;&lol7;&lol7;&lol7;&lol7;&lol7;">
  <!ENTITY lol9 "&lol8;&lol8;&lol8;&lol8;&lol8;&lol8;&lol8;&lol8;&lol8;&lol8;">
]>
<testsuites>
  <testsuite name="&lol9;" tests="1" failures="0" errors="0" skipped="0" time="0.1">
    <testcase name="test_example" classname="example.Test" time="0.05" />
  </testsuite>
</testsuites>
""")

    try:
        parse_junit_xml(bl_xml)
        pytest.fail("Exception not raised")
    except Exception as e:
        if str(e) == "Exception not raised":
            raise
        assert "Entities" in str(type(e).__name__) or "DTD" in str(type(e).__name__)
