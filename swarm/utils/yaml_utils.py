# swarm/utils/yaml_utils.py
"""YAML loading utilities with optimized loader selection."""
from typing import IO, Any, Union

import yaml

try:
    from yaml import CSafeLoader as SafeLoader
except ImportError:
    from yaml import SafeLoader  # type: ignore[assignment]


def load_yaml(stream: Union[str, IO[str]]) -> Any:
    """Load YAML data using the fastest available safe loader.

    Prioritizes CSafeLoader (C-based LibYAML) over SafeLoader (Python-based).
    CSafeLoader is ~7x faster when LibYAML bindings are available.
    """
    return yaml.load(stream, Loader=SafeLoader)
