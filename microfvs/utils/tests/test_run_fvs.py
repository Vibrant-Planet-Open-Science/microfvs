import pytest

from microfvs.constants import TEST_STANDINIT_RECORDS, TEST_TREEINIT_RECORDS
from microfvs.enums import FvsOutputTableName, FvsVariant
from microfvs.models import (
    FvsEventLibrary,
    FvsEventType,
    FvsKeyfile,
    FvsResult,
    FvsStandInit,
    FvsTreeInit,
)
from microfvs.utils.run_fvs import run_fvs

EXPECTED_POPULATED_TABLES = [
    FvsOutputTableName.FVS_CASES,
    FvsOutputTableName.FVS_STAND_STOCK,
    FvsOutputTableName.FVS_STRUCTURE_CLASS,
    FvsOutputTableName.FVS_SUMMARY2,
    FvsOutputTableName.FVS_TREELIST,
]

TEST_DISTURBANCE = FvsEventLibrary().lookup(
    event_type=FvsEventType.DISTURBANCE, event_key="FIC1"
)
TEST_TREATMENT = FvsEventLibrary().lookup(
    event_type=FvsEventType.TREATMENT, event_key="CMCC"
)

TEST_STANDINIT = FvsStandInit.model_validate(TEST_STANDINIT_RECORDS[0])
TEST_TREEINIT = FvsTreeInit.from_records(TEST_TREEINIT_RECORDS)
MISMATCHED_STANDINIT = FvsStandInit(
    stand_id="NONEXISTENT",
    variant=FvsVariant.CA,
    inv_year=2016,
    basal_area_factor=0,
    inv_plot_size=1,
    brk_dbh=999,
)


def test_run_fvs():
    ref_keyfile = FvsKeyfile(
        variant=TEST_STANDINIT.variant,
        stand_id=TEST_STANDINIT.stand_id,
        treatments=[TEST_TREATMENT],
        disturbances=[TEST_DISTURBANCE],
    )

    result = run_fvs(
        stand_init=TEST_STANDINIT,
        tree_init=TEST_TREEINIT,
        template_params={
            "treatments": [TEST_TREATMENT],
            "disturbances": [TEST_DISTURBANCE],
        },
    )

    assert isinstance(result, FvsResult)
    assert result.return_code == 0
    assert result.keyfile == ref_keyfile.content
    assert result.outfile is not None
    assert result.fvs_warnings is None
    assert set(result.fvs_data.keys()).issuperset(
        set(EXPECTED_POPULATED_TABLES)
    )
    for table in EXPECTED_POPULATED_TABLES:
        assert isinstance(result.fvs_data[table], list)
        assert len(result.fvs_data[table]) > 0
        assert isinstance(result.fvs_data[table][0], dict)


def test_run_fvs_warns_on_stand_id_mismatch():
    with pytest.warns(UserWarning, match="not found in tree_init"):
        result = run_fvs(
            stand_init=MISMATCHED_STANDINIT,
            tree_init=TEST_TREEINIT,
        )
    assert isinstance(result, FvsResult)
