!ReadMe_REGIMPUTE.txt
Last updated: 3/11/2025
_______________________________________________________________________________
REGIMPUTE: A Customizable Forest Inventory-Based Mean Imputation Method to 
Account for Natural Tree Regeneration in the Forest Vegetation Simulator (FVS)

Authors: Sebastian Busby, Leila Giovannoni, Daniel Swann, Mark Castle
_______________________________________________________________________________
INTRODUCTION

REGIMPUTE is a customizable forest inventory-based mean imputation methodology 
that can add natural tree regeneration into FVS simulations over time. 
REGIMPUTE utilizes an open-source workflow and a robust sample of empirical 
observations (Forest Inventory and Analysis [FIA] data) to summarize observed 
mean natural tree regeneration responses by species at the FVS variant level, 
across a broad range of forest structural states. REGIMPUTE is operationalized 
via customizable keyword files that can be edited for varying simulation 
timelines, conditionality, and user-desired complexity and precision. As stand
structure changes over time due to growth, mortality, and disturbance, 
REGIMPUTE adds species-specific and structural-state appropriate natural tree
regeneration into simulations, while accounting for natural tree regeneration
that may already be present.
________________________________________________________________________________
REGIMPUTE ADDFILES

Included in the REGIMPUTE.zip folder are FVS variant-specific REGIMPUTE
addfiles, or keyword component files (kcp files), that impute natural 
regeneration using the species or shade tolerance regeneration method. The 
following file notation is used for the shade tolerance and species regeneration
method addfiles:

    Regen_ShadeTolerance_Method_XX.kcp
    Regen_SpeciesMethod_XX.kcp

where XX is the two character code for the FVS variant (e.g. "CA"). Addfiles are
not explicitly provided for the KT, OC, and OP FVS variants. The CA and PN
REGIMPUTE addfiles may be assumed when running simulations with the OC and OP
variants respectively. REGIMPUTE kcp files have been developed for variants with
full establishment models. When using the kcps with these variants, users may
want to consider disabling features (e.g. automatic ingrowth) of the full 
establishment model with the relevant FVS keywords.

NOTE: Users are encouraged to read more about the REGIMPUTE regeneration 
methodology and even create their own custom addfiles using resources on the 
REGIMPUTE repository. The link to the repository can be found in the REGIMPUTE
REPOSITORY section below.
________________________________________________________________________________
REGIMPUTE REPOSITORY

Further information about REGIMPUTE and the source code can be found on the
REGIMPUTE repository: https://doi.org/10.6084/m9.figshare.26876338
________________________________________________________________________________
CITATION

Busby, S., Giovannoni, L., Swann, D. & Castle, M. 2024. REGIMPUTE: A 
customizable forest inventory-based mean imputation method to account for 
natural tree regeneration in the Forest Vegetation Simulator (FVS). Version 1.1.
Dataset. Figshare. https://doi.org/10.6084/m9.figshare.26876338