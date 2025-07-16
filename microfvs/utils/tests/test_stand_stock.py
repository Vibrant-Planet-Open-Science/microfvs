import numpy as np
import pandas as pd
import pytest

from microfvs.enums import FvsOutputTableName
from microfvs.models import FvsOutputTreeListRecord
from microfvs.utils.stand_stock import (
    ALL_DIAMETER_CLASSES,
    ALL_STAND_STOCK_COLUMNS,
    CUTLIST_CALCULATION_COLUMNS,
    DIAMETER_CLASS_COLUMN_NAME,
    HARVESTED_TREES_PER_ACRE_COLUMN_NAME,
    LIVE_TREES_PER_ACRE_COLUMN_NAME,
    RAW_DIAMETER_COLUMN_NAME,
    RAW_TREES_PER_ACRE_COLUMN_NAME,
    RESIDUAL_CALCULATION_COLUMNS,
    RESIDUAL_TREES_PER_ACRE_COLUMN_NAME,
    SPECIES_FIA_COLUMN_NAME,
    STAND_STOCK_INDEX_COLUMNS,
    TREELIST_CALCULATION_COLUMNS,
    YEAR_COLUMN_NAME,
    FvsStandStockWarning,
    _make_cutlist_stand_stock,
    _make_diameter_class_bins,
    _make_residual_stand_stock,
    _make_treelist_stand_stock,
    make_stand_stock_table,
)

DIAMETER_CLASS_DEFAULT = 4
DIAMETER_CLASS_LOWERED = 3
LARGE_DIAMETER_DEFAULT = 48
LARGE_DIAMETER_LOWERED = 12
NUMBER_OF_RANDOM_TREES = 100

random_treelist = FvsOutputTreeListRecord._random_treelist(
    NUMBER_OF_RANDOM_TREES
)
random_cutlist = FvsOutputTreeListRecord._random_treelist(
    NUMBER_OF_RANDOM_TREES
)
random_residual = FvsOutputTreeListRecord._random_treelist(
    NUMBER_OF_RANDOM_TREES
)


def test_treelist_stand_stock():
    df = pd.DataFrame.from_records(random_treelist)
    bins = _make_diameter_class_bins(
        DIAMETER_CLASS_DEFAULT, LARGE_DIAMETER_DEFAULT
    )
    stand_stock = _make_treelist_stand_stock(df, bins)
    assert isinstance(stand_stock, pd.DataFrame)
    assert list(stand_stock.columns) == TREELIST_CALCULATION_COLUMNS
    assert list(stand_stock.index.names) == STAND_STOCK_INDEX_COLUMNS

    # check that livetpa in smallest diameter class in stand_stock is same as what we
    # get directly from input treelist for all species and years
    for (year, fiaspp), group_trees in df.groupby(
        [YEAR_COLUMN_NAME, SPECIES_FIA_COLUMN_NAME]
    ):
        small_tpa = group_trees.loc[
            group_trees[RAW_DIAMETER_COLUMN_NAME] < DIAMETER_CLASS_DEFAULT
        ][RAW_TREES_PER_ACRE_COLUMN_NAME].sum()

        if small_tpa > 0:
            query_str = (
                f"{DIAMETER_CLASS_COLUMN_NAME} == 0 and "
                f"{SPECIES_FIA_COLUMN_NAME} == '{fiaspp}' and "
                f"{YEAR_COLUMN_NAME} == {year}"
            )
            stand_stock_row = stand_stock.query(query_str)
            assert stand_stock_row[
                LIVE_TREES_PER_ACRE_COLUMN_NAME
            ].item() == pytest.approx(small_tpa)


def test_cutlist_stand_stock():
    df = pd.DataFrame.from_records(random_cutlist)
    bins = _make_diameter_class_bins(
        DIAMETER_CLASS_DEFAULT, LARGE_DIAMETER_DEFAULT
    )
    stand_stock = _make_cutlist_stand_stock(df, bins)
    assert isinstance(stand_stock, pd.DataFrame)
    assert list(stand_stock.columns) == CUTLIST_CALCULATION_COLUMNS
    assert list(stand_stock.index.names) == STAND_STOCK_INDEX_COLUMNS

    # check that harvested tpa in smallest diameter class in stand_stock is same as what
    # we get directly from input cutlist for all species and years
    for (year, fiaspp), group_trees in df.groupby(
        [YEAR_COLUMN_NAME, SPECIES_FIA_COLUMN_NAME]
    ):
        small_tpa = group_trees.loc[
            group_trees[RAW_DIAMETER_COLUMN_NAME] < DIAMETER_CLASS_DEFAULT
        ][RAW_TREES_PER_ACRE_COLUMN_NAME].sum()

        if small_tpa > 0:
            query_str = (
                f"{DIAMETER_CLASS_COLUMN_NAME} == 0 and "
                f"{SPECIES_FIA_COLUMN_NAME} == '{fiaspp}' and "
                f"{YEAR_COLUMN_NAME} == {year}"
            )
            stand_stock_row = stand_stock.query(query_str)
            assert stand_stock_row[
                HARVESTED_TREES_PER_ACRE_COLUMN_NAME
            ].item() == pytest.approx(small_tpa)


