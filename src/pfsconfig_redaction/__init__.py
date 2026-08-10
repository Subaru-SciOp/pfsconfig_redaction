__all__ = ["__version__", "redact"]

from importlib.metadata import PackageNotFoundError, version

from .utils import redact

try:
    __version__ = version("pfsconfig_redaction")
except PackageNotFoundError:  # pragma: no cover
    # Imported straight from a source tree without being installed, so there is no
    # distribution metadata to read the setuptools_scm version back from.
    __version__ = "0.0.0+unknown"
