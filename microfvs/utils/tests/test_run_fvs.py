from microfvs.constants import TEST_STANDINIT_RECORDS, TEST_TREEINIT_RECORDS
from microfvs.enums import FvsOutputTableName
from microfvs.models import (
    FvsEventLibrary,
    FvsEventType,
    FvsKeyfile,
    FvsKeyfileTemplateParams,
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


def test_run_fvs():
    params = FvsKeyfileTemplateParams(
        variant=TEST_STANDINIT.variant,
        stand_id=TEST_STANDINIT.stand_id,
        treatments=[TEST_TREATMENT],
        disturbances=[TEST_DISTURBANCE],
    )
    keyfile = FvsKeyfile(params=params)

    result = run_fvs(
        stand_init=TEST_STANDINIT,
        tree_init=TEST_TREEINIT,
        treatments=[TEST_TREATMENT],
        disturbances=[TEST_DISTURBANCE],
    )

    assert isinstance(result, FvsResult)
    assert result.return_code == 0
    assert result.keyfile == keyfile.content
    assert result.outfile is not None
    assert result.fvs_warnings is None
    assert set(result.fvs_data.keys()).issuperset(
        set(EXPECTED_POPULATED_TABLES)
    )
    for table in EXPECTED_POPULATED_TABLES:
        assert isinstance(result.fvs_data[table], list)
        assert len(result.fvs_data[table]) > 0
        assert isinstance(result.fvs_data[table][0], dict)
