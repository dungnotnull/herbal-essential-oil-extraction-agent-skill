"""herbal_oil - production-grade skill-registry framework for Essential Oil
Extraction & Aromatic Chemistry analysis.

Public entry points:
    from herbal_oil.core import SkillRegistry, PipelineRunner
    from herbal_oil.config import Settings
"""
from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("herbal-oil-skill")
except PackageNotFoundError:  # pragma: no cover - editable installs
    __version__ = "2.0.0"

__all__ = ["__version__"]