def test_residual_stand_stock():
    df = pd.DataFrame.from_records(random_residual)
    bins = _make_diameter_class_bins(
        DIAMETER_CLASS_DEFAULT, LARGE_DIAMETER_DEFAULT
    )
    stand_stock = _make_residual_stand_stock(df, bins)
    assert isinstance(stand_stock, pd.DataFrame)
    assert list(stand_stock.columns) == RESIDUAL_CALCULATION_COLUMNS
    assert list(stand_stock.index.names) == STAND_STOCK_INDEX_COLUMNS

    # check that residual tpa in smallest diameter class in stand_stock is same as what
    # we get directly from input residual treelist for all species and years
    for (year, fiaspp), group_trees in df.groupby(
        [YEAR_COLUMN_NAME, SPECIES_FIA_COLUMN_NAME]
    ):
        small_tpa = group_trees.loc[
            group_trees[RAW_DIAMETER_COLUMN_NAME] < DIAMETER_CLASS_DEFAULT
        ][RAW_TREES_PER_ACRE_COLUMN_NAME].sum()

        if small_tpa > 0:
            query_str = (
                f"{DIAMETER_CLASS_COLUMN_NAME} == 0 and "
                f"{SPECIES_FIA_COLUMN_NAME} == '{fiaspp}' and "
                f"{YEAR_COLUMN_NAME} == {year}"
            )
            stand_stock_row = stand_stock.query(query_str)
            assert stand_stock_row[
                RESIDUAL_TREES_PER_ACRE_COLUMN_NAME
            ].item() == pytest.approx(small_tpa)


def test_treelist_empty():
    df = pd.DataFrame.from_records(random_treelist)[0:0]
    bins = _make_diameter_class_bins(
        DIAMETER_CLASS_DEFAULT, LARGE_DIAMETER_DEFAULT
    )
    stand_stock = _make_treelist_stand_stock(df, bins)
    assert isinstance(stand_stock, pd.DataFrame)
    assert list(stand_stock.columns) == TREELIST_CALCULATION_COLUMNS
    assert list(stand_stock.index.names) == STAND_STOCK_INDEX_COLUMNS
    assert len(stand_stock) == 0


def test_cutlist_empty():
    df = pd.DataFrame.from_records(random_cutlist)[0:0]
    bins = _make_diameter_class_bins(
        DIAMETER_CLASS_DEFAULT, LARGE_DIAMETER_DEFAULT
    )
    stand_stock = _make_cutlist_stand_stock(df, bins)
    assert isinstance(stand_stock, pd.DataFrame)
    assert list(stand_stock.columns) == CUTLIST_CALCULATION_COLUMNS
    assert list(stand_stock.index.names) == STAND_STOCK_INDEX_COLUMNS
    assert len(stand_stock) == 0


def test_residual_empty():
    df = pd.DataFrame.from_records(random_residual)[0:0]
    bins = _make_diameter_class_bins(
        DIAMETER_CLASS_DEFAULT, LARGE_DIAMETER_DEFAULT
    )
    stand_stock = _make_residual_stand_stock(df, bins)
    assert isinstance(stand_stock, pd.DataFrame)
    assert list(stand_stock.columns) == RESIDUAL_CALCULATION_COLUMNS
    assert list(stand_stock.index.names) == STAND_STOCK_INDEX_COLUMNS
    assert len(stand_stock) == 0


def test_combined_stand_stock():
    fvs_treelist_data = {
        FvsOutputTableName.FVS_TREELIST: pd.DataFrame.from_records(
            random_treelist
        ),
        FvsOutputTableName.FVS_CUTLIST: pd.DataFrame.from_records(
            random_cutlist
        ),
        FvsOutputTableName.FVS_AFTER_TREATMENT_TREELIST: pd.DataFrame.from_records(
            random_residual
        ),
    }
    stand_stock = make_stand_stock_table(
        fvs_treelist_data, DIAMETER_CLASS_DEFAULT, LARGE_DIAMETER_DEFAULT
    )
    assert isinstance(stand_stock, pd.DataFrame)
    assert set(stand_stock.columns) == set(ALL_STAND_STOCK_COLUMNS)


