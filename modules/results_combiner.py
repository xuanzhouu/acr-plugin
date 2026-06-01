# # -*- coding: utf-8 -*-
# """
# results_combiner.py
# Combine hourly .ach outputs into a single Excel per building.
# """
# import os, csv, pandas as pd
# from typing import List

# def combine_hourly_results(folder: str, header_csv: str, output_excel: str) -> pd.DataFrame:
#     """
#     Reads all .ach in folder (number‐sorted), uses first-column of header_csv
#     as column labels, writes output_excel. Returns final DataFrame.
#     """
#     # (refactor your combine_results)
#     return df

# -*- coding: utf-8 -*-
import os, pandas as pd

def combine_hourly_results(prj_dir, wide_df, output_excel):
    results = {}
    time_index = None
    bids = wide_df['ID'].astype(str).tolist()

    for bid in bids:
        ach_file = os.path.join(prj_dir, f"{bid}.ach")
        if not os.path.exists(ach_file): continue

        try:
            with open(ach_file, 'r') as f:
                lines = f.readlines()[2:]
                dates, times, values = [], [], []
                for ln in lines:
                    p = ln.split()
                    if len(p) >= 3:
                        dates.append(p[0])
                        times.append(p[1])
                        values.append(float(p[-1]))
                
                if time_index is None:
                    time_index = pd.DataFrame({'Date': dates, 'Time': times})
                results[f"ACR_{bid}"] = values
        except:
            continue

    if results:
        df_final = pd.concat([time_index, pd.DataFrame(results)], axis=1)
        df_final.to_excel(output_excel, index=False)
        return df_final
    return None