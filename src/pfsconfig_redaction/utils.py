import copy
import logging
from dataclasses import dataclass
from pprint import pformat

import numpy as np
from pfs.datamodel import PfsConfig, TargetType

# Basic configuration
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

# Get a logger for your module
logger = logging.getLogger(__name__)


# define a dataclass for the redaccted pfsConfig
@dataclass
class RedactedPfsConfigDataClass:
    """
    A dataclass to hold the redacted PfsConfig.

    Attributes
    ----------
    proposal_id : str
        The proposal ID associated with the PfsConfig.
    pfs_config : PfsConfig
        The redacted PfsConfig object.
    """

    proposal_id: str
    pfs_config: PfsConfig


def _target_type_name(target_type: int) -> str:
    """
    Return a readable name for a targetType value.

    Values the installed datamodel does not know about are reported as-is, since
    they are exactly the ones an operator needs to see.

    Parameters
    ----------
    target_type : int
        The targetType value to describe.

    Returns
    -------
    str
        The name of the target type, or the raw value if it is unknown.
    """
    try:
        return TargetType(target_type).name
    except ValueError:
        return f"unknown ({int(target_type)})"


def _widen_string_columns(
    pfs_config: PfsConfig, dict_mask: dict[str, int | str | float | tuple]
) -> None:
    """
    Widen the fixed-width string columns that cannot hold their mask value.

    The string columns of a pfsConfig are fixed width, and the width comes from
    the data: ``patch`` is written as ``3A`` because the values are like "1,1",
    so it is read back as a ``<U3`` array. Assigning a longer string into such
    an array truncates it silently, which would store "-1,-1" as "-1,". The
    column is grown first so that the documented mask value survives; it is
    written back out at whatever width it then needs.

    Parameters
    ----------
    pfs_config : PfsConfig
        The PfsConfig object to be modified in place.
    dict_mask : dict
        The mask values that are going to be assigned into the columns.
    """
    for key, value in dict_mask.items():
        if not isinstance(value, str):
            continue
        array = getattr(pfs_config, key)
        dtype = getattr(array, "dtype", None)
        if dtype is None or dtype.kind != "U":
            continue
        width = dtype.itemsize // np.dtype("U1").itemsize
        if len(value) > width:
            logger.debug(f"  Widening {key} from U{width} to U{len(value)}")
            setattr(pfs_config, key, array.astype(f"U{len(value)}"))


def _equals_mask(actual: np.ndarray, mask_value) -> bool:
    """
    Check that every element of ``actual`` holds ``mask_value``.

    NOTE: the comparison casts the mask value to the dtype it was stored in.
    ``parallax`` is float32 in a real file, so the stored 1.0e-7 does not compare
    equal to the Python float it came from.

    Parameters
    ----------
    actual : numpy.ndarray
        The values found in the redacted config.
    mask_value : int, str, float or tuple
        The value they are supposed to hold.

    Returns
    -------
    bool
        True if every element matches, NaN counting as a match for NaN.
    """
    expected = np.asarray(mask_value)
    if expected.dtype.kind == "f" and actual.dtype.kind == "f":
        expected = expected.astype(actual.dtype)
        return bool(
            np.all((actual == expected) | (np.isnan(actual) & np.isnan(expected)))
        )
    if expected.dtype.kind in "iu" and actual.dtype.kind in "iu":
        expected = expected.astype(actual.dtype)
    return bool(np.all(actual == expected))


