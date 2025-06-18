#!/usr/bin/env python3

import pytest


class TestImports:
    """Test that all package imports work correctly."""
    
    def test_import_main_package(self):
        """Test importing the main package."""
        import pfsconfig_redaction
        assert hasattr(pfsconfig_redaction, 'redact')
    
    def test_import_utils_module(self):
        """Test importing the utils module directly."""
        from pfsconfig_redaction import utils
        assert hasattr(utils, 'redact')
        assert hasattr(utils, 'RedactedPfsConfigDataClass')
    
    def test_import_redact_function(self):
        """Test importing the redact function directly."""
        from pfsconfig_redaction.utils import redact
        assert callable(redact)
    
    def test_import_dataclass(self):
        """Test importing the RedactedPfsConfigDataClass."""
        from pfsconfig_redaction.utils import RedactedPfsConfigDataClass
        assert RedactedPfsConfigDataClass is not None
    
    def test_all_exports(self):
        """Test that __all__ exports work correctly."""
        import pfsconfig_redaction
        
        # Check that __all__ is defined
        assert hasattr(pfsconfig_redaction, '__all__')
        assert 'redact' in pfsconfig_redaction.__all__
        
        # Check that exported functions are accessible
        assert hasattr(pfsconfig_redaction, 'redact')
    
    def test_dependencies_available(self):
        """Test that all required dependencies are available."""
        try:
            import numpy as np
            assert np is not None
        except ImportError:
            pytest.fail("numpy is not available")
        
        try:
            from pfs.datamodel import PfsConfig, TargetType
            assert PfsConfig is not None
            assert TargetType is not None
        except ImportError:
            pytest.fail("pfs.datamodel is not available")
    
    def test_optional_dependencies(self):
        """Test optional dependencies used in tests."""
        try:
            from pathlib import Path
            assert Path is not None
        except ImportError:
            pytest.fail("pathlib is not available")
        
        try:
            from unittest.mock import Mock
            assert Mock is not None
        except ImportError:
            pytest.fail("unittest.mock is not available")
    
    def test_logging_setup(self):
        """Test that logging is properly configured."""
        from pfsconfig_redaction.utils import logger
        assert logger is not None
        assert logger.name == 'pfsconfig_redaction.utils'