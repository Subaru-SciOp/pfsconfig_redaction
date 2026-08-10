from pathlib import Path
from unittest.mock import Mock

import numpy as np
import pytest
from pfs.datamodel import PfsConfig, TargetType

DATA_DIR = Path(__file__).parent / "data"

# Synthetic samples committed under tests/data/. See tests/data/generate_samples.py
# for what they contain and why they are not real observatory files.
DRP_SAMPLE = DATA_DIR / "pfsConfig-0x0123456789abcdef-012345.fits"
PFSF_SAMPLE = DATA_DIR / "PFSF01234500.fits"


@pytest.fixture
def drp_pfs_config():
    """A pfsConfig read from the sample written by the DRP (no FRAMEID/PROP-ID)."""
    return PfsConfig.readFits(DRP_SAMPLE)


@pytest.fixture
def pfsf_config():
    """A pfsConfig read from the sample ingested at the summit (PFSF)."""
    return PfsConfig.readFits(PFSF_SAMPLE)


@pytest.fixture
def mock_pfs_config():
    """Create a comprehensive mock PfsConfig for testing."""
    mock_config = Mock(spec=PfsConfig)

    # Header information
    mock_config.header = {"FRAMEID": "PFSF12361000", "PROP-ID": "S25A-001QF"}
    mock_config.pfsDesignId = 0x12345678
    mock_config.designName = "test_design"

    # Fiber information (10 fibers for more comprehensive testing)
    mock_config.fiberId = np.array([1, 2, 3, 4, 5, 6, 7, 8, 9, 10])
    mock_config.targetType = np.array(
        [
            TargetType.SCIENCE,  # fiber 1: S25A-001QF
            TargetType.SCIENCE,  # fiber 2: S25A-002QF
            TargetType.SCIENCE,  # fiber 3: S25A-001QF
            TargetType.SKY,  # fiber 4: N/A
            TargetType.FLUXSTD,  # fiber 5: N/A
            TargetType.SCIENCE,  # fiber 6: S25A-003QF
            TargetType.SCIENCE,  # fiber 7: S25A-002QF
            TargetType.SKY,  # fiber 8: N/A
            TargetType.SCIENCE,  # fiber 9: S25A-001QF
            TargetType.FLUXSTD,  # fiber 10: N/A
        ]
    )
    mock_config.proposalId = np.array(
        [
            "S25A-001QF",
            "S25A-002QF",
            "S25A-001QF",
            "N/A",
            "N/A",
            "S25A-003QF",
            "S25A-002QF",
            "N/A",
            "S25A-001QF",
            "N/A",
        ]
    )
    mock_config.catId = np.array(
        [1000, 2000, 1000, 3000, 4000, 5000, 2000, 6000, 1000, 7000]
    )
    mock_config.objId = np.array([10, 20, 30, 40, 50, 60, 70, 80, 90, 100])

    # Position and astronomical data
    mock_config.tract = np.array([1, 2, 3, 4, 5, 6, 7, 8, 9, 10])
    mock_config.patch = np.array(
        ["1,1", "2,2", "3,3", "4,4", "5,5", "6,6", "7,7", "8,8", "9,9", "10,10"]
    )
    mock_config.ra = np.array(
        [10.0, 20.0, 30.0, 40.0, 50.0, 60.0, 70.0, 80.0, 90.0, 100.0]
    )
    mock_config.dec = np.array([1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0])
    mock_config.pmRa = np.array([0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0])
    mock_config.pmDec = np.array(
        [0.01, 0.02, 0.03, 0.04, 0.05, 0.06, 0.07, 0.08, 0.09, 0.10]
    )
    mock_config.parallax = np.array(
        [1e-6, 2e-6, 3e-6, 4e-6, 5e-6, 6e-6, 7e-6, 8e-6, 9e-6, 10e-6]
    )
    mock_config.obCode = np.array(
        [
            "code1",
            "code2",
            "code3",
            "code4",
            "code5",
            "code6",
            "code7",
            "code8",
            "code9",
            "code10",
        ]
    )
    mock_config.pfiNominal = np.array(
        [
            (1.0, 1.0),
            (2.0, 2.0),
            (3.0, 3.0),
            (4.0, 4.0),
            (5.0, 5.0),
            (6.0, 6.0),
            (7.0, 7.0),
            (8.0, 8.0),
            (9.0, 9.0),
            (10.0, 10.0),
        ]
    )
    mock_config.pfiCenter = np.array(
        [
            (1.1, 1.1),
            (2.1, 2.1),
            (3.1, 3.1),
            (4.1, 4.1),
            (5.1, 5.1),
            (6.1, 6.1),
            (7.1, 7.1),
            (8.1, 8.1),
            (9.1, 9.1),
            (10.1, 10.1),
        ]
    )

    # Flux measurements (5 bands for each fiber)
    mock_config.fiberFlux = np.array(
        [
            [1.0, 2.0, 3.0, 4.0, 5.0],
            [1.1, 2.1, 3.1, 4.1, 5.1],
            [1.2, 2.2, 3.2, 4.2, 5.2],
            [1.3, 2.3, 3.3, 4.3, 5.3],
            [1.4, 2.4, 3.4, 4.4, 5.4],
            [1.5, 2.5, 3.5, 4.5, 5.5],
            [1.6, 2.6, 3.6, 4.6, 5.6],
            [1.7, 2.7, 3.7, 4.7, 5.7],
            [1.8, 2.8, 3.8, 4.8, 5.8],
            [1.9, 2.9, 3.9, 4.9, 5.9],
        ]
    )
    mock_config.psfFlux = mock_config.fiberFlux + 0.1
    mock_config.totalFlux = mock_config.fiberFlux + 0.2
    mock_config.fiberFluxErr = mock_config.fiberFlux * 0.1
    mock_config.psfFluxErr = mock_config.psfFlux * 0.1
    mock_config.totalFluxErr = mock_config.totalFlux * 0.1

    # Filter information
    # NOTE: a list of lists, as the datamodel defines it. A numpy array would
    # be fixed width, and assigning the mask value "none" into a <U1 array
    # truncates it to "n".
    mock_config.filterNames = [["g", "r", "i", "z", "y"] for _ in range(10)]

    return mock_config