def _verify_redaction(
    original: PfsConfig,
    redacted: PfsConfig,
    recipient: str,
    dict_mask_science: dict,
    dict_mask_fluxstd: dict,
    flux_keys: list[str],
    flux_val: float,
    filter_val: str,
) -> None:
    """
    Check the redacted config against the input before it is handed out.

    The check is deliberately expressed against the *output*: which fibers had to
    be masked is derived from the original config, and the redacted one is then
    read back to confirm what actually happened to them. Restating the masking
    rules would only assert that the loop did what the loop does.

    Three things are verified:

    1. every fiber that had to be masked holds the mask values, so a value that
       failed to be stored (silently truncated, for instance) is caught;
    2. no fiber of another proposal still shows its original ``proposalId`` or
       ``obCode``, which holds whatever the mask values happen to be. A custom
       mask dictionary that leaves either in place is refused;
    3. the fibers that had to be left alone are untouched, so redaction cannot
       quietly damage the recipient's own targets or the sky fibers.

    Parameters
    ----------
    original : PfsConfig
        The config as it was read.
    redacted : PfsConfig
        The redacted copy about to be returned.
    recipient : str
        The proposal ID this copy is destined for.
    dict_mask_science, dict_mask_fluxstd : dict
        The mask values that were applied.
    flux_keys : list of str
        The flux fields that were masked.
    flux_val : float
        The value the flux fields were masked with.
    filter_val : str
        The value the filter names were masked with.

    Raises
    ------
    ValueError
        If any of the three checks fails.
    """
    proposal_id = np.asarray(original.proposalId)
    target_type = np.asarray(original.targetType)
    is_other = (proposal_id != "N/A") & (proposal_id != recipient)

    masked_science = np.flatnonzero(is_other & (target_type == TargetType.SCIENCE))
    masked_fluxstd = np.flatnonzero(is_other & (target_type == TargetType.FLUXSTD))
    untouched = np.flatnonzero(~is_other)

    problems: list[str] = []

    # 1. The mask values reached the config.
    for indices, dict_mask in (
        (masked_science, dict_mask_science),
        (masked_fluxstd, dict_mask_fluxstd),
    ):
        if indices.size == 0:
            continue
        for key, value in dict_mask.items():
            actual = np.asarray(getattr(redacted, key))[indices]
            if not _equals_mask(actual, value):
                problems.append(
                    f"{key} was not masked with {value!r} on all "
                    f"{indices.size} fibers that required it"
                )

    for i_fiber in masked_science:
        for key in flux_keys:
            if not _equals_mask(np.asarray(getattr(redacted, key)[i_fiber]), flux_val):
                problems.append(f"{key} was not masked on fiber index {i_fiber}")
        if any(name != filter_val for name in redacted.filterNames[i_fiber]):
            problems.append(f"filterNames was not masked on fiber index {i_fiber}")

    # 2. No proposal association of another programme survives.
    # NOTE: a value that was already "N/A" identifies nothing, and masking it
    # leaves it unchanged, so it is not a survival.
    for indices in (masked_science, masked_fluxstd):
        for key in ("proposalId", "obCode"):
            before = np.asarray(getattr(original, key))[indices]
            after = np.asarray(getattr(redacted, key))[indices]
            still_there = np.flatnonzero((after == before) & (before != "N/A"))
            if still_there.size > 0:
                problems.append(
                    f"{key} of another proposal survived on "
                    f"{still_there.size} fibers, e.g. fiber index "
                    f"{indices[still_there[0]]}"
                )

    # 3. Everything that had to be left alone was left alone.
    keys_touched = set(dict_mask_science) | set(dict_mask_fluxstd) | {"objId"}
    for key in sorted(keys_touched):
        before = np.asarray(getattr(original, key))[untouched]
        after = np.asarray(getattr(redacted, key))[untouched]
        # NOTE: equal_nan, because a NaN that was there before is not a change.
        # Real files carry NaN in the photometry of targets never measured.
        if not np.array_equal(before, after, equal_nan=before.dtype.kind == "f"):
            problems.append(f"{key} was modified on fibers that had to be left alone")

    for i_fiber in untouched:
        for key in flux_keys:
            before = np.asarray(getattr(original, key)[i_fiber])
            after = np.asarray(getattr(redacted, key)[i_fiber])
            if not np.array_equal(before, after, equal_nan=before.dtype.kind == "f"):
                problems.append(f"{key} was modified on fiber index {i_fiber}")
        if list(original.filterNames[i_fiber]) != list(redacted.filterNames[i_fiber]):
            problems.append(f"filterNames was modified on fiber index {i_fiber}")

    if problems:
        message = (
            f"Redaction for proposal {recipient} did not produce a deliverable "
            f"config: {'; '.join(sorted(set(problems)))}."
        )
        logger.error(f"  {message}")
        raise ValueError(message)


