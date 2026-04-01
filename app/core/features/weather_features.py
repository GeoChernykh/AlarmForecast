import pandas as pd
from pathlib import Path


def add_region_ids(df, regions_path: str | Path = Path("data/alarms/regions.csv")) -> pd.DataFrame:
    if isinstance(regions_path, str):
        regions_path = Path(regions_path)

    if not regions_path.exists():
        raise FileNotFoundError(f"File not found on path {regions_path}.")
    
    regions = pd.read_csv(regions_path)
    result = df.merge(regions[["region_id", "city"]], how='left', on='city')
    result['region_id'] = result['region_id'].astype(int)

    return result


if __name__ == '__main__':
    add_region_ids(None)