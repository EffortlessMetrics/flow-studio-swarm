"""Tests for swarm/utils/yaml_utils.py."""

from io import StringIO
from unittest.mock import patch

import pytest
import yaml

from swarm.utils.yaml_utils import SafeLoader, load_yaml


class TestLoadYaml:
    """Tests for load_yaml function."""

    def test_load_yaml_from_string(self):
        """Test loading YAML from a string."""
        data = "key: value\nlist:\n  - item1\n  - item2"
        result = load_yaml(data)
        assert result == {"key": "value", "list": ["item1", "item2"]}

    def test_load_yaml_from_stream(self):
        """Test loading YAML from a file-like stream."""
        stream = StringIO("name: test\ncount: 42")
        result = load_yaml(stream)
        assert result == {"name": "test", "count": 42}

    def test_load_yaml_empty_document(self):
        """Test loading empty YAML document returns None."""
        result = load_yaml("")
        assert result is None

    def test_load_yaml_preserves_types(self):
        """Test that YAML types are preserved."""
        data = """
string: hello
integer: 42
float: 3.14
boolean: true
null_value: null
list: [1, 2, 3]
dict:
  nested: value
"""
        result = load_yaml(data)
        assert result["string"] == "hello"
        assert result["integer"] == 42
        assert result["float"] == 3.14
        assert result["boolean"] is True
        assert result["null_value"] is None
        assert result["list"] == [1, 2, 3]
        assert result["dict"] == {"nested": "value"}


class TestSafeLoaderSelection:
    """Tests for SafeLoader selection behavior."""

    def test_safeloader_is_csafeloader_when_available(self):
        """Test that CSafeLoader is preferred when available."""
        try:
            from yaml import CSafeLoader

            # CSafeLoader should be used when available
            assert SafeLoader is CSafeLoader
        except ImportError:
            # If CSafeLoader isn't available, regular SafeLoader is used
            from yaml import SafeLoader as YamlSafeLoader

            assert SafeLoader is YamlSafeLoader

    def test_load_yaml_uses_safe_loader(self):
        """Test that load_yaml uses the SafeLoader (safe loading)."""
        # This tests that we're using safe loading by checking that
        # dangerous YAML tags are not processed
        dangerous_yaml = "!!python/object/apply:os.system ['echo pwned']"

        # Safe loader should raise an error on dangerous tags
        with pytest.raises(yaml.constructor.ConstructorError):
            load_yaml(dangerous_yaml)


class TestYamlUtilsEdgeCases:
    """Edge case tests for yaml_utils."""

    def test_load_yaml_with_unicode(self):
        """Test loading YAML with unicode content."""
        data = "message: Hello 世界 🌍"
        result = load_yaml(data)
        assert result == {"message": "Hello 世界 🌍"}

    def test_load_yaml_multiline_string(self):
        """Test loading YAML with multiline strings."""
        data = """
text: |
  Line 1
  Line 2
  Line 3
"""
        result = load_yaml(data)
        assert result["text"] == "Line 1\nLine 2\nLine 3\n"

    def test_load_yaml_complex_nested_structure(self):
        """Test loading complex nested YAML structure."""
        data = """
flows:
  signal:
    steps:
      - id: normalize
        agent: signal-normalizer
      - id: frame
        agent: problem-framer
  plan:
    steps:
      - id: analyze
        agent: impact-analyzer
"""
        result = load_yaml(data)
        assert len(result["flows"]) == 2
        assert len(result["flows"]["signal"]["steps"]) == 2
        assert result["flows"]["signal"]["steps"][0]["agent"] == "signal-normalizer"
