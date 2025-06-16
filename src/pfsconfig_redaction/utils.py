#!/usr/bin/env python3

import copy
import logging
from dataclasses import dataclass
from pprint import pformat
from typing import Union

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


def redact(
    pfs_config: PfsConfig,
    dict_group_id: dict[str, str] | None = None,
    cat_id: int = 9000,
    dict_mask: dict[str, Union[int, str, float]] | None = None,
    flux_keys: list[str] | None = None,
    flux_val: float | None = None,
    filter_val: str | None = None,
) -> list[RedactedPfsConfigDataClass]:
    """
    Redact the PfsConfig object by masking sensitive information.

    Parameters
    ----------
    pfs_config : PfsConfig
        The PfsConfig object to be redacted.
    cpfsf_id0 : int, optional
        The initial cpfsf_id to start from. Default is 0.
    dict_group_id : dict, optional
        A dictionary defining group IDs for different proposal IDs. An example
        is {"S24B-EN16": "o24016", "S25A": "o25103"}. If not provided, the `PROP-ID` header
        keyword will not be replaced.
    cat_id : int, optional
        The catalog ID to be used for masking. Default is 9000.
    dict_mask : dict, optional
        A dictionary defining keys to be masked and their mask values.
        If not provided, a default dictionary will be used.
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

    if dict_mask is None:
        # A dictionary defining keys to be masked and their mask values.
        dict_mask = {
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

    orig_proposal_id = pfs_config.header.get("PROP-ID")
    logger.info(f"Original proposal ID in the pfsConfig: {orig_proposal_id}")

    # Get unique pairs of proposal IDs and catalog IDs
    proposal_ids, catalog_ids = map(
        list, zip(*set(zip(pfs_config.proposalId, pfs_config.catId)))
    )
    # convert from np._str to str
    proposal_ids = [str(s) for s in proposal_ids]

    logger.info(f"Unique proposal IDs in the pfsConfig: {pformat(proposal_ids)}")

    # Initialize the list to hold redacted PfsConfig objects
    redacted_pfsconfigs: list[RedactedPfsConfigDataClass] = []

    for i, propid_work in enumerate(proposal_ids):
        # skip if the proposal ID is "N/A"
        if propid_work == "N/A":
            logger.info(
                f"Ignoring the proposal ID N/A (input_catalog_id {catalog_ids[i]})"
            )
            continue

        logger.info(
            f"Processing proposal ID {propid_work} (input_catalog_id {catalog_ids[i]})"
        )

        # Get the number of SCIENCE fibers for targets from this proposal ID
        idx_propid = np.logical_and(
            pfs_config.proposalId == propid_work,
            pfs_config.targetType == TargetType.SCIENCE,
        )
        n_fiber_work = np.sum(idx_propid)

        n_fiber_masked = 0
        n_fiber_unmasked = 0

        # Create a copy of the original PfsConfig to redact
        redacted_cfg = copy.deepcopy(pfs_config)

        for i_fiber in range(pfs_config.fiberId.size):

            if (
                (redacted_cfg.proposalId[i_fiber] != "N/A")
                and (redacted_cfg.proposalId[i_fiber] != propid_work)
                and (redacted_cfg.targetType[i_fiber] == TargetType.SCIENCE)
            ):
                # Generate hashed object ID before masking catId
                redacted_cfg.objId[i_fiber] = int(-1 * pfs_config.fiberId[i_fiber])

                # Mask values
                for k, v in dict_mask.items():
                    getattr(redacted_cfg, k)[i_fiber] = v

                # NOTE: keep the number of elements for flux and filter information
                for k in flux_keys:
                    val_mask = np.full_like(getattr(redacted_cfg, k)[i_fiber], flux_val)
                    getattr(redacted_cfg, k)[i_fiber] = val_mask

                filter_mask = [
                    filter_val for _ in getattr(redacted_cfg, "filterNames")[i_fiber]
                ]
                getattr(redacted_cfg, "filterNames")[i_fiber] = filter_mask

                n_fiber_masked += 1
            else:
                n_fiber_unmasked += 1

        logger.info(f"Number of fibers for {propid_work}: {n_fiber_work}")
        logger.info(f"Number of masked fibers for {propid_work}: {n_fiber_masked}")
        logger.info(f"Number of unmasked fibers for {propid_work}: {n_fiber_unmasked}")

        if dict_group_id is not None:
            # Check if the proposal ID is in the dictionary
            if propid_work in dict_group_id:
                # Replace the proposal ID with the group ID
                redacted_cfg.header["PROP-ID"] = dict_group_id[propid_work]
                logger.info(
                    f"Replacing the PROP-ID in the header with group ID {dict_group_id[propid_work]}"
                )
            else:
                logger.warning(
                    f"Proposal ID {propid_work} not found in dict_group_id. No replacement made to PROP-ID in the header."
                )
        else:
            logger.warning(
                "dict_group_id is None. No replacement made for PROP-ID in the header."
            )

        redacted_pfsconfigs.append(
            RedactedPfsConfigDataClass(proposal_id=propid_work, pfs_config=redacted_cfg)
        )

    return redacted_pfsconfigs
