# -*- coding: utf-8 -*-
"""
/***************************************************************************
 BuildingACR
                                 A QGIS plugin
 This script initializes the plugin, making it known to QGIS.
 ***************************************************************************/
"""

def classFactory(iface):
    """
    :param iface: A QGIS interface instance.
    :type iface: QgsInterface
    """
    from .building_acr import BuildingACR
    return BuildingACR(iface)
