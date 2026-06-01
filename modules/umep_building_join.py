# -*- coding: utf-8 -*-

import processing
from qgis.core import QgsVectorLayer, QgsProject
from typing import Tuple

def join_umep_to_grid(grid_lyr: QgsVectorLayer, umep_csv: str, grid_id_field: str) -> QgsVectorLayer:
    params = {
        'INPUT': grid_lyr,
        'INPUT_2': umep_csv,
        'FIELD': grid_id_field,
        'FIELD_2': 'Pixel_ID',
        'OUTPUT': 'memory:umep_grid'
    }
    out = processing.run("native:joinattributestable", params)['OUTPUT']
    QgsProject.instance().addMapLayer(out)
    return out

def spatially_average_to_buildings(grid_with_umep: QgsVectorLayer, bld_lyr: QgsVectorLayer) -> QgsVectorLayer:
    params = {
        'INPUT': bld_lyr,
        'JOIN': grid_with_umep,
        'PREDICATE': [0],  # intersects
        'SUMMARIES': [2],  # mean
        'OUTPUT': 'memory:bld_umep'
    }
    out = processing.run("native:joinattributesbylocation", params)['OUTPUT']
    QgsProject.instance().addMapLayer(out)
    return out
