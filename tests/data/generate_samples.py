"""Generate the synthetic pfsConfig samples used by the test suite.

Real pfsConfig and PFSF files carry proprietary target information and cannot be
committed to this repository. The samples produced here are fully synthetic: no
value is copied or derived from an observed file.

What they *do* reproduce is the schema of the real files, because that is what
the redaction code is sensitive to. In particular the FITS string columns are
written with the same widths the observatory produces:

===============  ======  ==================================================
Column           Format  Why it matters
===============  ======  ==================================================
``patch``        ``3A``  A mask value longer than three characters is
                         silently truncated when assigned into the array.
``proposalId``   ``10A`` Same, for the proposal mask value.
``obCode``       ``45A`` Same, for the obCode mask value.
``epoch``        ``7A``
``filterName``   ``6A``  Filter mask values are truncated the same way.
===============  ======  ==================================================

The fiber table also follows the observatory conventions for the non-science
fibers (``catId``/``objId`` of ``-1`` for untargetted fibers, ``obCode`` of
``N/A``, no photometry for engineering fibers) and contains the flux standards
that are duplicated as SCIENCE targets of an open-use program (issue #28).

Two files are written, covering both input formats the tool has to accept:

- ``pfsConfig-0x0123456789abcdef-012345.fits``: as written by the DRP, whose
  header carries neither ``FRAMEID`` nor ``PROP-ID``.
- ``PFSF01234500.fits``: as ingested at the summit, with the extra header
  keywords that come from the telescope.

Regenerate the files with::

    uv run python tests/data/generate_samples.py

The output is deterministic, but not byte-identical between runs: astropy records
the time of writing in the comments of the CHECKSUM/DATASUM cards. Regenerating
therefore always shows a binary diff even when nothing changed, so only commit a
regenerated sample when this script actually changed.
"""

from pathlib import Path

import numpy as np
from astropy.io import fits
from pfs.datamodel import PfsConfig, TargetType
from pfs.datamodel.guideStars import GuideStars
from pfs.datamodel.pfsConfig import FiberStatus

DATA_DIR = Path(__file__).parent

PFS_DESIGN_ID = 0x0123456789ABCDEF
VISIT = 12345
DESIGN_NAME = "synthetic_sample_field_v1"
RA_BORESIGHT = 150.0
DEC_BORESIGHT = 2.0

# Proposal IDs are 10 characters wide in real files, which fixes the width of
# the proposalId column.
PROP_A = "S25A-001QF"
PROP_B = "S25A-002QN"
PROP_C = "S25B-003QF"
NA = "N/A"

# Catalogue IDs follow the observatory's usage: one catalogue per science
# programme, a dedicated sky catalogue and a dedicated flux standard catalogue.
CAT_ID_SCIENCE = {PROP_A: 10094, PROP_B: 10099, PROP_C: 10127}
CAT_ID_SKY = 1007
CAT_ID_FLUXSTD = 3006
CAT_ID_UNTARGETTED = -1

SCIENCE_FILTERS = ["g_hsc", "r2_hsc", "i2_hsc", "z_hsc", "y_ps1"]
NO_FILTERS = ["none"] * len(SCIENCE_FILTERS)

