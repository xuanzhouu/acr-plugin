# # -*- coding: utf-8 -*-
# """
# wind_modifiers.py
# Compute wind‐speed modifier profiles per building.
# """
# import os, time, csv, math, statistics
# from collections import defaultdict
# from typing import Tuple
# import pandas as pd

# def process_wind_modifiers(building_csv: str, weather_wth: str, output_folder: str)\
#         -> Tuple[pd.DataFrame, pd.DataFrame, float]:
#     """
#     Reads building_csv (with zd_* & z0_* columns) and a .wth weather file,
#     computes narrow & wide modifier tables, writes them to Excel in output_folder,
#     returns (narrow_df, wide_df, elapsed_seconds).
#     """
#     start = time.time()
#     # --- load weather and building data ---
#     # (refactor your existing code here)
#     # --- calculate modifiers_s3 dict, build narrow_df + wide_df ---
#     # narrow_df.to_excel(os.path.join(output_folder, 'modifiers_narrow.xlsx'), index=False)
#     # wide_df.to_excel(os.path.join(output_folder, 'modifiers_wide.xlsx'), index=False)
#     return narrow_df, wide_df, time.time() - start


# -*- coding: utf-8 -*-

import os
import csv
import math
import time
from collections import defaultdict
import statistics
import pandas as pd


# =========================================
# SUPPORT FUNCTIONS
# =========================================
def try_float(x):
    try:
        return float(x)
    except:
        return 0.0


def get_angle_diff(a, b):
    d = abs(a - b)
    return min(d, 360 - d)


def determine_wind_building_relationship(wind_dir, building_angle):
    angle_diff = get_angle_diff(wind_dir, building_angle)
    if angle_diff <= 45 or angle_diff >= 135:
        return 'parallel'
    else:
        return 'perpendicular'


def get_z0_from_wind_direction(building_data, wind_dir):
    wind_dir = wind_dir % 360

    if (wind_dir >= 0 and wind_dir < 15) or (wind_dir >= 345 and wind_dir <= 360):
        z0_column = 'z0_0'
    elif wind_dir >= 15 and wind_dir < 45:
        z0_column = 'z0_30'
    elif wind_dir >= 45 and wind_dir < 75:
        z0_column = 'z0_60'
    elif wind_dir >= 75 and wind_dir < 105:
        z0_column = 'z0_90'
    elif wind_dir >= 105 and wind_dir < 135:
        z0_column = 'z0_120'
    elif wind_dir >= 135 and wind_dir < 165:
        z0_column = 'z0_150'
    elif wind_dir >= 165 and wind_dir < 195:
        z0_column = 'z0_180'
    elif wind_dir >= 195 and wind_dir < 225:
        z0_column = 'z0_210'
    elif wind_dir >= 225 and wind_dir < 255:
        z0_column = 'z0_240'
    elif wind_dir >= 255 and wind_dir < 285:
        z0_column = 'z0_270'
    elif wind_dir >= 285 and wind_dir < 315:
        z0_column = 'z0_300'
    elif wind_dir >= 315 and wind_dir < 345:
        z0_column = 'z0_330'
    else:
        z0_column = 'z0_0'

    return try_float(building_data.get(z0_column))


def load_weather_data(weather_file_path):
    if not os.path.exists(weather_file_path):
        raise FileNotFoundError(weather_file_path)

    weather_data = []
    with open(weather_file_path, newline='', encoding='ISO-8859-1') as f:
        reader = csv.reader(f, delimiter='\t')
        header_found = False

        for row in reader:
            row = [c.strip() for c in row]

            if not header_found and all(k in row for k in ("Ws [m/s]", "Wd [deg]", "Ta [K]")):
                header_found = True
                headers = row
                continue

            if header_found and len(row) == len(headers):
                weather_data.append(dict(zip(headers, row)))

    return weather_data


