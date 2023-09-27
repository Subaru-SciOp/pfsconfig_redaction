#!/usr/bin/env python3

import copy
import os

import numpy as np
from astropy.io import fits
from logzero import logger
from pfs.datamodel import PfsConfig, PfsDesign


class MaskedPfsDesign:
    """A class to store information on the original pfsDesign and masked pfsDesigns

    Attributes
    ----------
    indir : str
        Directory where the input file is located, by default "."
    outdir : str
        Directory where output files will be saved, by default "."
    out_designs : dict (str, pfs.datamodel.pfsConfig.PfsDesign)
        A dictionary containing a PfsDesign instance (value) for
        each proposal ID (key).
    out_prefix : str
        A prefix for output file, by default "pfsDesign". The output file
        is named as `prefix_{proposal_id}.fits`.

    Methods
    -------
    do_all()
        Mask unnecessary information for all proposal IDs in the input pfsDesign and
        write them separately.
    """

    def _load_design(
        self, pfs_design_identifier, indir=".", is_hex=False, is_file=False, visit=None
    ):
        """Load pfsDesign file

        Parameters
        ----------
        pfs_design_identifier : str or int
            pfsDesign ID.
            The identifier can be one of a hex string (e.g., 0x4f966fa98c958b91),
            an integer (e.g., 5734893949501672337), or
            a filename (e.g., pfsDesign-0x4f966fa98c958b91.fits)
        indir : str, optional
            Directory where the input file is located, by default "."
        is_hex : bool, optional
            True if `pfs_design_identifier` is a hex string, by default False
        is_file : bool, optional
            True if `pfs_design_identifier` is a filename, by default False
        visit : int, optional
            visit number when the input is a pfsConfig file

        Returns
        -------
        pfs.datamodel.pfsConfig.PfsDesign or pfs.datamodel.pfsConfig.PfsConfig
            PfsDesign or PfsConfig class instance depending on the input
        """
        if is_file:
            logger.info(f"pfsDesign filename is provided: {pfs_design_identifier}")
            pfs_design_file = os.path.join(indir, pfs_design_identifier)
            pfs_design_id = fits.getval(pfs_design_file, "W_PFDSGN", 0)
            try:
                visit = fits.getval(pfs_design_file, "W_VISIT", 0)
                design = PfsConfig._readImpl(
                    pfs_design_file, pfsDesignId=pfs_design_id, visit=visit
                )
            except KeyError:
                visit = None
                design = PfsDesign._readImpl(pfs_design_file, pfsDesignId=pfs_design_id)
            return design
        elif is_hex:
            logger.info(
                f"pfsDesignId is provided as a hex string: {pfs_design_identifier}"
            )
            pfs_design_id = int(pfs_design_identifier, 16)
        else:
            logger.info(
                f"pfsDesignId is provided as an integer: {pfs_design_identifier}"
            )
            pfs_design_id = int(pfs_design_identifier)

        if visit is None:
            design = PfsDesign.read(pfs_design_id, dirName=indir)
        else:
            design = PfsConfig.read(pfs_design_id, dirName=indir, visit=visit)
        logger.info(f"{design.filename} successfully loaded from {indir}")

        return design

    def __init__(
        self,
        pfs_design_identifier,
        indir=".",
        outdir=".",
        is_hex=False,
        is_file=False,
        visit=None,
    ):
        """Initialize the class

        Parameters
        ----------
        pfs_design_identifier : str or int
            pfsDesign ID.
            The identifier can be one of a hex string (e.g., 0x4f966fa98c958b91),
            an integer (e.g., 5734893949501672337), or
            a filename (e.g., pfsDesign-0x4f966fa98c958b91.fits)
        is_hex : bool, optional
            True if `pfs_design_identifier` is a hex string, by default False
        is_file : bool, optional
            True if `pfs_design_identifier` is a filename, by default False
        visit : int, optional
            visit number when the input is a pfsConfig file
        """
        self.indir = indir
        self.outdir = outdir
        self.in_design = self._load_design(
            pfs_design_identifier,
            indir=self.indir,
            is_hex=is_hex,
            is_file=is_file,
            visit=visit,
        )
        self.out_designs = {}
        self.out_prefix = os.path.splitext(self.in_design.filename)[0]

    def _write_designs(self):
        """Write pfsDesign files for each proposal ID"""
        for k, v in self.out_designs.items():
            v.validate()
            v.write(dirName=self.outdir, fileName=f"{self.out_prefix}_{k}.fits")
            logger.info(f"{self.out_prefix}_{k}.fits is written in {self.outdir}")

    def _mask_entries(
        self, dict_mask=None, flux_keys=None, flux_val=None, filter_val=None
    ):
        if dict_mask is None:
            # A dictionary defining keys to be masked and their mask values.
            dict_mask = {
                "catId": -1,
                "tract": 0,
                "patch": "0,0",
                "objId": -1,  # (catId, objId)=(-1, -1) is a special case (any issues on DRP?)
                "ra": 0.0,
                "dec": 0.0,
                "pmRa": 0.0,
                "pmDec": 0.0,
                "parallax": 1.0e-8,
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

        proposal_ids = np.unique(self.in_design.proposalId)

        logger.info(f"Unique proposal IDs in the pfsDesign: {*proposal_ids,}")

        for propid_use in proposal_ids:
            if propid_use == "N/A":
                logger.info("Ignoring the proposal ID N/A")
                continue
            logger.info(f"Processing proposal ID {propid_use}")
            design_tmp = copy.deepcopy(self.in_design)
            for i in range(self.in_design.fiberId.size):
                if (design_tmp.proposalId[i] != "N/A") and (
                    design_tmp.proposalId[i] != propid_use
                ):
                    for k, v in dict_mask.items():
                        getattr(design_tmp, k)[i] = v

                    # NOTE: keep the number of elements for flux information
                    for k in flux_keys:
                        val_mask = np.full_like(getattr(design_tmp, k)[i], flux_val)
                        getattr(design_tmp, k)[i] = val_mask

                    filter_mask = [
                        filter_val for _ in getattr(design_tmp, "filterNames")[i]
                    ]
                    getattr(design_tmp, "filterNames")[i] = filter_mask

                    self.out_designs[propid_use] = design_tmp

    def do_all(self):
        self._mask_entries()
        self._write_designs()


masked_pfs_design = MaskedPfsDesign(
    "pfsDesign-0x4f966fa98c958b91.fits",
    indir="./tmp/examples/",
    outdir="./tmp/examples/",
    is_file=True,
)