@pytest.fixture
def simple_mock_pfs_config():
    """Create a simple mock PfsConfig for basic testing."""
    mock_config = Mock(spec=PfsConfig)
    mock_config.header = {"FRAMEID": "PFSF12345678", "PROP-ID": "S25A-TEST"}
    mock_config.pfsDesignId = 0x87654321
    mock_config.designName = "simple_test"

    # Minimal fiber setup (3 fibers)
    mock_config.fiberId = np.array([1, 2, 3])
    mock_config.targetType = np.array(
        [TargetType.SCIENCE, TargetType.SKY, TargetType.SCIENCE]
    )
    mock_config.proposalId = np.array(["S25A-TEST", "N/A", "S25A-TEST"])
    mock_config.catId = np.array([1000, 2000, 1000])
    mock_config.objId = np.array([10, 20, 30])

    # Minimal required attributes
    for attr in [
        "tract",
        "patch",
        "ra",
        "dec",
        "pmRa",
        "pmDec",
        "parallax",
        "obCode",
        "pfiNominal",
        "pfiCenter",
        "fiberFlux",
        "psfFlux",
        "totalFlux",
        "fiberFluxErr",
        "psfFluxErr",
        "totalFluxErr",
        "filterNames",
    ]:
        if attr in ["pfiNominal", "pfiCenter"]:
            setattr(mock_config, attr, np.array([(1.0, 1.0), (2.0, 2.0), (3.0, 3.0)]))
        elif attr == "patch":
            setattr(mock_config, attr, np.array(["1,1", "2,2", "3,3"]))
        elif attr == "obCode":
            setattr(mock_config, attr, np.array(["code1", "code2", "code3"]))
        elif "Flux" in attr:
            setattr(mock_config, attr, np.array([[1.0, 2.0], [3.0, 4.0], [5.0, 6.0]]))
        elif attr == "filterNames":
            setattr(mock_config, attr, [["g", "r"], ["i", "z"], ["g", "i"]])
        else:
            setattr(mock_config, attr, np.array([1.0, 2.0, 3.0]))

    return mock_config


