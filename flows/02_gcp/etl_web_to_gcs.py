from random import randint
from pathlib import Path
import pandas as pd
from prefect import flow, task
from prefect_gcp.cloud_storage import GcsBucket


@task(retries=3)
def fetch(dataset_url: str) -> pd.DataFrame:
    """Read data from web into pandas DataFrame"""
    # create an artificial failure to show value of retries
    # if randint(0, 1) > 0:
    #     raise Exception

    df = pd.read_csv(dataset_url)
    return df


@task(log_prints=True)
def clean(df=pd.DataFrame) -> pd.DataFrame:
    """Fix dtype issues"""  # learned of from exploring in a Jupyter notebook
    df["tpep_pickup_datetime"] = pd.to_datetime(df["tpep_pickup_datetime"])
    df["tpep_dropoff_datetime"] = pd.to_datetime(df["tpep_dropoff_datetime"])
    print(df.head(2))
    print(f"columns: {df.dtypes}")
    print(f"rows: {len(df)}")
    return df


@task()
def write_local(
    df: pd.DataFrame, color: str, base_path: str, dataset_file: str
) -> Path:
    """Write DataFrame to local parquet file"""
    end_path = Path(f"{color}/{dataset_file}.parquet")
    df.to_parquet(f"{base_path}/{end_path}", compression="gzip")
    return end_path


@task()
def write_gcs(path: Path, color: str) -> None:
    """Upload local parquet file to GCS"""
    gcs_block = GcsBucket.load("zoom-gcs")
    gcs_block.upload_from_path(
        from_path=f"data/{path}",
        to_path=path,
    )
    return


@flow()
def etl_web_to_gcs() -> None:
    """The main extract, transform, and load function"""
    color = "yellow"
    year = 2021
    month = 1
    dataset_file = f"{color}_tripdata_{year}-{month:02}"  # adds leading 0 if needed
    dataset_url = f"https://github.com/DataTalksClub/nyc-tlc-data/releases/download/{color}/{dataset_file}.csv.gz"
    base_path = "/Users/jeffhale/Desktop/prefect/prefect-zoomcamp/data"  # insert absolute path to your data folder

    df = fetch(dataset_url)
    df_clean = clean(df)
    path = write_local(df_clean, color, base_path, dataset_file)
    write_gcs(path, color)
    return


if __name__ == "__main__":
    etl_web_to_gcs()