# fiberId, targetType, proposalId, obCode tag. The tag is only used to build an
# obCode; "" means the fiber gets the "N/A" obCode of an unassigned fiber.
# "sample_open_use_2025a_run" is 25 characters, which makes the longest obCode
# exactly 45 characters, as in the real files.
LONG_TAG = "sample_open_use_2025a_run"
FIBERS = [
    (1, TargetType.SCIENCE, PROP_A, LONG_TAG),
    (2, TargetType.SCIENCE, PROP_A, "sample_run"),
    (3, TargetType.SCIENCE, PROP_A, "sample_run"),
    (4, TargetType.SCIENCE, PROP_B, LONG_TAG),
    (5, TargetType.SCIENCE, PROP_B, "sample_survey"),
    (6, TargetType.SCIENCE, PROP_C, "sample_survey"),
    # Flux standards that are also SCIENCE targets of an open-use programme, so
    # they carry a proposalId instead of "N/A" (issue #28).
    (7, TargetType.FLUXSTD, PROP_A, "sample_run"),
    (8, TargetType.FLUXSTD, PROP_B, "sample_survey"),
    # Ordinary flux standards.
    (9, TargetType.FLUXSTD, NA, ""),
    (10, TargetType.FLUXSTD, NA, ""),
    (11, TargetType.SKY, NA, ""),
    (12, TargetType.SKY, NA, ""),
    (13, TargetType.SKY, NA, ""),
    (14, TargetType.UNASSIGNED, NA, ""),
    (15, TargetType.UNASSIGNED, NA, ""),
    (16, TargetType.ENGINEERING, NA, ""),
    (17, TargetType.ENGINEERING, NA, ""),
    (18, TargetType.SCIENCE, PROP_A, "sample_run"),
    (19, TargetType.SCIENCE, PROP_A, "sample_run"),
    (20, TargetType.SCIENCE, PROP_B, "sample_survey"),
    (21, TargetType.SCIENCE, PROP_C, "sample_survey"),
    (22, TargetType.SCIENCE, PROP_C, "sample_survey"),
    (23, TargetType.SKY, NA, ""),
    (24, TargetType.SKY, NA, ""),
]

# Object IDs are of the order of magnitude seen in the real catalogues, but the
# values themselves are made up.
OBJ_ID_BASE = {
    TargetType.SCIENCE: 41135783716870000,
    TargetType.SKY: 19614687479000,
    TargetType.FLUXSTD: 3696507278826379000,
}


def _obj_id(fiber_id: int, target_type: TargetType) -> int:
    """Return a synthetic, unique object ID for a fiber."""
    if target_type in OBJ_ID_BASE:
        return OBJ_ID_BASE[target_type] + fiber_id
    return -1  # untargetted fibers, per the datamodel convention


def _ob_code(fiber_id: int, target_type: TargetType, tag: str) -> str:
    """Return an obCode of the shape used by the observatory."""
    if not tag:
        return NA
    return f"s_{_obj_id(fiber_id, target_type)}_{tag}"


