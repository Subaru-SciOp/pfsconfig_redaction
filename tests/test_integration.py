#!/usr/bin/env python3

import pytest
import numpy as np
from pathlib import Path
from pfs.datamodel import PfsConfig, TargetType

import pfsconfig_redaction


class TestIntegration:
    """Integration tests for the complete pfsconfig_redaction workflow."""
    
    @pytest.mark.skipif(
        not Path("tmp/PFSF12361000.fits").exists(),
        reason="Sample FITS file not available"
    )
    def test_complete_redaction_workflow(self, sample_fits_path, temp_output_dir):
        """Test the complete redaction workflow from file to output."""
        # Read the original PfsConfig
        pfs_config = PfsConfig.readFits(sample_fits_path)
        original_proposal_ids = np.unique(pfs_config.proposalId)
        
        # Perform redaction
        redacted_configs = pfsconfig_redaction.redact(pfs_config)
        
        # Verify basic properties
        assert isinstance(redacted_configs, list)
        assert len(redacted_configs) > 0
        
        # Verify that we get one result per unique proposal ID (excluding N/A)
        expected_proposal_ids = [pid for pid in original_proposal_ids if pid != "N/A"]
        result_proposal_ids = [config.proposal_id for config in redacted_configs]
        
        assert len(redacted_configs) == len(expected_proposal_ids)
        assert set(result_proposal_ids) == set(expected_proposal_ids)
        
        # Test writing redacted configs to files
        for redacted_config in redacted_configs:
            proposal_id = redacted_config.proposal_id
            output_file = temp_output_dir / f"redacted_{sample_fits_path.stem}_{proposal_id}.fits"
            
            # Write the redacted config
            redacted_config.pfs_config.writeFits(output_file)
            
            # Verify the file was written
            assert output_file.exists()
            
            # Verify we can read it back
            reloaded_config = PfsConfig.readFits(output_file)
            assert reloaded_config is not None
    
    @pytest.mark.skipif(
        not Path("tmp/PFSF12361000.fits").exists(),
        reason="Sample FITS file not available"
    )
    def test_redaction_preserves_non_science_targets(self, sample_fits_path):
        """Test that SKY and FLUXSTD targets are preserved in all redacted configs."""
        pfs_config = PfsConfig.readFits(sample_fits_path)
        redacted_configs = pfsconfig_redaction.redact(pfs_config)
        
        # Count original non-science targets
        original_sky_count = np.sum(pfs_config.targetType == TargetType.SKY)
        original_fluxstd_count = np.sum(pfs_config.targetType == TargetType.FLUXSTD)
        
        for redacted_config in redacted_configs:
            redacted_pfs = redacted_config.pfs_config
            
            # Verify SKY and FLUXSTD targets are preserved
            redacted_sky_count = np.sum(redacted_pfs.targetType == TargetType.SKY)
            redacted_fluxstd_count = np.sum(redacted_pfs.targetType == TargetType.FLUXSTD)
            
            assert redacted_sky_count == original_sky_count
            assert redacted_fluxstd_count == original_fluxstd_count
    
    @pytest.mark.skipif(
        not Path("tmp/PFSF12361000.fits").exists(),
        reason="Sample FITS file not available"
    )
    def test_redaction_masks_other_proposals(self, sample_fits_path):
        """Test that targets from other proposals are properly masked."""
        pfs_config = PfsConfig.readFits(sample_fits_path)
        redacted_configs = pfsconfig_redaction.redact(pfs_config)
        
        for redacted_config in redacted_configs:
            proposal_id = redacted_config.proposal_id
            redacted_pfs = redacted_config.pfs_config
            
            # Check each fiber
            for i in range(len(redacted_pfs.proposalId)):
                if (redacted_pfs.targetType[i] == TargetType.SCIENCE and 
                    redacted_pfs.proposalId[i] != "N/A" and
                    redacted_pfs.proposalId[i] != proposal_id):
                    
                    # Verify this fiber was masked
                    assert redacted_pfs.proposalId[i] == "masked"
                    assert redacted_pfs.catId[i] == 9000
                    assert redacted_pfs.ra[i] == -99
                    assert redacted_pfs.dec[i] == -99
                    assert redacted_pfs.targetType[i] == TargetType.SCIENCE_MASKED
    
    @pytest.mark.skipif(
        not Path("tmp/PFSF12361000.fits").exists(),
        reason="Sample FITS file not available"
    )
    def test_custom_masking_parameters(self, sample_fits_path):
        """Test redaction with custom masking parameters."""
        pfs_config = PfsConfig.readFits(sample_fits_path)
        
        custom_dict_mask = {
            "catId": 8888,
            "ra": -88.0,
            "dec": -88.0,
            "proposalId": "CUSTOM_MASKED"
        }
        custom_flux_val = -999.0
        custom_filter_val = "MASKED"
        
        redacted_configs = pfsconfig_redaction.redact(
            pfs_config,
            dict_mask=custom_dict_mask,
            flux_val=custom_flux_val,
            filter_val=custom_filter_val
        )
        
        for redacted_config in redacted_configs:
            proposal_id = redacted_config.proposal_id
            redacted_pfs = redacted_config.pfs_config
            
            # Check that custom masking values were applied
            for i in range(len(redacted_pfs.proposalId)):
                if (redacted_pfs.targetType[i] == TargetType.SCIENCE_MASKED and
                    redacted_pfs.proposalId[i] == "CUSTOM_MASKED"):
                    
                    assert redacted_pfs.catId[i] == 8888
                    assert redacted_pfs.ra[i] == -88.0
                    assert redacted_pfs.dec[i] == -88.0
                    
                    # Check flux masking
                    assert np.all(redacted_pfs.fiberFlux[i] == custom_flux_val)
                    
                    # Check filter masking
                    assert all(f == custom_filter_val for f in redacted_pfs.filterNames[i])
    
    def test_redaction_with_mock_data(self, mock_pfs_config):
        """Test redaction workflow with mock data."""
        redacted_configs = pfsconfig_redaction.redact(mock_pfs_config)
        
        # Should have 3 unique proposal IDs: S25A-001QF, S25A-002QF, S25A-003QF
        assert len(redacted_configs) == 3
        
        proposal_ids = [config.proposal_id for config in redacted_configs]
        expected_ids = ["S25A-001QF", "S25A-002QF", "S25A-003QF"]
        assert set(proposal_ids) == set(expected_ids)
        
        # Verify each redacted config
        for redacted_config in redacted_configs:
            proposal_id = redacted_config.proposal_id
            redacted_pfs = redacted_config.pfs_config
            
            # Count unmasked science targets for this proposal
            unmasked_science_count = 0
            for i in range(len(redacted_pfs.proposalId)):
                if (redacted_pfs.proposalId[i] == proposal_id and 
                    redacted_pfs.targetType[i] == TargetType.SCIENCE):
                    unmasked_science_count += 1
            
            # Verify count matches original
            original_count = np.sum(
                (mock_pfs_config.proposalId == proposal_id) &
                (mock_pfs_config.targetType == TargetType.SCIENCE)
            )
            assert unmasked_science_count == original_count
    
    def test_error_handling_invalid_input(self):
        """Test error handling with invalid input."""
        with pytest.raises(AttributeError):
            pfsconfig_redaction.redact(None)
        
        with pytest.raises(AttributeError):
            pfsconfig_redaction.redact("not_a_pfs_config")
    
    def test_logging_output(self, simple_mock_pfs_config, caplog):
        """Test that appropriate logging output is generated."""
        import logging
        caplog.set_level(logging.INFO)
        
        pfsconfig_redaction.redact(simple_mock_pfs_config)
        
        # Check that key log messages are present
        log_messages = [record.message for record in caplog.records]
        
        assert any("Starting redaction" in msg for msg in log_messages)
        assert any("pfsDesignId:" in msg for msg in log_messages)
        assert any("Number of fibers:" in msg for msg in log_messages)
        assert any("Processing proposal ID" in msg for msg in log_messages)