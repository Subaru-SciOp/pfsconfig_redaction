#!/usr/bin/env python3

import pytest
import time
import numpy as np
from unittest.mock import Mock
from pfs.datamodel import PfsConfig, TargetType

from pfsconfig_redaction.utils import redact


class TestPerformance:
    """Performance tests for the redaction functionality."""
    
    def create_large_mock_config(self, n_fibers=10000, n_proposals=50):
        """Create a large mock PfsConfig for performance testing."""
        mock_config = Mock(spec=PfsConfig)
        mock_config.header = {"FRAMEID": "PFSF99999999", "PROP-ID": "S25A-PERF"}
        mock_config.pfsDesignId = 0x99999999
        mock_config.designName = "performance_test"
        
        # Generate fiber data
        mock_config.fiberId = np.arange(1, n_fibers + 1)
        
        # Mix of target types
        target_types = np.random.choice([
            TargetType.SCIENCE, TargetType.SKY, TargetType.FLUXSTD
        ], size=n_fibers, p=[0.7, 0.2, 0.1])
        mock_config.targetType = target_types
        
        # Generate proposal IDs
        proposal_base = [f"S25A-{i:03d}QF" for i in range(1, n_proposals + 1)]
        proposal_base.append("N/A")
        proposal_ids = np.random.choice(proposal_base, size=n_fibers)
        mock_config.proposalId = proposal_ids
        
        # Generate other required data
        mock_config.catId = np.random.randint(1000, 9999, size=n_fibers)
        mock_config.objId = np.arange(1, n_fibers + 1) * 10
        
        # Position and astronomical data
        mock_config.tract = np.random.randint(1, 100, size=n_fibers)
        mock_config.patch = np.array([f"{i},{j}" for i, j in 
                                    zip(np.random.randint(1, 10, size=n_fibers),
                                        np.random.randint(1, 10, size=n_fibers))])
        mock_config.ra = np.random.uniform(0, 360, size=n_fibers)
        mock_config.dec = np.random.uniform(-90, 90, size=n_fibers)
        mock_config.pmRa = np.random.normal(0, 10, size=n_fibers)
        mock_config.pmDec = np.random.normal(0, 10, size=n_fibers)
        mock_config.parallax = np.random.exponential(1e-6, size=n_fibers)
        mock_config.obCode = np.array([f"code{i}" for i in range(n_fibers)])
        mock_config.pfiNominal = np.column_stack([
            np.random.uniform(-200, 200, size=n_fibers),
            np.random.uniform(-200, 200, size=n_fibers)
        ])
        mock_config.pfiCenter = mock_config.pfiNominal + np.random.normal(0, 0.1, size=(n_fibers, 2))
        
        # Flux data (5 bands)
        n_bands = 5
        mock_config.fiberFlux = np.random.exponential(1000, size=(n_fibers, n_bands))
        mock_config.psfFlux = mock_config.fiberFlux * np.random.uniform(0.8, 1.2, size=(n_fibers, n_bands))
        mock_config.totalFlux = mock_config.fiberFlux * np.random.uniform(1.0, 1.5, size=(n_fibers, n_bands))
        mock_config.fiberFluxErr = mock_config.fiberFlux * np.random.uniform(0.01, 0.1, size=(n_fibers, n_bands))
        mock_config.psfFluxErr = mock_config.psfFlux * np.random.uniform(0.01, 0.1, size=(n_fibers, n_bands))
        mock_config.totalFluxErr = mock_config.totalFlux * np.random.uniform(0.01, 0.1, size=(n_fibers, n_bands))
        
        # Filter names
        filter_names = ["g", "r", "i", "z", "y"]
        mock_config.filterNames = np.array([filter_names for _ in range(n_fibers)])
        
        return mock_config
    
    @pytest.mark.slow
    def test_large_dataset_performance(self):
        """Test redaction performance with a large dataset."""
        n_fibers = 10000
        n_proposals = 50
        
        mock_config = self.create_large_mock_config(n_fibers, n_proposals)
        
        start_time = time.time()
        result = redact(mock_config)
        end_time = time.time()
        
        execution_time = end_time - start_time
        
        # Verify results
        assert isinstance(result, list)
        assert len(result) > 0
        
        # Performance assertion - should complete within reasonable time
        # Adjust threshold based on expected performance
        assert execution_time < 30.0, f"Redaction took too long: {execution_time:.2f} seconds"
        
        print(f"Redacted {n_fibers} fibers with {n_proposals} proposals in {execution_time:.2f} seconds")
        print(f"Generated {len(result)} redacted configurations")
    
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
    
    def test_scalability_with_proposal_count(self):
        """Test how performance scales with number of proposals."""
        n_fibers = 1000
        proposal_counts = [5, 10, 25, 50]
        execution_times = []
        
        for n_proposals in proposal_counts:
            mock_config = self.create_large_mock_config(n_fibers, n_proposals)
            
            start_time = time.time()
            result = redact(mock_config)
            end_time = time.time()
            
            execution_time = end_time - start_time
            execution_times.append(execution_time)
            
            assert isinstance(result, list)
            # Number of results should be at most n_proposals (excluding N/A)
            assert len(result) <= n_proposals
            
            print(f"Proposals: {n_proposals}, Time: {execution_time:.3f}s, Results: {len(result)}")
        
        # Check that execution time doesn't grow too dramatically
        # (allowing for some variance due to system factors)
        time_ratio = execution_times[-1] / execution_times[0]
        proposal_ratio = proposal_counts[-1] / proposal_counts[0]
        
        # Time should scale roughly linearly or better with proposal count
        assert time_ratio < proposal_ratio * 2, f"Performance degraded too much: {time_ratio:.2f}x time for {proposal_ratio:.2f}x proposals"
    
    def test_scalability_with_fiber_count(self):
        """Test how performance scales with number of fibers."""
        n_proposals = 10
        fiber_counts = [100, 500, 1000, 2000]
        execution_times = []
        
        for n_fibers in fiber_counts:
            mock_config = self.create_large_mock_config(n_fibers, n_proposals)
            
            start_time = time.time()
            result = redact(mock_config)
            end_time = time.time()
            
            execution_time = end_time - start_time
            execution_times.append(execution_time)
            
            assert isinstance(result, list)
            assert len(result) <= n_proposals
            
            print(f"Fibers: {n_fibers}, Time: {execution_time:.3f}s, Results: {len(result)}")
        
        # Check scalability
        time_ratio = execution_times[-1] / execution_times[0]
        fiber_ratio = fiber_counts[-1] / fiber_counts[0]
        
        # Time should scale roughly linearly with fiber count
        assert time_ratio < fiber_ratio * 2, f"Performance degraded too much: {time_ratio:.2f}x time for {fiber_ratio:.2f}x fibers"
    
    def test_repeated_execution_consistency(self):
        """Test that repeated executions give consistent performance."""
        n_fibers = 1000
        n_proposals = 10
        n_runs = 5
        
        mock_config = self.create_large_mock_config(n_fibers, n_proposals)
        execution_times = []
        
        for run in range(n_runs):
            start_time = time.time()
            result = redact(mock_config)
            end_time = time.time()
            
            execution_time = end_time - start_time
            execution_times.append(execution_time)
            
            assert isinstance(result, list)
        
        # Check consistency
        mean_time = np.mean(execution_times)
        std_time = np.std(execution_times)
        
        print(f"Mean execution time: {mean_time:.3f}s ± {std_time:.3f}s")
        
        # Standard deviation should be relatively small compared to mean
        coefficient_of_variation = std_time / mean_time
        assert coefficient_of_variation < 0.5, f"Execution time too variable: {coefficient_of_variation:.3f}"