def test_no_treelist_output_tables_warning():
    with pytest.warns(FvsStandStockWarning):
        stand_stock = make_stand_stock_table(
            {}, DIAMETER_CLASS_DEFAULT, LARGE_DIAMETER_DEFAULT
        )

    assert isinstance(stand_stock, pd.DataFrame)
    assert list(stand_stock.columns) == ALL_STAND_STOCK_COLUMNS
    assert len(stand_stock) == 0


def test_large_dbh_lowering():
    df = pd.DataFrame.from_records(random_treelist)
    data = {FvsOutputTableName.FVS_TREELIST: df}
    default = make_stand_stock_table(
        data, DIAMETER_CLASS_DEFAULT, LARGE_DIAMETER_DEFAULT
    )
    capped = make_stand_stock_table(
        data, DIAMETER_CLASS_DEFAULT, LARGE_DIAMETER_LOWERED
    )
    assert (
        default.dbh_class.loc[default.dbh_class != ALL_DIAMETER_CLASSES].max()
        > LARGE_DIAMETER_LOWERED
    )
    assert (
        capped.dbh_class.loc[capped.dbh_class != ALL_DIAMETER_CLASSES].max()
        == LARGE_DIAMETER_LOWERED
    )


@pytest.mark.parametrize(
    "diameter_class", [DIAMETER_CLASS_DEFAULT, DIAMETER_CLASS_LOWERED]
)
def test_dbh_class_in_stand_stock_table(diameter_class):
    df = pd.DataFrame.from_records(random_treelist)
    data = {FvsOutputTableName.FVS_TREELIST: df}
    stand_stock = make_stand_stock_table(
        data, diameter_class, LARGE_DIAMETER_DEFAULT
    )

    diameter_classes = stand_stock[DIAMETER_CLASS_COLUMN_NAME].unique()
    assert np.all(
        diameter_classes[diameter_classes != ALL_DIAMETER_CLASSES]
        % diameter_class
        == 0
    )


@pytest.mark.parametrize(
    "diameter_class", [DIAMETER_CLASS_DEFAULT, DIAMETER_CLASS_LOWERED]
)
@pytest.mark.parametrize(
    "large_diameter", [LARGE_DIAMETER_DEFAULT, LARGE_DIAMETER_LOWERED]
)
def test_diameter_class_bin_maker(diameter_class, large_diameter):
    bins = _make_diameter_class_bins(diameter_class, large_diameter)
    assert bins[0] == 0
    assert bins[-1] == np.inf
    assert bins[-2] == large_diameter
    assert len(bins) == large_diameter // diameter_class + 2


# this implicitly tests the _add_all_and_combine helper by focusing on the only row that
# it adds to a stand_stock table
def test_add_all_diameter_totals():
    df = pd.DataFrame.from_records(random_treelist)
    bins = _make_diameter_class_bins(
        DIAMETER_CLASS_DEFAULT, LARGE_DIAMETER_DEFAULT
    )
    stand_stock = _make_treelist_stand_stock(df, bins)
    assert (  # check that "All" in one of the diameter classes
        ALL_DIAMETER_CLASSES
        in stand_stock.index.get_level_values(DIAMETER_CLASS_COLUMN_NAME)
    )

    # check that livetpa in "All" diameter class in stand_stock is same as what we
    # get directly from input treelist for all species and years
    for (year, fiaspp), group_trees in df.groupby(
        [YEAR_COLUMN_NAME, SPECIES_FIA_COLUMN_NAME]
    ):
        all_tpa = group_trees[RAW_TREES_PER_ACRE_COLUMN_NAME].sum()

        query_str = (
            f"{DIAMETER_CLASS_COLUMN_NAME} == '{ALL_DIAMETER_CLASSES}' and "
            f"{SPECIES_FIA_COLUMN_NAME} == '{fiaspp}' and "
            f"{YEAR_COLUMN_NAME} == {year}"
        )
        stand_stock_row = stand_stock.query(query_str)
        assert stand_stock_row[
            LIVE_TREES_PER_ACRE_COLUMN_NAME
        ].item() == pytest.approx(all_tpa)
