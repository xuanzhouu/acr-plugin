# # -*- coding: utf-8 -*-
# """
# contam_simulation.py
# Generate flagged .prj files, run CONTAM engine, collect execution status.
# """
# import os, re, subprocess, logging
# from typing import List

# def generate_prj_files(csv_path: str, template_prj: str, output_dir: str) -> List[str]:
#     """For each row in csv_path, substitute flags in template_prj,
#     write sequential .prj files into output_dir. Return list of paths."""
#     # (refactor your generate_prj_files)
#     return prj_file_paths

# def run_contam_simulations(contamx_exe: str, prj_dir: str) -> None:
#     """Launch contamx_exe on each .prj in prj_dir."""
#     logging.basicConfig(filename=os.path.join(prj_dir, 'contamx.log'),
#                         level=logging.INFO, filemode='w')
#     # (refactor your run_contam_simulations)



# -*- coding: utf-8 -*-

import os
import csv
import re
import subprocess
import logging
import pandas as pd
import time

# ===============================
# GLOBAL ERROR LOG
# ===============================
ERROR_LOG = []

def log_error(step, error_msg, building_id=None):
    if building_id:
        ERROR_LOG.append(f"[{step}] Building {building_id}: {error_msg}")
    else:
        ERROR_LOG.append(f"[{step}] {error_msg}")
    print(f"ERROR: {ERROR_LOG[-1]}")



import os
import re
import glob

import os
import re
import glob
import pandas as pd


def generate_prj_files(csv_input, prj_filename, output_dir, tin_folder, weather_folder):

    print("\n==============================")
    print("START PRJ GENERATION")
    print("==============================")

    # DataFrame / CSV
    if isinstance(csv_input, pd.DataFrame):
        rows = csv_input.to_dict(orient="records")
        print("Input type: DataFrame")
    else:
        import csv
        with open(csv_input, 'r', encoding='utf-8') as csvfile:
            rows = list(csv.DictReader(csvfile))
        print("Input type: CSV")

    print(f"Total rows: {len(rows)}")

    if not rows:
        print("No rows found → no PRJ will be created")
        return

    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    created_files = 0


    for row_number, row in enumerate(rows, start=1):

        building_id = row.get("ID", f"row{row_number}")

        print("\n----------------------------------")
        print(f"Processing building: {building_id}")

        try:
            with open(prj_filename, 'r', encoding='utf-8', errors='ignore') as prjfile:
                prj_content = prjfile.read()

            quarter = str(row.get("Quarter", "")).strip()
            print(f"   Quarter: {quarter}")

            tin_path = ""
            wth_path = ""

            if quarter:

                tin_pattern = os.path.join(tin_folder, "**", f"*{quarter}.cvf")
                tin_matches = glob.glob(tin_pattern, recursive=True)

                print(f"   Searching Tin with pattern:")
                print(f"   {tin_pattern}")

                if tin_matches:
                    tin_path = tin_matches[0]

                    print(f"Tin found: {tin_path}")

                    if len(tin_matches) > 1:
                        print("Multiple Tin files found:")
                        for m in tin_matches:
                            print("      ", m)

                else:
                    print(f" Tin NOT FOUND for {quarter}")

                wth_pattern = os.path.join(weather_folder, f"{quarter}.wth")
                wth_matches = glob.glob(wth_pattern)

                print(f"   Searching Weather:")
                print(f"   {wth_pattern}")

                if wth_matches:
                    wth_path = wth_matches[0]
                    print(f"Weather found: {wth_path}")
                else:
                    print(f"Weather NOT FOUND for {quarter}")

            else:
                print("No Quarter value")

 
            row["Tin"] = tin_path
            row["Quarter_path"] = wth_path

            print("   Replacing tokens...")

            for column_name, value in row.items():

                pattern = f"@\\({column_name}\\)[^\\s]*"

                if value is None or str(value) == 'nan':
                    safe_val = "0"
                else:
                    safe_val = str(value)

                safe_val = safe_val.replace('\\', '\\\\')

                prj_content = re.sub(pattern, safe_val, prj_content)

            if "@(" in prj_content:
                print(f"   ⚠ WARNING: Unreplaced token in {building_id}.prj")

            prj_path = os.path.join(output_dir, f"{building_id}.prj")

            print(f"   Writing PRJ → {prj_path}")

            with open(prj_path, 'w', encoding='utf-8') as f:
                f.write(prj_content)

            created_files += 1
            print(f"Done")

        except Exception as e:
            print(f"ERROR: {e}")


    print("\n==============================")
    print("PRJ CREATION SUMMARY")
    print("==============================")
    print(f"Created: {created_files}/{len(rows)}")