def redact(
    pfs_config: PfsConfig,
    cat_id: int = 9000,
    dict_mask_science: dict[str, int | str | float | tuple] | None = None,
    dict_mask_fluxstd: dict[str, int | str | float | tuple] | None = None,
    flux_keys: list[str] | None = None,
    flux_val: float | None = None,
    filter_val: str | None = None,
) -> list[RedactedPfsConfigDataClass]:
    """
    Redact the PfsConfig object by masking sensitive information.

    One redacted PfsConfig is produced per proposal ID found in the input. For each
    of them, fibers belonging to *other* proposals are masked according to their
    target type:

    - ``SCIENCE`` fibers are fully masked: target identity, coordinates, photometry
      and filter names are all replaced, and ``targetType`` becomes
      ``SCIENCE_MASKED``.
    - ``FLUXSTD`` fibers are only stripped of their proposal association, i.e.
      ``proposalId`` and ``obCode`` become ``"N/A"``. This covers flux standards
      that are also targeted as SCIENCE objects by an open-use program. Their
      ``catId``, ``objId``, coordinates and photometry are deliberately kept
      because they are needed for flux calibration downstream, and ``targetType``
      stays ``FLUXSTD``.

    Fibers with ``proposalId == "N/A"`` (ordinary flux standards, sky fibers, ...)
    are never masked.

    Parameters
    ----------
    pfs_config : PfsConfig
        The PfsConfig object to be redacted.
    cat_id : int, optional
        The catalog ID to be used for masking. Default is 9000.
    dict_mask_science : dict, optional
        A dictionary defining keys to be masked and their mask values for SCIENCE
        fibers of other proposals. If not provided, a default dictionary will be used.
    dict_mask_fluxstd : dict, optional
        A dictionary defining keys to be masked and their mask values for FLUXSTD
        fibers of other proposals. If not provided, ``proposalId`` and ``obCode``
        are masked with ``"N/A"``.
    flux_keys : list, optional
        A list of keys for flux values to be masked. Default is a list of
        ["fiberFlux", "psfFlux", "totalFlux", "fiberFluxErr", "psfFluxErr", "totalFluxErr"].
    flux_val : float, optional
        The value to be used for masking flux values. Default is np.nan.
    filter_val : str, optional
        The value to be used for masking filter values. Default is "none".

    Returns
    -------
    list[RedactedPfsConfigDataClass]
        A list of RedactedPfsConfigDataClass objects containing the redacted
        PfsConfig objects and their associated proposal IDs.
    """

    if dict_mask_science is None:
        # A dictionary defining keys to be masked and their mask values
        # for SCIENCE fibers belonging to other proposals.
        dict_mask_science = {
            "catId": cat_id,
            "tract": -1,
            "patch": "-1,-1",
            "ra": -99,
            "dec": -99,
            "pmRa": 0.0,
            "pmDec": 0.0,
            "parallax": 1.0e-7,
            "proposalId": "masked",
            "obCode": "masked",
            "pfiNominal": (np.nan, np.nan),
            "pfiCenter": (np.nan, np.nan),
            "targetType": TargetType.SCIENCE_MASKED,
        }

    if dict_mask_fluxstd is None:
        # FLUXSTD objects duplicated as SCIENCE targets of another proposal only
        # lose their proposal association; everything else is kept so that they
        # remain usable as flux standards.
        dict_mask_fluxstd = {
            "proposalId": "N/A",
            "obCode": "N/A",
        }

    if flux_keys is None:
        flux_keys = [
            "fiberFlux",
            "psfFlux",
            "totalFlux",
            "fiberFluxErr",
            "psfFluxErr",
            "totalFluxErr",
        ]

    if flux_val is None:
        flux_val = np.nan

    if filter_val is None:
        filter_val = "none"

    # NOTE: FRAMEID is present in PFSF files ingested at the summit but not in
    # pfsConfig files written by the DRP. It is used for logging only.
    logger.info(f"Starting redaction of {pfs_config.header.get('FRAMEID', 'N/A')}")
    logger.info(f"  pfsDesignId: {pfs_config.pfsDesignId:#016x}")
    logger.info(f"  pfsDesignName: {pfs_config.designName}")

    orig_proposal_id = pfs_config.header.get("PROP-ID", "N/A")
    logger.info(f"  Original proposal ID: {orig_proposal_id}")

    n_fiber_science: int = np.sum(pfs_config.targetType == TargetType.SCIENCE)
    n_fiber_sky: int = np.sum(pfs_config.targetType == TargetType.SKY)
    n_fiber_fluxstd: int = np.sum(pfs_config.targetType == TargetType.FLUXSTD)
    logger.info(f"  Number of fibers: {len(pfs_config.fiberId)}")
    logger.info(f"  Number of SCIENCE fibers: {n_fiber_science}")
    logger.info(f"  Number of SKY fibers: {n_fiber_sky}")
    logger.info(f"  Number of FLUXSTD fibers: {n_fiber_fluxstd}")

    # Handle empty arrays case
    if len(pfs_config.fiberId) == 0:
        logger.info("  No fibers found, returning empty list")
        return []

    # Get unique proposal IDs only (not grouped by catId), as plain str rather
    # than np.str_.
    # NOTE: sorted, because iterating a set of strings yields an order that
    # varies with PYTHONHASHSEED. Two runs over the same file would otherwise
    # produce their outputs and their logs in a different order.
    proposal_ids = sorted(str(s) for s in set(pfs_config.proposalId))

    logger.info(f"  Unique proposal IDs: {pformat(proposal_ids)}")

    # Initialize the list to hold redacted PfsConfig objects
    redacted_pfsconfigs: list[RedactedPfsConfigDataClass] = []

    for i, propid_work in enumerate(proposal_ids):
        # skip if the proposal ID is "N/A"
        if propid_work == "N/A":
            logger.info("Ignoring the proposal ID N/A")
            continue

        logger.info(f"Processing proposal ID {propid_work}")

        # Get and log the catIds associated with this proposal ID
        catids_for_proposal = pfs_config.catId[pfs_config.proposalId == propid_work]
        unique_catids = sorted({int(x) for x in catids_for_proposal})
        logger.info(f"  Associated catIds: {unique_catids}")

        # Get the number of SCIENCE fibers for targets from this proposal ID
        idx_propid_science = np.logical_and(
            pfs_config.proposalId == propid_work,
            pfs_config.targetType == TargetType.SCIENCE,
        )
        n_fiber_work_science = np.sum(idx_propid_science)

        # Get the number of FLUXSTD fibers for targets from this proposal ID
        idx_propid_fluxstd = np.logical_and(
            pfs_config.proposalId == propid_work,
            pfs_config.targetType == TargetType.FLUXSTD,
        )
        n_fiber_work_fluxstd = np.sum(idx_propid_fluxstd)

        # Create a copy of the original PfsConfig to redact
        redacted_cfg = copy.deepcopy(pfs_config)

        # NOTE: do this before any assignment, otherwise numpy truncates the mask
        # values to the width the column happened to have in the input file.
        _widen_string_columns(redacted_cfg, dict_mask_science)
        _widen_string_columns(redacted_cfg, dict_mask_fluxstd)

        n_fiber_masked_science: int = 0
        n_fiber_masked_fluxstd: int = 0
        n_fiber_masked: int = 0

        n_fiber_unmasked: int = 0
        n_fiber_unmasked_science: int = 0
        n_fiber_unmasked_fluxstd: int = 0

        for i_fiber in range(pfs_config.fiberId.size):
            # Fibers assigned to a proposal other than the one being processed
            is_other_proposal = (redacted_cfg.proposalId[i_fiber] != "N/A") and (
                redacted_cfg.proposalId[i_fiber] != propid_work
            )

            if is_other_proposal and (
                redacted_cfg.targetType[i_fiber] == TargetType.SCIENCE
            ):
                # Generate hashed object ID before masking catId
                redacted_cfg.objId[i_fiber] = int(-1 * pfs_config.fiberId[i_fiber])

                # Mask values
                for k, v in dict_mask_science.items():
                    getattr(redacted_cfg, k)[i_fiber] = v

                # NOTE: keep the number of elements for flux and filter information
                for k in flux_keys:
                    val_mask = np.full_like(getattr(redacted_cfg, k)[i_fiber], flux_val)
                    getattr(redacted_cfg, k)[i_fiber] = val_mask

                filter_mask = [filter_val for _ in redacted_cfg.filterNames[i_fiber]]
                redacted_cfg.filterNames[i_fiber] = filter_mask

                n_fiber_masked_science += 1
                n_fiber_masked += 1
            elif is_other_proposal and (
                redacted_cfg.targetType[i_fiber] == TargetType.FLUXSTD
            ):
                # Mask values for FLUXSTD fibers
                for k, v in dict_mask_fluxstd.items():
                    getattr(redacted_cfg, k)[i_fiber] = v

                n_fiber_masked_fluxstd += 1
                n_fiber_masked += 1
            elif is_other_proposal:
                # NOTE: only SCIENCE and FLUXSTD have a masking rule. Letting any
                # other target type fall through would hand this fiber to the
                # recipient with the proposalId, obCode, coordinates and objId of
                # another proposal intact, so refuse to produce a file at all.
                message = (
                    f"Fiber {redacted_cfg.fiberId[i_fiber]} belongs to proposal "
                    f"{redacted_cfg.proposalId[i_fiber]} and has targetType "
                    f"{_target_type_name(redacted_cfg.targetType[i_fiber])}, for "
                    "which no masking rule is defined. Refusing to redact for "
                    f"proposal {propid_work}."
                )
                logger.error(f"  {message}")
                raise ValueError(message)
            else:
                # Count unmasked SCIENCE fibers belonging to current proposal
                if (
                    redacted_cfg.targetType[i_fiber] == TargetType.SCIENCE
                    and redacted_cfg.proposalId[i_fiber] == propid_work
                ):
                    n_fiber_unmasked_science += 1
                # Count unmasked FLUXSTD fibers belonging to current proposal
                elif (
                    redacted_cfg.targetType[i_fiber] == TargetType.FLUXSTD
                    and redacted_cfg.proposalId[i_fiber] == propid_work
                ):
                    n_fiber_unmasked_fluxstd += 1
                n_fiber_unmasked += 1

        logger.info(
            f"  Number of SCIENCE fibers for {propid_work}: {n_fiber_work_science}"
        )
        logger.info(
            f"  Number of FLUXSTD fibers for {propid_work}: {n_fiber_work_fluxstd}"
        )

        logger.info(
            f"  Number of masked SCIENCE fibers for {propid_work}: {n_fiber_masked_science}"
        )
        logger.info(
            f"  Number of masked FLUXSTD fibers for {propid_work}: {n_fiber_masked_fluxstd}"
        )

        logger.info(f"  Number of masked fibers for {propid_work}: {n_fiber_masked}")

        logger.info(f"  Number of unmasked SCIENCE fibers: {n_fiber_unmasked_science}")
        logger.info(f"  Number of unmasked FLUXSTD fibers: {n_fiber_unmasked_fluxstd}")

        logger.info(
            f"  Number of unmasked fibers for {propid_work}: {n_fiber_unmasked}"
        )

        # NOTE: this used to compare the number of fibers belonging to this
        # proposal with the number left unmasked. Both were counted from the same
        # condition, so they agreed by construction and the check could not fail.
        # The redacted config is inspected instead.
        _verify_redaction(
            pfs_config,
            redacted_cfg,
            propid_work,
            dict_mask_science,
            dict_mask_fluxstd,
            flux_keys,
            flux_val,
            filter_val,
        )

        redacted_pfsconfigs.append(
            RedactedPfsConfigDataClass(proposal_id=propid_work, pfs_config=redacted_cfg)
        )

    return redacted_pfsconfigs
