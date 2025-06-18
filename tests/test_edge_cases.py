#!/usr/bin/env python3

import pytest
import numpy as np
from unittest.mock import Mock, patch
from pfs.datamodel import PfsConfig, TargetType

from pfsconfig_redaction.utils import redact, RedactedPfsConfigDataClass


class TestEdgeCases:
    """Test edge cases and error conditions for the redaction functionality."""
    
    def test_empty_proposal_ids(self):
        """Test handling of PfsConfig with no valid proposal IDs."""
        mock_config = Mock(spec=PfsConfig)
        mock_config.header = {"FRAMEID": "PFSF00000000", "PROP-ID": "N/A"}
        mock_config.pfsDesignId = 0x00000000
        mock_config.designName = "empty_test"
        
        # All proposal IDs are N/A
        mock_config.fiberId = np.array([1, 2, 3])
        mock_config.targetType = np.array([TargetType.SCIENCE, TargetType.SKY, TargetType.FLUXSTD])
        mock_config.proposalId = np.array(["N/A", "N/A", "N/A"])
        mock_config.catId = np.array([1000, 2000, 3000])
        
        result = redact(mock_config)
        
        assert isinstance(result, list)
        assert len(result) == 0
    
    def test_single_fiber(self):
        """Test redaction with only one fiber."""
        mock_config = Mock(spec=PfsConfig)
        mock_config.header = {"FRAMEID": "PFSF00000001", "PROP-ID": "S25A-SINGLE"}
        mock_config.pfsDesignId = 0x00000001
        mock_config.designName = "single_fiber_test"
        
        mock_config.fiberId = np.array([1])
        mock_config.targetType = np.array([TargetType.SCIENCE])
        mock_config.proposalId = np.array(["S25A-SINGLE"])
        mock_config.catId = np.array([1000])
        mock_config.objId = np.array([10])
        
        # Add minimal required attributes
        for attr in ["tract", "patch", "ra", "dec", "pmRa", "pmDec", "parallax", 
                     "obCode", "pfiNominal", "pfiCenter", "fiberFlux", "psfFlux", 
                     "totalFlux", "fiberFluxErr", "psfFluxErr", "totalFluxErr", "filterNames"]:
            if attr in ["pfiNominal", "pfiCenter"]:
                setattr(mock_config, attr, np.array([(1.0, 1.0)]))
            elif attr == "patch":
                setattr(mock_config, attr, np.array(["1,1"]))
            elif attr == "obCode":
                setattr(mock_config, attr, np.array(["code1"]))
            elif "Flux" in attr:
                setattr(mock_config, attr, np.array([[1.0, 2.0]]))
            elif attr == "filterNames":
                setattr(mock_config, attr, np.array([["g", "r"]]))
            else:
                setattr(mock_config, attr, np.array([1.0]))
        
        result = redact(mock_config)
        
        assert len(result) == 1
        assert result[0].proposal_id == "S25A-SINGLE"
    
    def test_all_non_science_fibers(self):
        """Test redaction with no SCIENCE fibers."""
        mock_config = Mock(spec=PfsConfig)
        mock_config.header = {"FRAMEID": "PFSF00000002", "PROP-ID": "S25A-NOSCIENCE"}
        mock_config.pfsDesignId = 0x00000002
        mock_config.designName = "no_science_test"
        
        mock_config.fiberId = np.array([1, 2, 3])
        mock_config.targetType = np.array([TargetType.SKY, TargetType.FLUXSTD, TargetType.SKY])
        mock_config.proposalId = np.array(["N/A", "N/A", "N/A"])
        mock_config.catId = np.array([1000, 2000, 3000])
        
        result = redact(mock_config)
        
        assert len(result) == 0
    
    def test_duplicate_proposal_catalog_pairs(self):
        """Test handling of duplicate (proposal_id, catalog_id) pairs."""
        mock_config = Mock(spec=PfsConfig)
        mock_config.header = {"FRAMEID": "PFSF00000003", "PROP-ID": "S25A-DUP"}
        mock_config.pfsDesignId = 0x00000003
        mock_config.designName = "duplicate_test"
        
        mock_config.fiberId = np.array([1, 2, 3, 4])
        mock_config.targetType = np.array([
            TargetType.SCIENCE, TargetType.SCIENCE, 
            TargetType.SCIENCE, TargetType.SCIENCE
        ])
        # Same proposal ID and catalog ID for multiple fibers
        mock_config.proposalId = np.array(["S25A-DUP", "S25A-DUP", "S25A-DUP", "S25A-OTHER"])
        mock_config.catId = np.array([1000, 1000, 1000, 2000])
        mock_config.objId = np.array([10, 20, 30, 40])
        
        # Add required attributes
        for attr in ["tract", "patch", "ra", "dec", "pmRa", "pmDec", "parallax", 
                     "obCode", "pfiNominal", "pfiCenter", "fiberFlux", "psfFlux", 
                     "totalFlux", "fiberFluxErr", "psfFluxErr", "totalFluxErr", "filterNames"]:
            if attr in ["pfiNominal", "pfiCenter"]:
                setattr(mock_config, attr, np.array([(1.0, 1.0), (2.0, 2.0), (3.0, 3.0), (4.0, 4.0)]))
            elif attr == "patch":
                setattr(mock_config, attr, np.array(["1,1", "2,2", "3,3", "4,4"]))
            elif attr == "obCode":
                setattr(mock_config, attr, np.array(["code1", "code2", "code3", "code4"]))
            elif "Flux" in attr:
                setattr(mock_config, attr, np.array([[1.0, 2.0], [3.0, 4.0], [5.0, 6.0], [7.0, 8.0]]))
            elif attr == "filterNames":
                setattr(mock_config, attr, np.array([["g", "r"], ["i", "z"], ["g", "i"], ["r", "z"]]))
            else:
                setattr(mock_config, attr, np.array([1.0, 2.0, 3.0, 4.0]))
        
        result = redact(mock_config)
        
        # Should still get 2 unique proposal IDs
        assert len(result) == 2
        proposal_ids = [config.proposal_id for config in result]
        assert "S25A-DUP" in proposal_ids
        assert "S25A-OTHER" in proposal_ids
    
    def test_very_long_proposal_id(self):
        """Test handling of unusually long proposal IDs."""
        mock_config = Mock(spec=PfsConfig)
        long_proposal_id = "S25A-" + "A" * 100  # Very long proposal ID
        
        mock_config.header = {"FRAMEID": "PFSF00000004", "PROP-ID": long_proposal_id}
        mock_config.pfsDesignId = 0x00000004
        mock_config.designName = "long_id_test"
        
        mock_config.fiberId = np.array([1])
        mock_config.targetType = np.array([TargetType.SCIENCE])
        mock_config.proposalId = np.array([long_proposal_id])
        mock_config.catId = np.array([1000])
        mock_config.objId = np.array([10])
        
        # Add minimal required attributes
        for attr in ["tract", "patch", "ra", "dec", "pmRa", "pmDec", "parallax", 
                     "obCode", "pfiNominal", "pfiCenter", "fiberFlux", "psfFlux", 
                     "totalFlux", "fiberFluxErr", "psfFluxErr", "totalFluxErr", "filterNames"]:
            if attr in ["pfiNominal", "pfiCenter"]:
                setattr(mock_config, attr, np.array([(1.0, 1.0)]))
            elif attr == "patch":
                setattr(mock_config, attr, np.array(["1,1"]))
            elif attr == "obCode":
                setattr(mock_config, attr, np.array(["code1"]))
            elif "Flux" in attr:
                setattr(mock_config, attr, np.array([[1.0, 2.0]]))
            elif attr == "filterNames":
                setattr(mock_config, attr, np.array([["g", "r"]]))
            else:
                setattr(mock_config, attr, np.array([1.0]))
        
        result = redact(mock_config)
        
        assert len(result) == 1
        assert result[0].proposal_id == long_proposal_id
    
    def test_zero_length_arrays(self):
        """Test handling of zero-length arrays."""
        mock_config = Mock(spec=PfsConfig)
        mock_config.header = {"FRAMEID": "PFSF00000005", "PROP-ID": "EMPTY"}
        mock_config.pfsDesignId = 0x00000005
        mock_config.designName = "empty_arrays_test"
        
        # Zero-length arrays
        for attr in ["fiberId", "targetType", "proposalId", "catId", "objId"]:
            setattr(mock_config, attr, np.array([]))
        
        result = redact(mock_config)
        
        assert len(result) == 0
    
    @patch('pfsconfig_redaction.utils.copy.deepcopy')
    def test_deepcopy_failure(self, mock_deepcopy, simple_mock_pfs_config):
        """Test handling of deepcopy failure."""
        mock_deepcopy.side_effect = RuntimeError("Deepcopy failed")
        
        with pytest.raises(RuntimeError, match="Deepcopy failed"):
            redact(simple_mock_pfs_config)
    
    def test_invalid_target_types(self):
        """Test handling of invalid target types."""
        mock_config = Mock(spec=PfsConfig)
        mock_config.header = {"FRAMEID": "PFSF00000006", "PROP-ID": "S25A-INVALID"}
        mock_config.pfsDesignId = 0x00000006
        mock_config.designName = "invalid_types_test"
        
        mock_config.fiberId = np.array([1, 2])
        mock_config.targetType = np.array([999, -1])  # Invalid target types
        mock_config.proposalId = np.array(["S25A-INVALID", "S25A-INVALID"])
        mock_config.catId = np.array([1000, 2000])
        mock_config.objId = np.array([10, 20])
        
        # Add minimal required attributes
        for attr in ["tract", "patch", "ra", "dec", "pmRa", "pmDec", "parallax", 
                     "obCode", "pfiNominal", "pfiCenter", "fiberFlux", "psfFlux", 
                     "totalFlux", "fiberFluxErr", "psfFluxErr", "totalFluxErr", "filterNames"]:
            if attr in ["pfiNominal", "pfiCenter"]:
                setattr(mock_config, attr, np.array([(1.0, 1.0), (2.0, 2.0)]))
            elif attr == "patch":
                setattr(mock_config, attr, np.array(["1,1", "2,2"]))
            elif attr == "obCode":
                setattr(mock_config, attr, np.array(["code1", "code2"]))
            elif "Flux" in attr:
                setattr(mock_config, attr, np.array([[1.0, 2.0], [3.0, 4.0]]))
            elif attr == "filterNames":
                setattr(mock_config, attr, np.array([["g", "r"], ["i", "z"]]))
            else:
                setattr(mock_config, attr, np.array([1.0, 2.0]))
        
        # Should handle invalid target types gracefully
        result = redact(mock_config)
        assert len(result) == 1
    
    def test_nan_and_inf_values(self):
        """Test handling of NaN and infinity values in input data."""
        mock_config = Mock(spec=PfsConfig)
        mock_config.header = {"FRAMEID": "PFSF00000007", "PROP-ID": "S25A-NANTEST"}
        mock_config.pfsDesignId = 0x00000007
        mock_config.designName = "nan_test"
        
        mock_config.fiberId = np.array([1, 2])
        mock_config.targetType = np.array([TargetType.SCIENCE, TargetType.SCIENCE])
        mock_config.proposalId = np.array(["S25A-NANTEST", "S25A-OTHER"])
        mock_config.catId = np.array([1000, 2000])
        mock_config.objId = np.array([10, 20])
        
        # Include NaN and inf values
        mock_config.ra = np.array([np.nan, np.inf])
        mock_config.dec = np.array([-np.inf, 45.0])
        mock_config.fiberFlux = np.array([[np.nan, 2.0], [3.0, np.inf]])
        
        # Add other required attributes
        for attr in ["tract", "patch", "pmRa", "pmDec", "parallax", 
                     "obCode", "pfiNominal", "pfiCenter", "psfFlux", 
                     "totalFlux", "fiberFluxErr", "psfFluxErr", "totalFluxErr", "filterNames"]:
            if attr in ["pfiNominal", "pfiCenter"]:
                setattr(mock_config, attr, np.array([(1.0, 1.0), (2.0, 2.0)]))
            elif attr == "patch":
                setattr(mock_config, attr, np.array(["1,1", "2,2"]))
            elif attr == "obCode":
                setattr(mock_config, attr, np.array(["code1", "code2"]))
            elif "Flux" in attr and attr != "fiberFlux":
                setattr(mock_config, attr, np.array([[1.0, 2.0], [3.0, 4.0]]))
            elif attr == "filterNames":
                setattr(mock_config, attr, np.array([["g", "r"], ["i", "z"]]))
            else:
                setattr(mock_config, attr, np.array([1.0, 2.0]))
        
        # Should handle NaN/inf values without crashing
        result = redact(mock_config)
        assert len(result) == 2
    
    def test_empty_filter_names(self):
        """Test handling of empty filter names."""
        mock_config = Mock(spec=PfsConfig)
        mock_config.header = {"FRAMEID": "PFSF00000008", "PROP-ID": "S25A-NOFILTER"}
        mock_config.pfsDesignId = 0x00000008
        mock_config.designName = "no_filter_test"
        
        mock_config.fiberId = np.array([1])
        mock_config.targetType = np.array([TargetType.SCIENCE])
        mock_config.proposalId = np.array(["S25A-NOFILTER"])
        mock_config.catId = np.array([1000])
        mock_config.objId = np.array([10])
        
        # Empty filter names
        mock_config.filterNames = np.array([[]])
        
        # Add other required attributes
        for attr in ["tract", "patch", "ra", "dec", "pmRa", "pmDec", "parallax", 
                     "obCode", "pfiNominal", "pfiCenter", "fiberFlux", "psfFlux", 
                     "totalFlux", "fiberFluxErr", "psfFluxErr", "totalFluxErr"]:
            if attr in ["pfiNominal", "pfiCenter"]:
                setattr(mock_config, attr, np.array([(1.0, 1.0)]))
            elif attr == "patch":
                setattr(mock_config, attr, np.array(["1,1"]))
            elif attr == "obCode":
                setattr(mock_config, attr, np.array(["code1"]))
            elif "Flux" in attr:
                setattr(mock_config, attr, np.array([[1.0]]))  # Single element to match empty filter
            else:
                setattr(mock_config, attr, np.array([1.0]))
        
        # Should handle empty filter names gracefully
        result = redact(mock_config)
        assert len(result) == 1