@pytest.fixture
def mock_pfs_config_dup_fluxstd():
    """Create a mock PfsConfig containing FLUXSTD objects duplicated as SCIENCE targets.

    Fibers 2 and 6 are flux standards that are also SCIENCE targets of an open-use
    program, so they carry a proposalId instead of "N/A" (see issue #28). Fiber 3 is
    an ordinary flux standard.

    ==========  ==========  ============
    fiberId     targetType  proposalId
    ==========  ==========  ============
    1           SCIENCE     S26A-999QF
    2           FLUXSTD     S26A-999QF
    3           FLUXSTD     N/A
    4           SCIENCE     S26A-888QF
    5           SKY         N/A
    6           FLUXSTD     S26A-888QF
    ==========  ==========  ============
    """
    n_fiber = 6
    mock_config = Mock(spec=PfsConfig)

    mock_config.header = {"FRAMEID": "PFSF99999999", "PROP-ID": "S26A-999QF"}
    mock_config.pfsDesignId = 0x2061554FB4B4FF38
    mock_config.designName = "dup_fluxstd_test"

    mock_config.fiberId = np.arange(1, n_fiber + 1)
    mock_config.targetType = np.array(
        [
            TargetType.SCIENCE,
            TargetType.FLUXSTD,
            TargetType.FLUXSTD,
            TargetType.SCIENCE,
            TargetType.SKY,
            TargetType.FLUXSTD,
        ]
    )
    # NOTE: string dtypes mirror the widths of the real pfsConfig FITS columns
    # (proposalId: 10A, obCode: 45A). Letting numpy infer them would truncate the
    # mask values, e.g. "masked" -> "maske".
    mock_config.proposalId = np.array(
        ["S26A-999QF", "S26A-999QF", "N/A", "S26A-888QF", "N/A", "S26A-888QF"],
        dtype="U10",
    )
    mock_config.obCode = np.array(
        [f"obcode_{i}" for i in range(1, n_fiber + 1)], dtype="U45"
    )
    mock_config.patch = np.array(["1,1"] * n_fiber, dtype="U16")

    mock_config.catId = np.array([1000, 10358, 3006, 2000, 0, 10358])
    mock_config.objId = np.array([10, 20, 30, 40, 50, 60])
    mock_config.tract = np.arange(1, n_fiber + 1)
    mock_config.ra = np.array([10.0, 20.0, 30.0, 40.0, 50.0, 60.0])
    mock_config.dec = np.array([1.0, 2.0, 3.0, 4.0, 5.0, 6.0])
    mock_config.pmRa = np.linspace(0.1, 0.6, n_fiber)
    mock_config.pmDec = np.linspace(0.01, 0.06, n_fiber)
    mock_config.parallax = np.linspace(1e-6, 6e-6, n_fiber)
    mock_config.pfiNominal = np.array([(float(i), float(i)) for i in range(n_fiber)])
    mock_config.pfiCenter = np.array([(i + 0.1, i + 0.1) for i in range(n_fiber)])

    mock_config.fiberFlux = np.arange(1.0, n_fiber * 3 + 1.0).reshape(n_fiber, 3)
    mock_config.psfFlux = mock_config.fiberFlux + 0.1
    mock_config.totalFlux = mock_config.fiberFlux + 0.2
    mock_config.fiberFluxErr = mock_config.fiberFlux * 0.1
    mock_config.psfFluxErr = mock_config.psfFlux * 0.1
    mock_config.totalFluxErr = mock_config.totalFlux * 0.1

    mock_config.filterNames = [["g", "r", "i"] for _ in range(n_fiber)]

    return mock_config


@pytest.fixture
def temp_output_dir(tmp_path):
    """Create a temporary directory for test outputs."""
    output_dir = tmp_path / "test_output"
    output_dir.mkdir()
    return output_dir
