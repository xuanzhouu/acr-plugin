# -*- coding: utf-8 -*-
"""
/***************************************************************************
 BuildingACR

 Hourly building air change rate simulation using CONTAM and the effect of 
 local urban morphology on wind speed correction usiogn UMEP results.

                    first version:          2026-03-24
                    email:                  yasemin.usta@polito.it; xuan.zhou@polito.it; guglielmina.mutani@polito.it

 ***************************************************************************/
"""

import os
import csv

from qgis.PyQt.QtCore import QCoreApplication
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtWidgets import QAction, QDialog, QFileDialog, QMessageBox
from qgis.core import QgsProject, QgsVectorLayer, Qgis
from qgis.PyQt import uic

from .modules.wind_modifiers    import process_wind_modifiers
from .modules.contam_simulation import generate_prj_files, run_contam_simulations
from .modules.results_combiner  import combine_hourly_results


# =========================
# UI Dialog
# =========================
class BuildingACRDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)

        ui_path = os.path.join(os.path.dirname(__file__), 'Building_ACR_dialog_base.ui')
        uic.loadUi(ui_path, self)

        # buttons
        self.btnRun.clicked.connect(self.accept)
        self.btnBrowseWeatherFolder.clicked.connect(self.select_weather_folder)
        self.btnBrowseFacadeTemp.clicked.connect(self.select_facade_temp)
        self.btnBrowseOutputFolder.clicked.connect(self.select_output)
        self.btnBrowseTinFolder.clicked.connect(self.select_tin_folder)

    def select_weather_folder(self):
        d = QFileDialog.getExistingDirectory(self, "Select Weather Folder (.wth)")
        if d:
            self.lineEditWeatherFolder.setText(d)

    def select_facade_temp(self):
        f, _ = QFileDialog.getOpenFileName(self, "Select Facade Temp CSV", "", "CSV (*.csv)")
        if f:
            self.lineEditFacadeTemp.setText(f)

    def select_output(self):
        d = QFileDialog.getExistingDirectory(self, "Select Output Folder")
        if d:
            self.lineEditOutputFolder.setText(d)

    def select_tin_folder(self):
        d = QFileDialog.getExistingDirectory(self, "Select Tin folder (.cvf)")
        if d:
            self.lineEditTinFolder.setText(d)


# =========================
# Main Plugin
# =========================
class BuildingACR:
    def __init__(self, iface):
        self.iface = iface
        self.plugin_dir = os.path.dirname(__file__)
        self.dlg = BuildingACRDialog(iface.mainWindow())
        self.actions = []
        self.menu = u'&Building ACR'

    def tr(self, msg):
        return QCoreApplication.translate('BuildingACR', msg)

    def add_action(self, icon_path, text, callback, parent):
        icon = QIcon(icon_path)
        action = QAction(icon, text, parent)
        action.triggered.connect(callback)

        self.iface.addToolBarIcon(action)
        self.iface.addPluginToMenu(self.menu, action)

        self.actions.append(action)
        return action

    def initGui(self):
        icon_path = os.path.join(self.plugin_dir, 'icon.png')

        self.add_action(
            icon_path,
            self.tr('Run ACR Workflow'),
            self.run,
            self.iface.mainWindow()
        )

    def unload(self):
        for action in self.actions:
            self.iface.removePluginMenu(self.menu, action)
            self.iface.removeToolBarIcon(action)

    def populate_layers(self):
        self.dlg.comboBuildingLayer.clear()

        for lyr in QgsProject.instance().mapLayers().values():
            if isinstance(lyr, QgsVectorLayer):
                self.dlg.comboBuildingLayer.addItem(lyr.name(), lyr.id())

    # =========================
    # MAIN RUN
    # =========================
    def run(self):
        self.populate_layers()
        self.dlg.show()

        if self.dlg.exec_() != QDialog.Accepted:
            return

        # -------- inputs --------
        weather_folder = self.dlg.lineEditWeatherFolder.text().strip()
        facade_temp    = self.dlg.lineEditFacadeTemp.text().strip()
        tin_folder     = self.dlg.lineEditTinFolder.text().strip()
        output_dir     = self.dlg.lineEditOutputFolder.text().strip()
        simulator      = self.dlg.comboSimulator.currentText()

        layer_id  = self.dlg.comboBuildingLayer.currentData()
        bld_layer = QgsProject.instance().mapLayer(layer_id)

        # -------- checks --------
        if not bld_layer:
            self.iface.messageBar().pushCritical("Error", "Invalid building layer.")
            return

        if not os.path.isdir(weather_folder):
            self.iface.messageBar().pushCritical("Error", "Invalid weather folder.")
            return

        if not os.path.isdir(tin_folder):
            self.iface.messageBar().pushCritical("Error", "Invalid Tin folder.")
            return

        if not os.path.isfile(facade_temp):
            self.iface.messageBar().pushCritical("Error", "Invalid facade temperature file.")
            return

        os.makedirs(output_dir, exist_ok=True)

        try:
            # =========================
            # STEP 1: Export building CSV
            # =========================
            self.iface.messageBar().pushMessage("ACR", "Preparing building data...", level=Qgis.Info)

            building_csv = os.path.join(output_dir, "buildings_temp.csv")

            fields = [f.name() for f in bld_layer.fields()]

            with open(building_csv, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(fields)

                for feat in bld_layer.getFeatures():
                    writer.writerow(feat.attributes())

            # =========================
            # STEP 2: Wind Modifiers
            # =========================
            self.iface.messageBar().pushMessage("ACR", "Computing wind modifiers...", level=Qgis.Info)

            mod_dir = os.path.join(output_dir, 'modifiers')
            os.makedirs(mod_dir, exist_ok=True)

            wide_df, t_mod = process_wind_modifiers(
                building_csv,
                weather_folder,
                facade_temp,
                mod_dir
            )

            # =========================
            # STEP 3: CONTAM / Simulator
            # =========================
            if simulator == "CONTAM":

                self.iface.messageBar().pushMessage("ACR", "Running CONTAM...", level=Qgis.Info)

                prj_dir = os.path.join(output_dir, 'prj_files')
                os.makedirs(prj_dir, exist_ok=True)

                template = os.path.join(self.plugin_dir, 'templates', 'flagged.prj')
                exe_path = os.path.join(self.plugin_dir, 'bin', 'contamx3.exe')

                # 关键：传 Tin + Weather folder
                generate_prj_files(
                    wide_df,
                    template,
                    prj_dir,
                    tin_folder,
                    weather_folder
                )

                run_contam_simulations(exe_path, prj_dir)

            else:
                QMessageBox.warning(None, "Not Implemented", "3ZLPM not implemented yet.")
                return

            # =========================
            # STEP 4: Results
            # =========================
            final_excel = os.path.join(output_dir, 'Building_Hourly_ACR_Results.xlsx')

            combine_hourly_results(prj_dir, wide_df, final_excel)

            self.iface.messageBar().pushMessage(
                "Success", f"Results saved: {final_excel}", level=Qgis.Success
            )

        except Exception as e:
            QMessageBox.critical(None, "Error", str(e))