def run_contam_simulations(contamx_path, prj_dir, verbose=False):
    logging.basicConfig(
        filename=os.path.join(prj_dir, "contamx.log"),
        level=logging.INFO,
        filemode='w'
    )

    if not os.path.isfile(contamx_path):
        log_error("CONTAM Simulation", f'Simulation engine "{contamx_path}" not found')
        return

    if not os.path.isdir(prj_dir):
        log_error("CONTAM Simulation", f'Directory "{prj_dir}" not found')
        return

    prj_list = []
    prj_list_noext = []

    for dirpath, dirnames, filenames in os.walk(prj_dir):
        for name in filenames:
            root, ext = os.path.splitext(name)
            if ext.lower() == ".prj":
                full_path = os.path.join(dirpath, name)
                prj_list.append(full_path)
                prj_list_noext.append(root)

    if not prj_list:
        log_error("CONTAM Simulation", "No .prj files found in directory")
        return

    print(f"\nProject files to process: {len(prj_list)} files")

    if verbose:
        for idx, path in enumerate(prj_list, start=1):
            print(f"  {idx}. {os.path.relpath(path, prj_dir)}")

    processes = []

    for prj_path in prj_list:
        cmd_list = [contamx_path, prj_path]
        cmd = f'"{contamx_path}" "{prj_path}"'
        print("Command line:", cmd)

        p = subprocess.Popen(cmd_list, shell=False)
        processes.append(p)

        logging.info(f"Launched: {cmd_list} (pid={p.pid})")

    successful_sims = 0
    failed_sims = 0

    for p in processes:
        ret = p.wait()

        msg = f"contamx p.wait(pid={p.pid}) = {ret}"
        print(msg)
        logging.info(msg)

        if ret == 0:
            successful_sims += 1
        else:
            failed_sims += 1
            log_error("CONTAM Simulation", f"Simulation failed with return code {ret}", f"pid_{p.pid}")

    print(f"\nCONTAM Simulation Summary:")
    print(f"  Successful: {successful_sims}")
    print(f"  Failed: {failed_sims}")
    print(f"  Total processed: {len(prj_list)}")


def combine_results(folder_path, output_file, csv_filename):
    try:
        data = {}

        header_names = []
        try:
            with open(csv_filename, 'r') as csvfile:
                csvreader = csv.reader(csvfile)
                next(csvreader)
                header_names = [int(row[0]) for row in csvreader]
        except Exception as e:
            log_error("Results Combination", f"Failed to read CSV file {csv_filename}: {str(e)}")
            return

        try:
            ach_files = sorted(
                [f for f in os.listdir(folder_path) if f.endswith('.ach')],
                key=lambda x: int(os.path.splitext(x)[0])
            )
        except Exception as e:
            log_error("Results Combination", f"Failed to list .ach files: {str(e)}")
            return

        if not ach_files:
            log_error("Results Combination", "No .ach files found")
            return

        first_col = []
        second_col = []
        all_last_cols = {}

        ach_file_map = {}
        for filename in ach_files:
            building_id = int(os.path.splitext(filename)[0])
            ach_file_map[building_id] = filename

        for idx, header_name in enumerate(header_names):
            if header_name not in ach_file_map:
                log_error("Results Combination", f"No .ach file for {header_name}")
                continue

            filename = ach_file_map[header_name]
            file_path = os.path.join(folder_path, filename)

            try:
                with open(file_path, 'r') as file:
                    lines = file.readlines()

                    date = []
                    time_ = []
                    last_col = []

                    for line in lines[2:]:
                        parts = line.split()
                        if len(parts) < 3:
                            continue

                        date.append(parts[0])
                        time_.append(parts[1])
                        last_col.append(float(parts[-1]))

                    if idx == 0:
                        first_col = date
                        second_col = time_

                    all_last_cols[f"ACR_{header_name}"] = last_col

            except Exception as e:
                log_error("Results Combination", f"Failed file {filename}: {str(e)}")

        df = pd.DataFrame({
            'date': first_col,
            'time': second_col,
            **all_last_cols
        })

        df.to_excel(output_file, index=False)
        print(f"Excel saved: {output_file}")

    except Exception as e:
        log_error("Results Combination", f"Unexpected error: {str(e)}")


def print_error_summary():
    if ERROR_LOG:
        print("\n=== ERROR SUMMARY ===")
        for i, error in enumerate(ERROR_LOG, 1):
            print(f"{i}. {error}")
    else:
        print("\nNo errors encountered")


# =========================================
# MAIN
# =========================================
def main():
    csv_filename = r"YOUR.csv"
    prj_filename = r"TEMPLATE.prj"
    output_dir = r"OUTPUT_PRJ"
    contamx_path = r"contamx.exe"
    output_excel = r"RESULT.xlsx"

    print("\n=== STEP 1: PRJ GENERATION ===")
    generate_prj_files(csv_filename, prj_filename, output_dir)

    print("\n=== STEP 2: CONTAM RUN ===")
    run_contam_simulations(contamx_path, output_dir)

    print("\n=== STEP 3: RESULT COMBINE ===")
    combine_results(output_dir, output_excel, csv_filename)

    print_error_summary()


# =========================================
# RUN
# =========================================
if __name__ == "__main__":
    start_time = time.time()
    main()
    end_time = time.time()

    print(f"\nExecution time: {time.strftime('%H:%M:%S', time.gmtime(end_time - start_time))}")