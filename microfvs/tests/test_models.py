import subprocess

import pytest

from microfvs.constants import (
    DIAMETER_MAXIMUM,
    DIAMETER_MINIMUM,
    FVS_DATABASE_NAME,
    RESULT_TESTING_KEYFILE_CONTENT,
    STR_PROCESS,
    STR_STAND_ID,
    STR_STOP,
    TEST_FVS_WARNINGS_AND_ERRORS,
    TEST_STANDINIT_RECORDS,
    TEST_TREEINIT_RECORDS,
)
from microfvs.enums import FvsOutputTableName, FvsVariant
from microfvs.models import (
    FvsEventLibrary,
    FvsEventType,
    FvsKeyfile,
    FvsKeyfileTemplateParams,
    FvsOutputTreeListRecord,
    FvsResult,
    FvsStandInit,
    FvsTreeInitRecord,
)

EXPECTED_POPULATED_TABLES = [
    FvsOutputTableName.FVS_CASES,
    FvsOutputTableName.FVS_STAND_STOCK,
    FvsOutputTableName.FVS_STRUCTURE_CLASS,
    FvsOutputTableName.FVS_SUMMARY2,
    FvsOutputTableName.FVS_TREELIST,
]

TEST_FVS_DISTURBANCE = FvsEventLibrary().lookup(
    event_type=FvsEventType.DISTURBANCE, event_key="FIC1"
)
TEST_FVS_TREATMENT = FvsEventLibrary().lookup(
    event_type=FvsEventType.TREATMENT, event_key="CMCC"
)

TEST_STANDINIT = FvsStandInit.model_validate(TEST_STANDINIT_RECORDS[0])
TEST_TREEINIT = [
    FvsTreeInitRecord.model_validate(tree) for tree in TEST_TREEINIT_RECORDS
]


def test_standid_as_int():
    stand_init = FvsStandInit(
        stand_id=12345,
        variant=FvsVariant.INLAND_CALIFORNIA,
        inv_year=1990,
        basal_area_factor=0,
        inv_plot_size=1,
        brk_dbh=999,
    )
    assert stand_init.stand_id == "12345"


def test_keyfile_name():
    stand_init = FvsStandInit(
        stand_id=12345,
        variant=FvsVariant.INLAND_CALIFORNIA,
        inv_year=1990,
        basal_area_factor=0,
        inv_plot_size=1,
        brk_dbh=999,
    )
    params = FvsKeyfileTemplateParams(
        variant=stand_init.variant,
        stand_id=stand_init.stand_id,
        treatments=[TEST_FVS_TREATMENT],
        disturbances=[TEST_FVS_DISTURBANCE],
    )
    keyfile = FvsKeyfile(params=params)
    assert keyfile.name == (
        f"{FvsVariant.INLAND_CALIFORNIA}_{12345}_"
        f"{TEST_FVS_TREATMENT.name}_{TEST_FVS_DISTURBANCE.name}"
    )


@pytest.mark.parametrize("num_trees", [5, 10, 100])
def test_random_treelist(num_trees):
    trees = FvsOutputTreeListRecord._random_treelist(num_trees)
    assert len(trees) == num_trees
    assert trees[0]["dbh"] == DIAMETER_MINIMUM
    assert trees[-1]["dbh"] == DIAMETER_MAXIMUM
    assert (
        FvsOutputTreeListRecord._random_tree(smallest_tree=True).dbh
        == DIAMETER_MINIMUM
    )
    assert (
        FvsOutputTreeListRecord._random_tree(largest_tree=True).dbh
        == DIAMETER_MAXIMUM
    )
    with pytest.raises(
        ValueError,
        match="Only one of smallest_tree and largest_tree can be True.",
    ):
        FvsOutputTreeListRecord._random_tree(
            smallest_tree=True, largest_tree=True
        )


def test_fvs_result(tmp_path):
    params = FvsKeyfileTemplateParams(
        stand_id="12345",
        variant=FvsVariant.INLAND_CALIFORNIA,
        inv_year=1990,
        basal_area_factor=0,
        inv_plot_size=1,
        brk_dbh=999,
    )
    keyfile = FvsKeyfile(template=RESULT_TESTING_KEYFILE_CONTENT, params=params)
    keyfile_path = f"{tmp_path}/{keyfile.name}.key"
    with open(keyfile_path, "w") as f:
        f.write(keyfile.content)

    cmd = [
        f"/usr/local/bin/FVS{keyfile.fvs_variant.lower()}",
        f"--keywordfile={keyfile_path}",
    ]
    proc = subprocess.run(cmd, capture_output=True, cwd=tmp_path)
    db_path = f"{tmp_path}/{FVS_DATABASE_NAME}"
    result = FvsResult.from_files(
        fvs_keyfile=keyfile,
        process=proc,
        path_to_dbout=db_path,
        path_to_outfile=keyfile_path.replace(".key", ".out"),
    )
    assert result.return_code == 0
    assert result.keyfile == keyfile.content
    assert result.command == " ".join(cmd)
    assert result.fvs_warnings is None
    assert result.outfile is not None
    assert set(result.fvs_data.keys()).issuperset(
        set(EXPECTED_POPULATED_TABLES)
    )
    for table in EXPECTED_POPULATED_TABLES:
        assert isinstance(result.fvs_data[table], list)
        assert len(result.fvs_data[table]) > 0
        assert isinstance(result.fvs_data[table][0], dict)

    dumped = result.model_dump()
    assert isinstance(dumped, dict)
    dumped_json = result.model_dump_json()
    assert isinstance(dumped_json, str)


def test_parse_fvs_warnings_errors():
    problems = FvsResult._parse_fvs_warnings_and_errors(
        TEST_FVS_WARNINGS_AND_ERRORS
    )
    assert len(problems) == 3
    assert (
        problems[0].type == "WARNING"
        and problems[0].id == "FVS14"
        and problems[0].line_number == 1
    )
    assert (
        problems[1].type == "WARNING"
        and problems[1].id == "FFE MODEL"
        and problems[1].line_number == 3
    )
    assert (
        problems[2].type == "ERROR"
        and problems[2].id == "FVS01"
        and problems[2].line_number == 6
    )


def test_fvskeyfile():
    stand_init = FvsStandInit.model_validate(TEST_STANDINIT_RECORDS[0])

    params = FvsKeyfileTemplateParams(
        variant=stand_init.variant,
        stand_id=stand_init.stand_id,
        treatments=[TEST_FVS_TREATMENT],
        disturbances=[TEST_FVS_DISTURBANCE],
    )
    keyfile = FvsKeyfile(params=params)

    assert isinstance(keyfile, FvsKeyfile)
    assert keyfile.stand_id == stand_init.stand_id
    assert keyfile.fvs_variant == stand_init.variant
    assert (
        keyfile.content.splitlines()[4]
        == TEST_STANDINIT_RECORDS[0][STR_STAND_ID]
    )
    assert keyfile.content.splitlines()[-2] == STR_PROCESS
    assert keyfile.content.splitlines()[-1] == STR_STOP
