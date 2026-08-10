import copy
from unittest.mock import Mock, patch

import numpy as np
import pytest
from pfs.datamodel import PfsConfig, TargetType

from pfsconfig_redaction.utils import redact


class TestLargeInputs:
    """Tests of the redaction against inputs far larger than a real pfsConfig.

    NOTE: these deliberately assert no wall-clock time. Timing thresholds on a
    shared CI runner measure the runner's load, not this code, and the ratios
    they used to compare were dominated by noise because the baseline runs took
    a few milliseconds. What is asserted instead are the properties that would
    actually regress: the input is copied once per proposal rather than once per
    fiber, the peak memory stays bounded, and the result does not change between
    runs.
    """

    def create_large_mock_config(self, n_fibers=10000, n_proposals=50, seed=20250401):
        """Create a large mock PfsConfig for testing.

        NOTE: the data is generated from a fixed seed. With an unseeded
        generator, every run exercised a different fiber table, so a failure
        could not be reproduced from the test alone.
        """
        rng = np.random.default_rng(seed)
        mock_config = Mock(spec=PfsConfig)
        mock_config.header = {"FRAMEID": "PFSF99999999", "PROP-ID": "S25A-PERF"}
        mock_config.pfsDesignId = 0x99999999
        mock_config.designName = "performance_test"

        # Generate fiber data
        mock_config.fiberId = np.arange(1, n_fibers + 1)

        # Mix of target types
        target_types = rng.choice(
            [TargetType.SCIENCE, TargetType.SKY, TargetType.FLUXSTD],
            size=n_fibers,
            p=[0.7, 0.2, 0.1],
        )
        mock_config.targetType = target_types

        # Generate proposal IDs. Only SCIENCE fibers and the flux standards that
        # are also SCIENCE targets of a programme carry a proposal association;
        # sky fibers are always "N/A".
        proposal_base = [f"S25A-{i:03d}QF" for i in range(1, n_proposals + 1)]
        proposal_base.append("N/A")
        proposal_ids = np.where(
            target_types == TargetType.SKY,
            "N/A",
            rng.choice(proposal_base, size=n_fibers),
        )
        mock_config.proposalId = proposal_ids

        # Generate other required data
        mock_config.catId = rng.integers(1000, 9999, size=n_fibers)
        mock_config.objId = np.arange(1, n_fibers + 1) * 10

        # Position and astronomical data
        mock_config.tract = rng.integers(1, 100, size=n_fibers)
        mock_config.patch = np.array(
            [
                f"{i},{j}"
                for i, j in zip(
                    rng.integers(1, 10, size=n_fibers),
                    rng.integers(1, 10, size=n_fibers),
                )
            ]
        )
        mock_config.ra = rng.uniform(0, 360, size=n_fibers)
        mock_config.dec = rng.uniform(-90, 90, size=n_fibers)
        mock_config.pmRa = rng.normal(0, 10, size=n_fibers)
        mock_config.pmDec = rng.normal(0, 10, size=n_fibers)
        mock_config.parallax = rng.exponential(1e-6, size=n_fibers)
        mock_config.obCode = np.array([f"code{i}" for i in range(n_fibers)])
        mock_config.pfiNominal = np.column_stack(
            [
                rng.uniform(-200, 200, size=n_fibers),
                rng.uniform(-200, 200, size=n_fibers),
            ]
        )
        mock_config.pfiCenter = mock_config.pfiNominal + rng.normal(
            0, 0.1, size=(n_fibers, 2)
        )

        # Flux data (5 bands)
        n_bands = 5
        mock_config.fiberFlux = rng.exponential(1000, size=(n_fibers, n_bands))
        mock_config.psfFlux = mock_config.fiberFlux * rng.uniform(
            0.8, 1.2, size=(n_fibers, n_bands)
        )
        mock_config.totalFlux = mock_config.fiberFlux * rng.uniform(
            1.0, 1.5, size=(n_fibers, n_bands)
        )
        mock_config.fiberFluxErr = mock_config.fiberFlux * rng.uniform(
            0.01, 0.1, size=(n_fibers, n_bands)
        )
        mock_config.psfFluxErr = mock_config.psfFlux * rng.uniform(
            0.01, 0.1, size=(n_fibers, n_bands)
        )
        mock_config.totalFluxErr = mock_config.totalFlux * rng.uniform(
            0.01, 0.1, size=(n_fibers, n_bands)
        )

        # Filter names
        filter_names = ["g", "r", "i", "z", "y"]
        mock_config.filterNames = np.array([filter_names for _ in range(n_fibers)])

        return mock_config

    @pytest.mark.slow
    def test_large_dataset_is_redacted_completely(self):
        """A file far larger than a real one is redacted, with nothing left over."""
        n_fibers = 10000
        n_proposals = 50

        mock_config = self.create_large_mock_config(n_fibers, n_proposals)
        expected_proposal_ids = {
            str(pid) for pid in np.unique(mock_config.proposalId) if pid != "N/A"
        }

        result = redact(mock_config)

        assert {item.proposal_id for item in result} == expected_proposal_ids

        for item in result:
            others = np.flatnonzero(
                (mock_config.proposalId != "N/A")
                & (mock_config.proposalId != item.proposal_id)
            )
            assert others.size > 0
            assert set(item.pfs_config.proposalId[others]) <= {"masked", "N/A"}

    @pytest.mark.slow
    def test_memory_usage_large_dataset(self):
        """Test memory usage with large datasets."""
        import tracemalloc

        n_fibers = 5000
        n_proposals = 25

        mock_config = self.create_large_mock_config(n_fibers, n_proposals)

        tracemalloc.start()

        result = redact(mock_config)

        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        # Verify results
        assert isinstance(result, list)
        assert len(result) > 0

        # Memory usage should be reasonable (adjust threshold as needed)
        peak_mb = peak / 1024 / 1024
        assert peak_mb < 500, f"Peak memory usage too high: {peak_mb:.2f} MB"

        print(f"Peak memory usage: {peak_mb:.2f} MB")
        print(f"Current memory usage: {current / 1024 / 1024:.2f} MB")

    def test_input_is_copied_once_per_proposal(self):
        """The work grows with the number of proposals, not with the fibers.

        This replaces a pair of tests that compared wall-clock times as the
        proposal and fiber counts grew. Copying the whole config inside the fiber
        loop is the regression they were trying to catch, and counting the copies
        catches it without measuring anything the runner controls.
        """
        mock_config = self.create_large_mock_config(n_fibers=1000, n_proposals=10)
        real_deepcopy = copy.deepcopy

        with patch(
            "pfsconfig_redaction.utils.copy.deepcopy", side_effect=real_deepcopy
        ) as deepcopy_spy:
            result = redact(mock_config)

        assert len(result) > 1
        assert deepcopy_spy.call_count == len(result)

    def test_repeated_execution_is_deterministic(self):
        """Redacting the same input twice gives the same result.

        This replaces a test that asserted the *duration* of repeated runs stayed
        within a coefficient of variation, which measured the machine rather than
        the code. Two runs agreeing also shows redact() leaves its input alone.
        """
        mock_config = self.create_large_mock_config(n_fibers=1000, n_proposals=10)

        first = redact(mock_config)
        second = redact(mock_config)

        assert [item.proposal_id for item in first] == [
            item.proposal_id for item in second
        ]

        for one, other in zip(first, second):
            assert np.array_equal(
                one.pfs_config.proposalId, other.pfs_config.proposalId
            )
            assert np.array_equal(
                one.pfs_config.targetType, other.pfs_config.targetType
            )
            assert np.array_equal(one.pfs_config.objId, other.pfs_config.objId)
            assert np.array_equal(one.pfs_config.ra, other.pfs_config.ra)