def build_pfs_config(header: dict) -> PfsConfig:
    """Build the synthetic PfsConfig, with ``header`` merged into the primary HDU."""
    n_fiber = len(FIBERS)
    fiber_id = np.array([f[0] for f in FIBERS], dtype=np.int32)
    target_type = np.array([int(f[1]) for f in FIBERS], dtype=np.int32)
    proposal_id = np.array([f[2] for f in FIBERS])
    ob_code = np.array([_ob_code(f[0], f[1], f[3]) for f in FIBERS])

    cat_id = np.array(
        [
            CAT_ID_SCIENCE[f[2]]
            if f[1] == TargetType.SCIENCE
            else CAT_ID_SKY
            if f[1] == TargetType.SKY
            else CAT_ID_FLUXSTD
            if f[1] == TargetType.FLUXSTD
            else CAT_ID_UNTARGETTED
            for f in FIBERS
        ],
        dtype=np.int32,
    )
    obj_id = np.array([_obj_id(f[0], f[1]) for f in FIBERS], dtype=np.int64)

    is_engineering = np.array([f[1] == TargetType.ENGINEERING for f in FIBERS])
    tract = np.where(is_engineering, -1, 1).astype(np.int32)
    patch = np.where(is_engineering, "0,0", "1,1")
    epoch = np.array(
        ["J2016.0" if f[1] == TargetType.FLUXSTD else "J2000.0" for f in FIBERS]
    )

    # Positions are spread over a degree-scale field around the boresight.
    offsets = np.linspace(-0.4, 0.4, n_fiber)
    ra = RA_BORESIGHT + offsets
    dec = DEC_BORESIGHT + offsets[::-1]
    pfi_nominal = np.stack([offsets * 200.0, offsets[::-1] * 200.0], axis=1)
    pfi_center = pfi_nominal + 0.01

    # Engineering fibers carry no photometry; everything else has one entry per
    # filter, with "none" filters for the fibers that were never measured.
    filter_names = []
    for _, tt, _, _ in FIBERS:
        if tt == TargetType.ENGINEERING:
            filter_names.append([])
        elif tt in (TargetType.SCIENCE, TargetType.FLUXSTD):
            filter_names.append(list(SCIENCE_FILTERS))
        else:
            filter_names.append(list(NO_FILTERS))

    fiber_flux = [
        np.arange(1, len(names) + 1, dtype=float) * 1000.0 + i
        for i, names in enumerate(filter_names)
    ]
    psf_flux = [flux * 0.9 for flux in fiber_flux]
    total_flux = [flux * 1.1 for flux in fiber_flux]
    fiber_flux_err = [flux * 0.01 for flux in fiber_flux]
    psf_flux_err = [flux * 0.01 for flux in psf_flux]
    total_flux_err = [flux * 0.01 for flux in total_flux]

    fiber_status = np.full(n_fiber, int(FiberStatus.GOOD), dtype=np.int32)
    fiber_status[13] = int(FiberStatus.BROKENFIBER)
    fiber_status[16] = int(FiberStatus.UNILLUMINATED)

    return PfsConfig(
        pfsDesignId=PFS_DESIGN_ID,
        visit=VISIT,
        raBoresight=RA_BORESIGHT,
        decBoresight=DEC_BORESIGHT,
        posAng=0.0,
        arms="brn",
        fiberId=fiber_id,
        tract=tract,
        patch=patch,
        ra=ra,
        dec=dec,
        catId=cat_id,
        objId=obj_id,
        targetType=target_type,
        fiberStatus=fiber_status,
        epoch=epoch,
        pmRa=np.linspace(-5.0, 5.0, n_fiber).astype(np.float32),
        pmDec=np.linspace(5.0, -5.0, n_fiber).astype(np.float32),
        parallax=np.full(n_fiber, 1.0e-8, dtype=np.float32),
        proposalId=proposal_id,
        obCode=ob_code,
        fiberFlux=fiber_flux,
        psfFlux=psf_flux,
        totalFlux=total_flux,
        fiberFluxErr=fiber_flux_err,
        psfFluxErr=psf_flux_err,
        totalFluxErr=total_flux_err,
        filterNames=filter_names,
        pfiCenter=pfi_center,
        pfiNominal=pfi_nominal,
        guideStars=GuideStars.empty(),
        designName=DESIGN_NAME,
        header=header,
    )


# Keywords added when the file is ingested at the summit. A pfsConfig written by
# the DRP has none of them; the redaction tool has to accept both.
SUMMIT_HEADER = {
    "FRAMEID": "PFSF01234500",
    "EXP-ID": "PFSE01234500",
    "DATA-TYP": "OBJECT",
    "TELESCOP": "Subaru",
    "INSTRUME": "PFS",
    "OBSERVER": "Sample Observer",
    "PROP-ID": PROP_A,
    "DATE-OBS": "2025-04-01",
    "EQUINOX": 2000.0,
    "W_DINROT": 0.0,
}

# The widths the real files have; the samples are worthless if they drift.
EXPECTED_FORMATS = {
    "CONFIG": {"patch": "3A", "epoch": "7A", "proposalId": "10A", "obCode": "45A"},
    "PHOTOMETRY": {"filterName": "6A"},
}


def check_formats(path: Path) -> None:
    """Fail if a written sample does not have the column widths of a real file."""
    with fits.open(path) as hdu_list:
        for hdu_name, expected in EXPECTED_FORMATS.items():
            formats = {c.name: c.format for c in hdu_list[hdu_name].columns}
            for name, fmt in expected.items():
                if formats[name] != fmt:
                    raise SystemExit(
                        f"{path.name}: {hdu_name}.{name} is {formats[name]}, "
                        f"expected {fmt}. The sample no longer matches the real "
                        f"files; adjust the values in this script."
                    )


def main() -> None:
    for filename, header in [
        (f"pfsConfig-{PFS_DESIGN_ID:#018x}-{VISIT:06d}.fits", {}),
        (f"{SUMMIT_HEADER['FRAMEID']}.fits", SUMMIT_HEADER),
    ]:
        path = DATA_DIR / filename
        build_pfs_config(header).writeFits(path)
        check_formats(path)
        print(f"wrote {path} ({path.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
