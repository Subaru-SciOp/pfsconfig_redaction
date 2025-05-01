#!/usr/bin/env python3

import copy
import hashlib
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
class RedactedPfsConfig:
    """
    A dataclass to hold the redacted PfsConfig.

    Attributes
    ----------
    proposal_id : str
        The proposal ID associated with the PfsConfig.
    pfs_config : PfsConfig
        The redacted PfsConfig object.
    cpfsf_id : int
        The cpfsf_id associated with the PfsConfig.
    """

    proposal_id: str
    pfs_config: PfsConfig
    cpfsf_id: int


def generate_hashed_obj_id(
    cat_id: int, obj_id: np.int64, secret_salt: str = None
) -> np.int64:
    """
    Generate a hashed object ID based on the given catalog ID, object ID, and secret salt.

    Parameters
    ----------
    cat_id : int
        catId of the object in the original pfsConfig file.
    obj_id : np.int64
        objId of the object in the original pfsConfig file.
    secret_salt : str, optional
        A secret salt used to generate the hash. This should be a unique and
        unpredictable value to ensure the security of the hash.
        If not provided, a ValueError will be raised.

    Returns
    -------
    np.int64
        The hashed object ID, which is a 64-bit integer.
    """

    if secret_salt is None:
        logger.error("secret_salt must be provided")
        raise ValueError("secret_salt must be provided")
    if not isinstance(secret_salt, str):
        logger.error("secret_salt must be a string")
        raise TypeError("secret_salt must be a string")

    # Include the secret salt in the hash input
    hash_input = f"{secret_salt}{cat_id}:{obj_id}".encode("utf-8")
    hash_digest = hashlib.sha256(hash_input).digest()

    value = int.from_bytes(hash_digest[:8], byteorder="little")
    value = value % np.iinfo(np.int64).max

    return value


def redact(
    pfs_config: PfsConfig,
    cpfsf_id0: int = 0,
    dict_mask: dict = None,
    flux_keys=None,
    flux_val=None,
    filter_val=None,
    secret_salt: str = None,
    cat_id: int = 9000,
):
    if secret_salt is None:
        logger.error("secret_salt must be provided")
        raise ValueError("secret_salt must be provided")

    if not isinstance(secret_salt, str):
        logger.error("secret_salt must be a string")
        raise TypeError("secret_salt must be a string")

    if dict_mask is None:
        # A dictionary defining keys to be masked and their mask values.
        dict_mask = {
            "catId": cat_id,
            "tract": 0,
            "patch": "0,0",
            "ra": 0.0,
            "dec": 0.0,
            "pmRa": 0.0,
            "pmDec": 0.0,
            "parallax": 1.0e-7,
            "proposalId": "masked",
            "obCode": "masked",
        }

    if flux_keys is None:
        # Length of flux arrays can be different for each fiber,
        # so only keys are defined here.
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

    # Get unique pairs of proposal IDs and catalog IDs
    proposal_ids, catalog_ids = map(
        list, zip(*set(zip(pfs_config.proposalId, pfs_config.catId)))
    )
    # convert from np._str to str
    proposal_ids = [str(s) for s in proposal_ids]

    logger.info(f"Unique proposal IDs in the pfsConfig: {pformat(proposal_ids)}")

    redacted_pfsconfigs = []

    cpfsf_id = cpfsf_id0

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
        # increment cpfsf_id
        cpfsf_id += 1

        redacted_cfg = copy.deepcopy(pfs_config)

        for i_fiber in range(pfs_config.fiberId.size):
            if (
                (redacted_cfg.proposalId[i_fiber] != "N/A")
                and (redacted_cfg.proposalId[i_fiber] != propid_work)
                and (redacted_cfg.targetType[i_fiber] == TargetType.SCIENCE)
            ):
                # Generate hashed object ID first
                redacted_cfg.objId[i_fiber] = generate_hashed_obj_id(
                    pfs_config.catId[i_fiber],
                    pfs_config.objId[i_fiber],
                    secret_salt=secret_salt,
                )

                # Mask values
                for k, v in dict_mask.items():
                    getattr(redacted_cfg, k)[i_fiber] = v

                # NOTE: keep the number of elements for flux information
                for k in flux_keys:
                    val_mask = np.full_like(getattr(redacted_cfg, k)[i_fiber], flux_val)
                    getattr(redacted_cfg, k)[i_fiber] = val_mask

                filter_mask = [
                    filter_val for _ in getattr(redacted_cfg, "filterNames")[i_fiber]
                ]
                getattr(redacted_cfg, "filterNames")[i_fiber] = filter_mask

        redacted_pfsconfigs.append(
            RedactedPfsConfig(
                proposal_id=propid_work, pfs_config=redacted_cfg, cpfsf_id=cpfsf_id
            )
        )

    return redacted_pfsconfigs
