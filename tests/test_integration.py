import numpy as np
import pytest
from pfs.datamodel import PfsConfig, TargetType

import pfsconfig_redaction


def science_fibers_of_other_proposals(original, recipient):
    """Indices of the SCIENCE fibers ``recipient`` must not be able to see."""
    return np.flatnonzero(
        (original.targetType == TargetType.SCIENCE)
        & (original.proposalId != "N/A")
        & (original.proposalId != recipient)
    )


class TestIntegration:
    """Integration tests for the complete pfsconfig_redaction workflow.

    These run against the synthetic samples committed under tests/data/, which
    reproduce the schema of the real files (see tests/data/generate_samples.py).
    """

    def test_complete_redaction_workflow(self, pfsf_config, temp_output_dir):
        """Test the complete redaction workflow from file to output."""
        expected_proposal_ids = {
            str(pid) for pid in np.unique(pfsf_config.proposalId) if pid != "N/A"
        }

        redacted_configs = pfsconfig_redaction.redact(pfsf_config)

        assert {config.proposal_id for config in redacted_configs} == (
            expected_proposal_ids
        )

        for redacted_config in redacted_configs:
            output_file = (
                temp_output_dir / f"redacted_{redacted_config.proposal_id}.fits"
            )
            redacted_config.pfs_config.writeFits(output_file)

            assert output_file.exists()

            reloaded_config = PfsConfig.readFits(output_file)
            assert reloaded_config.fiberId.size == pfsf_config.fiberId.size

    def test_redaction_works_on_both_input_formats(self, drp_pfs_config, pfsf_config):
        """Files written by the DRP and files ingested at the summit both redact.

        The DRP writes no FRAMEID/PROP-ID header keywords; the fiber table is the
        same, so the redaction result must be too.
        """
        from_drp = pfsconfig_redaction.redact(drp_pfs_config)
        from_pfsf = pfsconfig_redaction.redact(pfsf_config)

        assert {config.proposal_id for config in from_drp} == (
            {config.proposal_id for config in from_pfsf}
        )

    def test_redaction_preserves_non_science_targets(self, drp_pfs_config):
        """Test that SKY and FLUXSTD targets are preserved in all redacted configs."""
        redacted_configs = pfsconfig_redaction.redact(drp_pfs_config)

        # Count original non-science targets
        original_sky_count = np.sum(drp_pfs_config.targetType == TargetType.SKY)
        original_fluxstd_count = np.sum(drp_pfs_config.targetType == TargetType.FLUXSTD)

        assert len(redacted_configs) > 0

        for redacted_config in redacted_configs:
            redacted_pfs = redacted_config.pfs_config

            # Verify SKY and FLUXSTD targets are preserved
            redacted_sky_count = np.sum(redacted_pfs.targetType == TargetType.SKY)
            redacted_fluxstd_count = np.sum(
                redacted_pfs.targetType == TargetType.FLUXSTD
            )

            assert redacted_sky_count == original_sky_count
            assert redacted_fluxstd_count == original_fluxstd_count

    def test_redaction_masks_other_proposals(self, drp_pfs_config):
        """Test that targets from other proposals are properly masked.

        NOTE: which fibers have to be masked is decided from the *original*
        config. Deciding it from the redacted one would make the check vacuous,
        since masking is what removes the proposalId the condition looks for.
        """
        original = drp_pfs_config
        redacted_configs = pfsconfig_redaction.redact(original)

        for redacted_config in redacted_configs:
            redacted_pfs = redacted_config.pfs_config
            to_mask = science_fibers_of_other_proposals(
                original, redacted_config.proposal_id
            )

            assert to_mask.size > 0, "the sample must contain fibers to mask"

            for i in to_mask:
                assert redacted_pfs.targetType[i] == TargetType.SCIENCE_MASKED
                assert redacted_pfs.proposalId[i] == "masked"
                assert redacted_pfs.obCode[i] == "masked"
                assert redacted_pfs.patch[i] == "-1,-1"
                assert redacted_pfs.catId[i] == 9000
                assert redacted_pfs.objId[i] == -original.fiberId[i]
                assert redacted_pfs.ra[i] == -99
                assert redacted_pfs.dec[i] == -99
                assert np.all(np.isnan(redacted_pfs.fiberFlux[i]))
                assert all(name == "none" for name in redacted_pfs.filterNames[i])

    def test_mask_value_wider_than_the_column_is_not_truncated(self, drp_pfs_config):
        """A mask value longer than the FITS column survives intact.

        The string columns of a pfsConfig are fixed width (patch is 3A, so the
        numpy array is <U3), and assigning a longer value into such an array
        truncates it without warning: "-1,-1" would be stored as "-1,". The
        redacted file has to carry the documented mask value instead.
        """
        original = drp_pfs_config
        long_ob_code = "x" * 60  # obCode is 45A in a real file

        assert original.patch.dtype.itemsize // 4 < len("-1,-1")
        assert original.obCode.dtype.itemsize // 4 < len(long_ob_code)

        redacted_configs = pfsconfig_redaction.redact(
            original,
            dict_mask_science={
                "patch": "-1,-1",
                "obCode": long_ob_code,
                "targetType": TargetType.SCIENCE_MASKED,
            },
        )

        for redacted_config in redacted_configs:
            redacted_pfs = redacted_config.pfs_config
            to_mask = science_fibers_of_other_proposals(
                original, redacted_config.proposal_id
            )

            assert to_mask.size > 0, "the sample must contain fibers to mask"

            for i in to_mask:
                assert redacted_pfs.patch[i] == "-1,-1"
                assert redacted_pfs.obCode[i] == long_ob_code

            # Widening the column must leave every other fiber alone.
            for i in np.flatnonzero(original.proposalId == "N/A"):
                assert redacted_pfs.patch[i] == original.patch[i]
                assert redacted_pfs.obCode[i] == original.obCode[i]

    def test_custom_masking_parameters(self, drp_pfs_config):
        """Test redaction with custom masking parameters."""
        original = drp_pfs_config
        custom_dict_mask = {
            "catId": 8888,
            "ra": -88.0,
            "dec": -88.0,
            "proposalId": "CUSTOM_MAS",  # 10 characters: the column width
        }
        custom_flux_val = -999.0
        custom_filter_val = "MASKED"

        redacted_configs = pfsconfig_redaction.redact(
            original,
            dict_mask_science=custom_dict_mask,
            flux_val=custom_flux_val,
            filter_val=custom_filter_val,
        )

        for redacted_config in redacted_configs:
            redacted_pfs = redacted_config.pfs_config
            to_mask = science_fibers_of_other_proposals(
                original, redacted_config.proposal_id
            )

            assert to_mask.size > 0, "the sample must contain fibers to mask"

            for i in to_mask:
                assert redacted_pfs.proposalId[i] == "CUSTOM_MAS"
                assert redacted_pfs.catId[i] == 8888
                assert redacted_pfs.ra[i] == -88.0
                assert redacted_pfs.dec[i] == -88.0
                assert np.all(redacted_pfs.fiberFlux[i] == custom_flux_val)
                assert all(
                    name == custom_filter_val for name in redacted_pfs.filterNames[i]
                )

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
                if (
                    redacted_pfs.proposalId[i] == proposal_id
                    and redacted_pfs.targetType[i] == TargetType.SCIENCE
                ):
                    unmasked_science_count += 1

            # Verify count matches original
            original_count = np.sum(
                (mock_pfs_config.proposalId == proposal_id)
                & (mock_pfs_config.targetType == TargetType.SCIENCE)
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
