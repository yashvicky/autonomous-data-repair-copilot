import duckdb
import polars as pl
from pydantic import BaseModel


class ExampleRecord(BaseModel):
    customer_id: str


def test_python_data_stack() -> None:
    frame = pl.DataFrame({"customer_id": ["001", "002"]})
    assert frame.height == 2
    assert frame["customer_id"][0] == "001"

    with duckdb.connect(":memory:") as connection:
        result = connection.sql("SELECT 1").fetchone()
    assert result is not None
    assert result[0] == 1

    record = ExampleRecord(customer_id="001")
    assert record.customer_id == "001"
