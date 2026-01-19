# swarm/utils/yaml_utils.py
from typing import IO, Any, Union

import yaml

try:
    from yaml import CSafeLoader as SafeLoader
except ImportError:
    from yaml import SafeLoader  # type: ignore

def load_yaml(stream: Union[str, IO[str]]) -> Any:
    """
    Load YAML data using the fastest available safe loader.
    Prioritizes CSafeLoader (C-based) over SafeLoader (Python-based).
    """
    return yaml.load(stream, Loader=SafeLoader)
