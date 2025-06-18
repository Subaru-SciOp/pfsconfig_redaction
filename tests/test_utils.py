#!/usr/bin/env python3

import pytest
import numpy as np
from pathlib import Path
from unittest.mock import Mock, patch
from pfs.datamodel import PfsConfig, TargetType

from pfsconfig_redaction.utils import redact, RedactedPfsConfigDataClass


class TestRedactedPfsConfigDataClass:
    """Test the RedactedPfsConfigDataClass dataclass."""
    
    def test_dataclass_creation(self):
        """Test that the dataclass can be created with proper attributes."""
        mock_pfs_config = Mock(spec=PfsConfig)
        proposal_id = "S25A-001QF"
        
        redacted_config = RedactedPfsConfigDataClass(
            proposal_id=proposal_id,
            pfs_config=mock_pfs_config
        )
        
        assert redacted_config.proposal_id == proposal_id
        assert redacted_config.pfs_config == mock_pfs_config


class TestRedactFunction:
    """Test the redact function."""
    
    @pytest.fixture
    def mock_pfs_config(self):
        """Create a mock PfsConfig for testing."""
        mock_config = Mock(spec=PfsConfig)
        mock_config.header = {"FRAMEID": "PFSF12361000", "PROP-ID": "S25A-001QF"}
        mock_config.pfsDesignId = 0x12345678
        mock_config.designName = "test_design"
        
        # Create sample data for 5 fibers
        mock_config.fiberId = np.array([1, 2, 3, 4, 5])
        mock_config.targetType = np.array([
            TargetType.SCIENCE,
            TargetType.SCIENCE, 
            TargetType.SKY,
            TargetType.FLUXSTD,
            TargetType.SCIENCE
        ])
        mock_config.proposalId = np.array([
            "S25A-001QF", "S25A-002QF", "N/A", "N/A", "S25A-001QF"
        ])
        mock_config.catId = np.array([1000, 2000, 3000, 4000, 1000])
        mock_config.objId = np.array([10, 20, 30, 40, 50])
        
        # Add required attributes for masking
        mock_config.tract = np.array([1, 2, 3, 4, 5])
        mock_config.patch = np.array(["1,1", "2,2", "3,3", "4,4", "5,5"])
        mock_config.ra = np.array([10.0, 20.0, 30.0, 40.0, 50.0])
        mock_config.dec = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
        mock_config.pmRa = np.array([0.1, 0.2, 0.3, 0.4, 0.5])
        mock_config.pmDec = np.array([0.01, 0.02, 0.03, 0.04, 0.05])
        mock_config.parallax = np.array([1e-6, 2e-6, 3e-6, 4e-6, 5e-6])
        mock_config.obCode = np.array(["code1", "code2", "code3", "code4", "code5"])
        mock_config.pfiNominal = np.array([(1.0, 1.0), (2.0, 2.0), (3.0, 3.0), (4.0, 4.0), (5.0, 5.0)])
        mock_config.pfiCenter = np.array([(1.1, 1.1), (2.1, 2.1), (3.1, 3.1), (4.1, 4.1), (5.1, 5.1)])
        
        # Add flux attributes
        mock_config.fiberFlux = np.array([[1.0, 2.0], [3.0, 4.0], [5.0, 6.0], [7.0, 8.0], [9.0, 10.0]])
        mock_config.psfFlux = np.array([[1.1, 2.1], [3.1, 4.1], [5.1, 6.1], [7.1, 8.1], [9.1, 10.1]])
        mock_config.totalFlux = np.array([[1.2, 2.2], [3.2, 4.2], [5.2, 6.2], [7.2, 8.2], [9.2, 10.2]])
        mock_config.fiberFluxErr = np.array([[0.1, 0.2], [0.3, 0.4], [0.5, 0.6], [0.7, 0.8], [0.9, 1.0]])
        mock_config.psfFluxErr = np.array([[0.11, 0.21], [0.31, 0.41], [0.51, 0.61], [0.71, 0.81], [0.91, 1.01]])
        mock_config.totalFluxErr = np.array([[0.12, 0.22], [0.32, 0.42], [0.52, 0.62], [0.72, 0.82], [0.92, 1.02]])
        
        # Add filter attributes
        mock_config.filterNames = np.array([
            ["g", "r"], ["r", "i"], ["i", "z"], ["z", "y"], ["g", "i"]
        ])
        
        return mock_config
    
    @patch('pfsconfig_redaction.utils.copy.deepcopy')
    def test_redact_default_parameters(self, mock_deepcopy, mock_pfs_config):
        """Test redact function with default parameters."""
        mock_deepcopy.return_value = mock_pfs_config
        
        result = redact(mock_pfs_config)
        
        assert isinstance(result, list)
        assert len(result) == 2  # Two unique proposal IDs (excluding N/A)
        assert all(isinstance(item, RedactedPfsConfigDataClass) for item in result)
        
        proposal_ids = [item.proposal_id for item in result]
        assert "S25A-001QF" in proposal_ids
        assert "S25A-002QF" in proposal_ids
        assert "N/A" not in proposal_ids
    
    @patch('pfsconfig_redaction.utils.copy.deepcopy')
    def test_redact_custom_parameters(self, mock_deepcopy, mock_pfs_config):
        """Test redact function with custom parameters."""
        mock_deepcopy.return_value = mock_pfs_config
        
        custom_dict_mask = {"catId": 8000, "ra": -88, "dec": -88}
        custom_flux_keys = ["fiberFlux", "psfFlux"]
        custom_flux_val = -999.0
        custom_filter_val = "masked"
        
        result = redact(
            mock_pfs_config,
            cat_id=8000,
            dict_mask=custom_dict_mask,
            flux_keys=custom_flux_keys,
            flux_val=custom_flux_val,
            filter_val=custom_filter_val
        )
        
        assert isinstance(result, list)
        assert len(result) == 2
    
    def test_redact_na_proposal_id_skipped(self, mock_pfs_config):
        """Test that N/A proposal IDs are properly skipped."""
        # Modify mock to have only N/A proposal IDs
        mock_pfs_config.proposalId = np.array(["N/A", "N/A", "N/A", "N/A", "N/A"])
        
        result = redact(mock_pfs_config)
        
        assert isinstance(result, list)
        assert len(result) == 0  # No valid proposal IDs to process
    
    @patch('pfsconfig_redaction.utils.copy.deepcopy')
    def test_redact_fiber_count_validation(self, mock_deepcopy, mock_pfs_config):
        """Test that fiber count validation works correctly."""
        # Create a corrupted copy where targetType gets modified during deepcopy
        # to simulate a scenario where counts don't match
        corrupted_copy = Mock(spec=PfsConfig)
        
        # Copy all attributes from original
        for attr in ['header', 'pfsDesignId', 'designName', 'fiberId', 'proposalId', 
                     'catId', 'objId', 'tract', 'patch', 'ra', 'dec', 'pmRa', 'pmDec', 
                     'parallax', 'obCode', 'pfiNominal', 'pfiCenter', 'fiberFlux', 
                     'psfFlux', 'totalFlux', 'fiberFluxErr', 'psfFluxErr', 'totalFluxErr', 
                     'filterNames']:
            if hasattr(mock_pfs_config, attr):
                setattr(corrupted_copy, attr, getattr(mock_pfs_config, attr))
        
        # Modify the corrupted copy to have a different targetType that creates mismatch
        # Original: S25A-002QF has 1 SCIENCE fiber (position 1)
        # Corrupted: S25A-002QF fiber becomes SKY, creating 0 unmasked SCIENCE fibers
        corrupted_copy.targetType = np.array([
            TargetType.SCIENCE,    # fiber 1: S25A-001QF
            TargetType.SKY,        # fiber 2: S25A-002QF - Changed from SCIENCE 
            TargetType.SKY,        # fiber 3: N/A
            TargetType.FLUXSTD,    # fiber 4: N/A
            TargetType.SCIENCE     # fiber 5: S25A-001QF
        ])
        
        mock_deepcopy.return_value = corrupted_copy
        
        with pytest.raises(ValueError, match="Number of SCIENCE fibers"):
            redact(mock_pfs_config)
    
    def test_redact_none_parameters(self, mock_pfs_config):
        """Test redact function with None parameters uses defaults."""
        result = redact(
            mock_pfs_config,
            dict_mask=None,
            flux_keys=None,
            flux_val=None,
            filter_val=None
        )
        
        assert isinstance(result, list)