# =========================================
# MAIN FUNCTION
# =========================================
def process_wind_modifiers(building_file, weather_folder, facade_temp_file, output_folder):

    t0 = time.time()

    debug_dir = os.path.join(output_folder, "DEBUG_PER_BUILDING")
    os.makedirs(debug_dir, exist_ok=True)

    width_map = {'LL': 46, 'MM': 17, 'NN': 12}

    # buildings
    encodings_to_try = ['utf-8', 'windows-1252', 'latin-1', 'iso-8859-1']
    buildings = []

    for encoding in encodings_to_try:
        try:
            with open(building_file, newline='', encoding=encoding) as f:
                buildings = []
                for row in csv.DictReader(f):
                    row['UC_width'] = width_map.get(row.get('UC'), try_float(row.get('UC')))
                    row['CO_width'] = width_map.get(row.get('CO'), try_float(row.get('CO')))
                    buildings.append(row)
            break
        except:
            continue

    if not buildings:
        raise Exception("Cannot read building file")

    # facade temps
    facade_temps = pd.read_csv(facade_temp_file)
    facade_temps.columns = facade_temps.columns.map(str)
    facade_temps = facade_temps.set_index(facade_temps.columns[0])

    modifiers = defaultdict(lambda: defaultdict(list))

    processed = 0
    skipped = 0

    for b in buildings:

        bid = str(b['ID'])
        quarter = b['Quarter']
        wth_path = os.path.join(weather_folder, f"{quarter}.wth")

        try:
            weather_data = load_weather_data(wth_path)
        except:
            skipped += 1
            continue

        z_roof = try_float(b['refHt_roof'])
        z_pts = [0.25*z_roof, 0.75*z_roof, 0.25*z_roof, 0.75*z_roof]

        b_angle = try_float(b['B_angle'])
        pos = b['B_position']

        if pos == 'L':
            canyon_az = (b_angle + 90) % 360
            court_az = (270 + b_angle) % 360
        elif pos == 'R':
            canyon_az = (270 + b_angle) % 360
            court_az = (90 + b_angle) % 360
        elif pos == 'T':
            canyon_az = (b_angle + 90) % 360
            court_az = (b_angle - 90) % 360
        elif pos == 'D':
            canyon_az = (b_angle - 90) % 360
            court_az = (b_angle + 90) % 360
        else:
            canyon_az = (b_angle + 90) % 360
            court_az = (b_angle - 90) % 360

        debug_rows = []

        for i, wd in enumerate(weather_data):

            Ws = try_float(wd['Ws [m/s]'])
            Wdir = try_float(wd['Wd [deg]'])
            Tout = try_float(wd['Ta [K]']) - 273.15

            try:
                Tsurf = try_float(facade_temps.iloc[i][bid])
            except:
                Tsurf = Tout

            DT = Tsurf - Tout

            rel = determine_wind_building_relationship(Wdir, b_angle)
            z0 = get_z0_from_wind_direction(b, Wdir)

            ang_c = min(abs(Wdir - canyon_az), 360 - abs(Wdir - canyon_az))
            ang_o = abs(Wdir - court_az)

            ws_c = Ws * math.cos(math.radians(ang_c))
            ws_o = Ws * math.cos(math.radians(ang_o))

            # 
            if Ws <= 4:
                Vs = [
                    math.copysign(1,ws_c)*abs(-0.537+0.957*z_pts[0]/b['UC_width']-0.012*abs(DT)+0.0039*ws_c),
                    math.copysign(1,ws_c)*abs(-0.537+0.957*z_pts[1]/b['UC_width']-0.012*abs(DT)+0.0039*ws_c),
                    math.copysign(1,ws_o)*abs(-0.537+0.957*z_pts[2]/b['CO_width']-0.012*abs(DT)+0.0039*ws_o),
                    math.copysign(1,ws_o)*abs(-0.537+0.957*z_pts[3]/b['CO_width']-0.012*abs(DT)+0.0039*ws_o),
                ]

            elif rel == 'parallel':
                Avg_Hbld = try_float(b['Avg_Hbld'])
                z2 = 0.1*(Avg_Hbld**2)/z0 if z0>0 else 1.0
                Vlow = Ws*math.exp(z_pts[0]/z2)
                Vup = Ws*math.exp(z_pts[1]/z2)

                Vs = [
                    Vlow*math.cos(math.radians(ang_c)),
                    Vup*math.cos(math.radians(ang_c)),
                    Vlow*math.cos(math.radians(ang_o)),
                    Vup*math.cos(math.radians(ang_o))
                ]

            else:
                Avg_Hbld = try_float(b['Avg_Hbld'])

                k_uc = math.pi/b['UC_width']
                k_co = math.pi/b['CO_width']

                B_uc = math.exp(-2*k_uc*Avg_Hbld)
                B_co = math.exp(-2*k_co*Avg_Hbld)

                A_uc = (k_uc*Ws)/(1-B_uc) if B_uc!=1 else 0
                A_co = (k_co*Ws)/(1-B_co) if B_co!=1 else 0

                def h(a,k,beta,z):
                    dz = z-Avg_Hbld
                    return (a/k)*(math.exp(k*dz)*(1+k*dz)-beta*math.exp(-k*dz)*(1-k*dz))

                u1 = h(A_uc,k_uc,B_uc,z_pts[0])*math.sin(k_uc*(b['UC_width']/2))
                u2 = h(A_uc,k_uc,B_uc,z_pts[1])*math.sin(k_uc*(b['UC_width']/2))
                u3 = h(A_co,k_co,B_co,z_pts[2])*math.sin(k_co*(b['CO_width']/2))
                u4 = h(A_co,k_co,B_co,z_pts[3])*math.sin(k_co*(b['CO_width']/2))

                Vs = [
                    u1*math.cos(math.radians(ang_c)),
                    u2*math.cos(math.radians(ang_c)),
                    u3*math.cos(math.radians(ang_o)),
                    u4*math.cos(math.radians(ang_o))
                ]

            Ms = [
                0.0 if Ws==0 else (
                    math.copysign(1,v)*((abs(v)/Ws)**2) if i<2
                    else math.copysign(1,v)*-1*((abs(v)/Ws)**2)
                )
                for i,v in enumerate(Vs)
            ]

            wd_bin = int((round((canyon_az-Wdir)/30)*30)%360)

            for pt,m in enumerate(Ms,1):
                modifiers[bid][(wd_bin,pt)].append(m)

        processed += 1


    rows = []

    for bid, wd_dict in modifiers.items():

        building_data = next(b for b in buildings if int(b['ID'])==int(bid))

        row = {}

        for k,v in building_data.items():
            if not (k.startswith('z0_') or k.startswith('zd_')):
                row[k] = v

        for pt in range(1,5):
            for d in range(0,361,30):
                key = (0 if d==360 else d, pt)
                vals = wd_dict.get(key,[])
                row[f'm{pt}_{d}'] = round(statistics.mean(vals),6) if vals else None

        rows.append(row)

    wide_df = pd.DataFrame(rows)

    os.makedirs(output_folder, exist_ok=True)
    wide_path = os.path.join(output_folder, "wind_modifiers_wide.csv")
    wide_df.to_csv(wide_path, index=False)

    print(f"\nProcessed: {processed}, Skipped: {skipped}")
    print(f"Saved: {wide_path}")
    print(f"Time: {round(time.time()-t0,2)} s")

    return wide_df, time.time()-t0