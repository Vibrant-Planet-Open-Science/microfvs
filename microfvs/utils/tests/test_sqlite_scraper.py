import pandas as pd
import pytest
import sqlalchemy as db

from microfvs.constants import FVS_DATABASE_NAME
from microfvs.enums import FvsOutputTableName
from microfvs.models import FvsOutputTreeListRecord
from microfvs.utils.sqlite_scraper import FvsSqliteScraper, SqliteScraper
from microfvs.utils.stand_stock import (
    ALL_STAND_STOCK_COLUMNS,
    FvsStandStockWarning,
)

WRONG_TABLE_NAME = "wrong_table"

random_treelist = FvsOutputTreeListRecord._random_treelist(100)


def test_sqlite_scrape():
    engine = db.create_engine("sqlite://", echo=False)  # an in-memory db
    df = pd.DataFrame(data=[[0, 1]], columns=["col1", "col2"])
    df.to_sql("a_table", engine)
    scraped = SqliteScraper._scrape_engine(engine)
    assert isinstance(scraped, dict)
    assert "a_table" in scraped
    assert isinstance(scraped["a_table"], pd.DataFrame)


def test_sqlite_scrape_dtype():
    engine = db.create_engine("sqlite://", echo=False)  # an in-memory db
    df = pd.DataFrame(data=[[0, 1]], columns=["col1", "col2"])
    df.to_sql("a_table", engine)
    scraped = SqliteScraper._scrape_engine(engine, dtype="Int64")
    assert scraped["a_table"]["col1"].dtype == "Int64"


def test_scrape_with_stand_stock(tmp_path):
    path_to_db = f"{tmp_path}/{FVS_DATABASE_NAME}"
    # create an in-memory SQLite DB to write data to
    engine = db.create_engine(f"sqlite:///{path_to_db}", echo=False)
    df = pd.DataFrame.from_records(random_treelist)
    df.to_sql(FvsOutputTableName.FVS_TREELIST, engine)
    # scrape the in-memory database
    scraped = FvsSqliteScraper.scrape(path_to_db)

    assert isinstance(scraped, dict)
    assert FvsOutputTableName.FVS_TREELIST in scraped
    assert FvsOutputTableName.FVS_STAND_STOCK in scraped
    stand_stock = scraped[FvsOutputTableName.FVS_STAND_STOCK]
    assert isinstance(stand_stock, pd.DataFrame)
    assert set(stand_stock.columns) == set(ALL_STAND_STOCK_COLUMNS)


def test_scrape_stand_stock_no_trees(tmp_path):
    path_to_db = f"{tmp_path}/{FVS_DATABASE_NAME}"
    # create an in-memory SQLite DB to write data to
    engine = db.create_engine(f"sqlite:///{path_to_db}", echo=False)
    df = pd.DataFrame.from_records(random_treelist)
    df.to_sql(WRONG_TABLE_NAME, engine)
    # scrape the in-memory database
    with pytest.warns(FvsStandStockWarning):
        scraped = FvsSqliteScraper.scrape(path_to_db)

    assert isinstance(scraped, dict)
    assert WRONG_TABLE_NAME in scraped
    assert FvsOutputTableName.FVS_STAND_STOCK in scraped
    stand_stock = scraped[FvsOutputTableName.FVS_STAND_STOCK]
    assert isinstance(stand_stock, pd.DataFrame)
    assert len(stand_stock) == 0
    assert set(stand_stock.columns) == set(ALL_STAND_STOCK_COLUMNS)