class TestRedactIntegration:
    """Integration tests for the redact function with real-like data."""
    
    @pytest.fixture
    def sample_fits_file(self):
        """Path to the sample FITS file for testing."""
        return Path("tmp/PFSF12361000.fits")
    
    @pytest.mark.skipif(
        not Path("tmp/PFSF12361000.fits").exists(),
        reason="Sample FITS file not available"
    )
    def test_redact_with_real_file(self, sample_fits_file):
        """Test redact function with real FITS file."""
        pfs_config = PfsConfig.readFits(sample_fits_file)
        
        result = redact(pfs_config)
        
        assert isinstance(result, list)
        assert len(result) > 0
        assert all(isinstance(item, RedactedPfsConfigDataClass) for item in result)
        
        # Verify that each result has valid proposal IDs
        for redacted_config in result:
            assert redacted_config.proposal_id != "N/A"
            assert isinstance(redacted_config.pfs_config, PfsConfig)
    
    @pytest.mark.skipif(
        not Path("tmp/PFSF12361000.fits").exists(),
        reason="Sample FITS file not available"
    )
    def test_redact_masking_behavior(self, sample_fits_file):
        """Test that masking behavior works correctly with real data."""
        pfs_config = PfsConfig.readFits(sample_fits_file)
        
        result = redact(pfs_config)
        
        for redacted_config in result:
            redacted_pfs = redacted_config.pfs_config
            proposal_id = redacted_config.proposal_id
            
            # Check that other proposal IDs are masked
            for i in range(len(redacted_pfs.proposalId)):
                if (redacted_pfs.proposalId[i] != "N/A" and 
                    redacted_pfs.proposalId[i] != proposal_id and
                    redacted_pfs.targetType[i] == TargetType.SCIENCE):
                    
                    # Verify masking occurred
                    assert redacted_pfs.proposalId[i] == "masked"
                    assert redacted_pfs.catId[i] == 9000  # default cat_id
                    assert redacted_pfs.ra[i] == -99
                    assert redacted_pfs.dec[i] == -99