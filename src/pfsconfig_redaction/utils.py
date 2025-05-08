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
class RedactedPfsConfigDataClass:
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

    # Convert the first 8 bytes of the hash to a 64-bit integer
    value = int.from_bytes(hash_digest[:8], byteorder="little")
    value = value % np.iinfo(np.int64).max

    return value


def redact(
    pfs_config: PfsConfig,
    cpfsf_id0: int = 0,
    secret_salt: str = None,
    cat_id: int = 9000,
    dict_mask: dict = None,
    flux_keys=None,
    flux_val=None,
    filter_val=None,
) -> list[RedactedPfsConfigDataClass]:
    """
    Redact the PfsConfig object by masking sensitive information.

    Parameters
    ----------
    pfs_config : PfsConfig
        The PfsConfig object to be redacted.
    cpfsf_id0 : int, optional
        The initial cpfsf_id to start from. Default is 0.
    secret_salt : str, optional
        A secret salt used to generate the hash. This should be a unique and
        unpredictable value to ensure the security of the hash.
        If not provided, a ValueError will be raised.
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

    # Initialize the list to hold redacted PfsConfig objects
    redacted_pfsconfigs: list[RedactedPfsConfigDataClass] = []

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

        # Get the number of SCIENCE fibers for targets from this proposal ID
        idx_propid = np.logical_and(
            pfs_config.proposalId == propid_work,
            pfs_config.targetType == TargetType.SCIENCE,
        )
        n_fiber_work = np.sum(idx_propid)

        n_fiber_masked = 0
        n_fiber_unmasked = 0

        # Increment cpfsf_id
        cpfsf_id += 1

        # Create a copy of the original PfsConfig to redact
        redacted_cfg = copy.deepcopy(pfs_config)

        for i_fiber in range(pfs_config.fiberId.size):

            if (
                (redacted_cfg.proposalId[i_fiber] != "N/A")
                and (redacted_cfg.proposalId[i_fiber] != propid_work)
                and (redacted_cfg.targetType[i_fiber] == TargetType.SCIENCE)
            ):
                # Generate hashed object ID before masking catId
                redacted_cfg.objId[i_fiber] = generate_hashed_obj_id(
                    pfs_config.catId[i_fiber],
                    pfs_config.objId[i_fiber],
                    secret_salt=secret_salt,
                )

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

        redacted_pfsconfigs.append(
            RedactedPfsConfigDataClass(
                proposal_id=propid_work, pfs_config=redacted_cfg, cpfsf_id=cpfsf_id
            )
        )

    return redacted_pfsconfigs
