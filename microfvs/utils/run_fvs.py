import os
import sqlite3
import subprocess
import tempfile
import warnings

import pandas as pd

from microfvs.constants import (
    FVS_DATABASE_NAME,
    STAND_ID_COLUMN_NAME,
)
from microfvs.enums import FvsKeyfileTemplate
from microfvs.models import (
    FvsKeyfile,
    FvsResult,
    FvsStandInit,
    FvsStandStockParams,
    FvsTreeInit,
    FvsTreeInitRecord,
)


def run_fvs(
    stand_init: FvsStandInit,
    tree_init: FvsTreeInit | None = None,
    template: str = FvsKeyfileTemplate.DEFAULT,
    template_params: dict = {},
    stand_stock_params: FvsStandStockParams = FvsStandStockParams(),
) -> FvsResult:
    """Runs a single FVS simulation and returns the result(s).

    Args:
        stand_init (FvsStandInit): Stand initialization data for one or
            more stands. All stands represented in stand_init will be
            run in the order specified unless or until `limit` is
            reached.
        tree_init (FvsTreeInit, optional): Tree initialization data for
            one or more stands. If not provided, bare ground will be
            simulated.
        template (str, optional): FVS keyfile template to use. Defaults
            to FvsKeyfileTemplate.DEFAULT
        template_params (dict, optional): Template variables
            (e.g. treatments, disturbances, num_cycles,
            cycle_length, custom placeholders). ``variant`` and
            ``stand_id`` are always derived from ``stand_init``.
        stand_stock_params (FvsStandStockParams): Optional set of
            parameters to govern the generation of a Stand and Stock
            Table in the FVS outputs. Default is to produce the Stand
            and Stock Table, and to do so using DBH classes of 4 inches
            and a large diameter category starting at 48 inches DBH.

    Returns:
        A single FvsResult.
    """
    if tree_init is None:
        tree_init_df = pd.DataFrame(
            columns=list(FvsTreeInitRecord.model_fields.keys())
        )
    else:
        tree_init_df = tree_init.to_dataframe()
        tree_stand_ids = set(tree_init_df[STAND_ID_COLUMN_NAME].unique())
        if stand_init.stand_id not in tree_stand_ids:
            warnings.warn(
                f"stand_id '{stand_init.stand_id}' not found in tree_init "
                f"(found: {tree_stand_ids}). Will simulate bare ground.",
                stacklevel=2,
            )

    with tempfile.TemporaryDirectory() as temp_dir:
        db_path = os.path.join(temp_dir, FVS_DATABASE_NAME)
        conn = sqlite3.connect(db_path)

        stand_data = stand_init.to_dataframe()

        fvs_variant = stand_init.variant
        stand_id = stand_init.stand_id

        stand_data.to_sql(
            "fvs_standinit", conn, if_exists="replace", index=False
        )
        tree_data = tree_init_df.loc[
            tree_init_df[STAND_ID_COLUMN_NAME] == stand_id
        ]
        tree_data.to_sql("fvs_treeinit", conn, if_exists="replace", index=False)

        kw = dict(template_params)
        reserved = FvsKeyfile.RESERVED_TEMPLATE_KEYS & kw.keys()
        if reserved:
            msg = (
                f"template_params contains reserved key(s): {reserved}. "
                "These are derived automatically and cannot be overridden."
            )
            raise ValueError(msg)
        treatments = kw.pop("treatments", None)
        disturbances = kw.pop("disturbances", None)
        keyfile_args: dict = {
            "variant": fvs_variant,
            "stand_id": stand_id,
            "template": template,
            "template_params": kw,
        }
        if treatments is not None:
            keyfile_args["treatments"] = treatments
        if disturbances is not None:
            keyfile_args["disturbances"] = disturbances
        keyfile = FvsKeyfile(**keyfile_args)

        keyfile_path = os.path.join(temp_dir, keyfile.name + ".key")
        with open(keyfile_path, "w") as f:
            f.write(keyfile.content)

        cmd = [
            f"/usr/local/bin/FVS{keyfile.fvs_variant.lower()}",
            f"--keywordfile={keyfile.name}.key",
        ]
        process = subprocess.run(cmd, capture_output=True, cwd=temp_dir)

        return FvsResult.from_files(
            fvs_keyfile=keyfile,
            process=process,
            path_to_dbout=db_path,
            path_to_outfile=keyfile_path.replace(".key", ".out"),
            add_stand_stock=stand_stock_params.add_stand_stock,
            dbh_class=stand_stock_params.dbh_class,
            large_dbh=stand_stock_params.large_dbh,
        )
