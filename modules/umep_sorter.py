# -*- coding: utf-8 -*-

import os, re, time
import pandas as pd
from typing import Tuple

def sort_umep_data(input_folder: str, output_csv: str) -> Tuple[pd.DataFrame, float]:
    """Read every .txt in input_folder, pivot zd & z0 by Wd into columns,
    write to output_csv, return (df, elapsed_seconds)."""
    start = time.time()
    txts = [f for f in os.listdir(input_folder) if f.endswith('.txt')]
    rows = []
    for fn in txts:
        m = re.search(r'(\d+)\.txt$', fn)
        pid = m.group(1) if m else fn[:-4]
        df = pd.read_csv(os.path.join(input_folder, fn), delim_whitespace=True)
        row = {'Pixel_ID': pid}
        for _, rec in df.iterrows():
            wd = int(rec['Wd'])
            row[f'zd_{wd}'], row[f'z0_{wd}'] = rec['zd'], rec['z0']
        rows.append(row)
    result = pd.DataFrame(rows)
    result.to_csv(output_csv, index=False)
    return result, time.time() - start
