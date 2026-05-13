import os
import sys
import shlex
import subprocess
import numpy as np
import matplotlib.pyplot as plt
from astropy.io import fits
from matplotlib.colors import LogNorm
import shutil

from PySide6.QtCore import Qt
from PySide6.QtGui import QAction
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QDialog,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMenu,
    QMessageBox,
    QPushButton,
    QProgressBar,
    QSlider,
    QSplitter,
    QToolButton,
    QVBoxLayout,
    QWidget,
    QSpinBox,
    QDoubleSpinBox
)

from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qtagg import NavigationToolbar2QT as NavigationToolbar
from matplotlib.figure import Figure
from matplotlib.widgets import SpanSelector


CUBEX_ACTIONS = {
    "CubePSFSub": {
        "executable": "Tools/CubePSFSub",
        "suffix": "_PSFSub.fits",
        "params": {
            "x": "",
            "y": "",
            "nbins": "-1",
            "zPSFsize": "150",
            "rmin": "1",
            "rmax": "25",
            "recenter": ".true.",
            "maskpix": "",
            "withvar": ".true.",
        },
    },
    "CubeBKGSub": {
        "executable": "Tools/CubeBKGSub",
        "suffix": "_BKGSub.fits",
        "params": {
            "bpsize": "1 1 45",
            "bfrad": "0 0 2",
            "maskpix": "",
        },
    },
    "CubeSel": {
        "executable": "Tools/CubeSel",
        "suffix": "_CubeSel.fits",
        "params": {
            "zmin": "",
            "zmax": "",
        },
    },
    "Cube2Im": {
        "executable": "Tools/Cube2Im",
        "suffix": "_IM.fits",
        "params": {},
    },
    "Cube2Spc": {
        "executable": "Tools/Cube2Spc",
        "suffix": "_SPC.fits",
        "params": {
            "idcube": "",
            "id": "",
            "smoothr": "2",
        },
    },
    "CubeReplace": {
        "executable": "Tools/CubeReplace",
        "suffix": "_replaced.fits",
        "params": {
            "oldval": "",
            "newval": "",
        },
    },
    "CubEx": {
        "executable": "CubEx",
        "suffix": "",
        "use_parameter_file": True,
        "params": {
            "InpFile": "",
            "Catalogue": "",
            "VarFile": "",
            "ApplyFilter": ".true.",
            "ApplyFilterVar": ".true.",
            "FilterXYRad": "2",
            "FilterZRad": "0",
            "SN_Threshold": "3",
            "MinNSpax": "1000",
            "NCheckCubes": "2",
            "CheckCubeType": '"Objects_Id" "Objects_SNR_F"',
            "SourceMask": "",
            "UnMask": "",
            "XYedge": "10",
            "LayerMaskList": "",
        },
    },

    "CreateMask": {
        "special": True,
        "params": {
            "input_image": "",
            "output_mask": "SourceMask.fits",
            "MultiExt": ".false.",
            "ApplyFilter": ".true.",
            "ApplyFilterVar": ".true.",
            "FilterXYRad": "1",
            "SN_Threshold": "5",
            "MinNVox": "80",
        },
    },

    "Binarize3DMask": {
        "special": True,
        "params": {
            "mask3d": "",
            "selected_id": "",
        },
    },

    "CreateMaps": {
        "special": True,
        "params": {
            "cube": "",
            "mask3d": "",
            "SBmap": "",
            "KinMap": "",
            "id": "1",
            "idpad": "-1",
            "nl": "-1",
            "nlpad": "3",
            "gsm": "1",
            "sbscale": ".true.",
            "nl2": "0",
            "nlpad2": "0",
            "gsm2": "2",
            "vzero": "",
        },
    },
}


def safe_column_name(name):
    """Return a FITS-table-safe column name."""
    out = str(name).replace("-", "_").replace(" ", "_").replace("/", "_")
    out = out.replace(".", "_").replace(":", "_")
    return out[:60]


def infer_value_dtype(value):
    """Infer a simple dtype for values saved in the action registry."""
    if value is None:
        return "U256"

    txt = str(value).strip()

    if txt == "":
        return "U256"

    try:
        float(txt)
        return "float64"
    except Exception:
        return "U256"


def convert_value_for_table(value, dtype):
    """Convert value before writing into an astropy Table cell."""
    if dtype == "float64":
        try:
            return float(value)
        except Exception:
            return np.nan

    if value is None:
        return ""

    return str(value)


class CubeViewer(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("AutomatiCubEx - Cube Viewer")

        self.cube = None
        self.header = None
        self.cube_path = None
        self.current_z = 0
        self.wave = None

        self.selected_x = None
        self.selected_y = None

        self.spec_min = None
        self.spec_max = None
        self.image_mode = "slice"
        self.aperture_radius = 0.0

        self.cubex_root = None
        self.registry_table_path = None

        self.loaded_files = {}

        self.image_xlim = None
        self.image_ylim = None
        self.spectrum_xlim = None
        self.spectrum_ylim = None

        self._updating_image_limits = False
        self._updating_spectrum_limits = False

        self._build_ui()

    def _build_ui(self):
        main_widget = QWidget()
        main_layout = QHBoxLayout(main_widget)

        left_layout = QVBoxLayout()
        right_layout = QVBoxLayout()
        right_panel = QWidget()
        right_panel_layout = QVBoxLayout(right_panel)
        right_panel.setFixedWidth(340)

        self.open_button = QPushButton("Load FITS cube")
        self.open_button.clicked.connect(self.open_cube)

        self.open_extra_button = QPushButton("Open another FITS")
        self.open_extra_button.clicked.connect(self.open_cube)

        self.reload_button = QPushButton("Reload current")
        self.reload_button.clicked.connect(self.reload_current_cube)

        self.remove_loaded_button = QPushButton("Remove selected")
        self.remove_loaded_button.clicked.connect(self.remove_selected_loaded_file)

        self.cubex_path_button = QPushButton("Set CubEx path")
        self.cubex_path_button.clicked.connect(self.select_cubex_path)

        self.table_button = QPushButton("Set action table")
        self.table_button.clicked.connect(self.select_registry_table)

        self.cube_selector = QComboBox()
        self.cube_selector.currentTextChanged.connect(self.switch_loaded_file)

        self.cubex_path_label = QLabel("CubEx path: not set")
        self.table_label = QLabel("Action table: not set")
        self.info_label = QLabel("No cube loaded")

        self.load_progress = QProgressBar()
        self.load_progress.setRange(0, 100)
        self.load_progress.setValue(0)

        top_bar_1 = QHBoxLayout()
        top_bar_1.addWidget(self.open_button)
        top_bar_1.addWidget(self.open_extra_button)
        top_bar_1.addWidget(self.reload_button)
        top_bar_1.addWidget(self.remove_loaded_button)

        top_bar_2 = QHBoxLayout()
        top_bar_2.addWidget(QLabel("Loaded file"))
        top_bar_2.addWidget(self.cube_selector)

        top_bar_3 = QHBoxLayout()
        top_bar_3.addWidget(self.cubex_path_button)
        top_bar_3.addWidget(self.table_button)

        self.image_fig = Figure(figsize=(9, 7), constrained_layout=True)
        self.image_canvas = FigureCanvas(self.image_fig)
        self.image_toolbar = NavigationToolbar(self.image_canvas, self)
        self.image_ax = self.image_fig.add_subplot(111)
        self.image_canvas.mpl_connect("button_press_event", self.on_image_click)

        self.image_ax.callbacks.connect("xlim_changed", self.on_image_limits_changed)
        self.image_ax.callbacks.connect("ylim_changed", self.on_image_limits_changed)

        self.z_slider = QSlider(Qt.Horizontal)
        self.z_slider.setMinimum(0)
        self.z_slider.setMaximum(0)
        self.z_slider.valueChanged.connect(self.update_slice_from_slider)

        self.z_label = QLabel("z = 0")

        z_bar = QHBoxLayout()
        z_bar.addWidget(QLabel("Spectral slice"))
        z_bar.addWidget(self.z_slider)
        z_bar.addWidget(self.z_label)

        self.spectrum_fig = Figure(figsize=(9, 2.8), constrained_layout=True)
        self.spectrum_canvas = FigureCanvas(self.spectrum_fig)
        self.spectrum_toolbar = NavigationToolbar(self.spectrum_canvas, self)
        self.spectrum_ax = self.spectrum_fig.add_subplot(111)

        self.spectrum_ax.callbacks.connect("xlim_changed", self.on_spectrum_limits_changed)
        self.spectrum_ax.callbacks.connect("ylim_changed", self.on_spectrum_limits_changed)

        self.span_selector = SpanSelector(
            self.spectrum_ax,
            self.on_spectral_region_selected,
            "horizontal",
            useblit=True,
            props=dict(alpha=0.25),
            interactive=True,
            drag_from_anywhere=True,
        )

        image_widget = QWidget()
        image_layout = QVBoxLayout(image_widget)
        image_layout.setContentsMargins(0, 0, 0, 0)
        image_layout.addWidget(self.image_toolbar)
        image_layout.addWidget(self.image_canvas)

        spectrum_widget = QWidget()
        spectrum_layout = QVBoxLayout(spectrum_widget)
        spectrum_layout.setContentsMargins(0, 0, 0, 0)
        spectrum_layout.addWidget(self.spectrum_toolbar)
        spectrum_layout.addWidget(self.spectrum_canvas)

        viewer_splitter = QSplitter(Qt.Vertical)
        viewer_splitter.addWidget(image_widget)
        viewer_splitter.addWidget(spectrum_widget)
        viewer_splitter.setSizes([850, 250])

        left_layout.addWidget(viewer_splitter)
        left_layout.addLayout(z_bar)
        
        files_box = QGroupBox("Project / Files")
        files_layout = QVBoxLayout(files_box)

        files_layout.addLayout(top_bar_1)
        files_layout.addLayout(top_bar_2)
        files_layout.addLayout(top_bar_3)

        files_layout.addWidget(self.cubex_path_label)
        files_layout.addWidget(self.table_label)
        files_layout.addWidget(self.info_label)
        files_layout.addWidget(self.load_progress)

        actions_box = QGroupBox("Actions")
        actions_layout = QVBoxLayout(actions_box)

        self.image_mode_combo = QComboBox()
        self.image_mode_combo.addItems(["slice", "mean selected region", "median selected region"])
        self.image_mode_combo.currentTextChanged.connect(self.change_image_mode)

        self.apply_region_button = QPushButton("Apply selected spectral region")
        self.apply_region_button.clicked.connect(lambda: self.update_image(keep_zoom=True))

        self.actions_button = QToolButton()
        self.actions_button.setText("Actions")
        self.actions_button.setPopupMode(QToolButton.InstantPopup)

        actions_menu = QMenu(self.actions_button)
        for action_name in CUBEX_ACTIONS:
            action = QAction(action_name, self)
            action.triggered.connect(lambda checked=False, name=action_name: self.open_action_dialog(name))
            actions_menu.addAction(action)

        self.actions_button.setMenu(actions_menu)

        self.selection_label = QLabel("Selected spectral region: none")
        self.source_label = QLabel("Selected source: none")
        self.output_label = QLabel("Last output: none")
        self.current_values_label = QLabel("Current values: z = none | lambda = none | x = none | y = none")
        
        self.aperture_radius_box = QDoubleSpinBox()
        self.aperture_radius_box.setMinimum(0.0)
        self.aperture_radius_box.setMaximum(500.0)
        self.aperture_radius_box.setSingleStep(1.0)
        self.aperture_radius_box.setValue(0.0)
        self.aperture_radius_box.setSuffix(" pix")
        self.aperture_radius_box.valueChanged.connect(self.update_aperture_radius)

        self.aperture_label = QLabel("Aperture radius for spectrum")

        actions_layout.addWidget(QLabel("Image extraction mode"))
        actions_layout.addWidget(self.image_mode_combo)
        actions_layout.addWidget(self.apply_region_button)
        actions_layout.addSpacing(12)
        actions_layout.addWidget(self.actions_button)
        actions_layout.addSpacing(12)
        actions_layout.addWidget(self.selection_label)
        actions_layout.addWidget(self.source_label)
        actions_layout.addWidget(self.output_label)
        actions_layout.addWidget(self.current_values_label)
        actions_layout.addWidget(self.aperture_label)
        actions_layout.addWidget(self.aperture_radius_box)
        actions_layout.addStretch()

        right_panel_layout.addWidget(files_box)
        right_panel_layout.addWidget(actions_box)
        right_panel_layout.addStretch()

        main_layout.addLayout(left_layout, stretch=8)
        main_layout.addWidget(right_panel, stretch=2)
        self.compact_right_panel_text()
        self.setCentralWidget(main_widget)

    def on_image_limits_changed(self, ax):
        if self._updating_image_limits:
            return

        self.image_xlim = ax.get_xlim()
        self.image_ylim = ax.get_ylim()

    def on_spectrum_limits_changed(self, ax):
        if self._updating_spectrum_limits:
            return

        self.spectrum_xlim = ax.get_xlim()
        self.spectrum_ylim = ax.get_ylim()

    def select_cubex_path(self):
        path = QFileDialog.getExistingDirectory(self, "Select CubEx root directory")
        if not path:
            return

        self.cubex_root = path
        self.cubex_path_label.setText(f"CubEx path: {path}")

    def select_registry_table(self):
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Select or create action registry table",
            "",
            "CSV table (*.csv)",
        )

        if not path:
            return

        if not path.lower().endswith(".csv"):
            path += ".csv"

        self.registry_table_path = path
        self.table_label.setText(f"Action table: {path}")

    def open_cube(self):
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Open FITS cube",
            "",
            "FITS files (*.fits *.fit *.fz)",
        )

        if not path:
            return

        self.load_cube(path, add_to_list=True, reset_zoom=True)

    def reload_current_cube(self):
        if self.cube_path is None:
            return

        self.load_cube(self.cube_path, add_to_list=False, reset_zoom=False)

    def switch_loaded_file(self, label):
        if not label:
            return

        path = self.loaded_files.get(label)
        if path is None:
            return

        if path == self.cube_path:
            return

        self.load_cube(path, add_to_list=False, reset_zoom=True)

    def remove_selected_loaded_file(self):
        """Remove the selected file from the loaded-file list without deleting it from disk."""
        label = self.cube_selector.currentText()
        if not label:
            return

        if label in self.loaded_files:
            self.loaded_files.pop(label, None)

        idx = self.cube_selector.currentIndex()
        self.cube_selector.blockSignals(True)
        if idx >= 0:
            self.cube_selector.removeItem(idx)
        self.cube_selector.blockSignals(False)

        if self.cube_selector.count() > 0:
            new_label = self.cube_selector.currentText()
            new_path = self.loaded_files.get(new_label)
            if new_path:
                self.load_cube(new_path, add_to_list=False, reset_zoom=True)
        else:
            self.cube = None
            self.header = None
            self.cube_path = None
            self.data_is_image = False
            self.wave = None
            self.selected_x = None
            self.selected_y = None
            self.image_ax.clear()
            self.spectrum_ax.clear()
            self.image_canvas.draw_idle()
            self.spectrum_canvas.draw_idle()
            self.info_label.setText("No FITS image/cube loaded")
            self.output_label.setText("Last output: none")
            self.current_values_label.setText("Current values: z = none | lambda = none | x = none | y = none")

    def add_loaded_file(self, path):
        label = os.path.basename(path)

        if label in self.loaded_files and self.loaded_files[label] != path:
            label = path

        self.loaded_files[label] = path

        already = [self.cube_selector.itemText(i) for i in range(self.cube_selector.count())]
        if label not in already:
            self.cube_selector.blockSignals(True)
            self.cube_selector.addItem(label)
            self.cube_selector.blockSignals(False)

        self.cube_selector.blockSignals(True)
        self.cube_selector.setCurrentText(label)
        self.cube_selector.blockSignals(False)

    def load_cube(self, path, add_to_list=True, reset_zoom=True):
        self.load_progress.setValue(5)
        QApplication.processEvents()

        self.cube = None
        self.header = None
        self.cube_path = path

        with fits.open(path, memmap=True) as hdul:
            self.load_progress.setValue(25)
            QApplication.processEvents()

            for hdu in hdul:
                if hdu.data is not None and hdu.data.ndim == 3:
                    self.cube = np.asarray(hdu.data, dtype=float)
                    self.header = hdu.header
                    break

        self.load_progress.setValue(80)
        QApplication.processEvents()

        if self.cube is None:
            self.info_label.setText("No 3D cube found")
            self.load_progress.setValue(0)
            return

        if add_to_list:
            self.add_loaded_file(path)

        if reset_zoom:
            self.image_xlim = None
            self.image_ylim = None
            self.spectrum_xlim = None
            self.spectrum_ylim = None

        nz, ny, nx = self.cube.shape
        self.compute_wavelength_axis()

        self.current_z = min(max(self.current_z, 0), nz - 1)

        self.z_slider.blockSignals(True)
        self.z_slider.setMinimum(0)
        self.z_slider.setMaximum(nz - 1)
        self.z_slider.setValue(self.current_z)
        self.z_slider.blockSignals(False)

        self.z_label.setText(f"z = {self.current_z}")
        self.info_label.setText(f"{path} | shape = {nx} x {ny} x {nz}")

        self.update_image(keep_zoom=not reset_zoom)
        self.update_spectrum(keep_zoom=not reset_zoom)
        self.update_current_values_label()

        self.load_progress.setValue(100)

    def update_slice_from_slider(self):
        if self.cube is None:
            return

        self.current_z = self.z_slider.value()
        self.z_label.setText(f"z = {self.current_z}")

        self.image_mode = "slice"

        self.image_mode_combo.blockSignals(True)
        self.image_mode_combo.setCurrentText("slice")
        self.image_mode_combo.blockSignals(False)

        self.update_image(keep_zoom=True)
        self.update_spectrum(keep_zoom=True)
        self.update_current_values_label()

    def change_image_mode(self, text):
        self.image_mode = text
        self.update_image(keep_zoom=True)

    def get_current_image(self):
        if self.cube is None:
            return None

        if self.image_mode == "slice":
            return self.cube[self.current_z, :, :]

        if self.spec_min is None or self.spec_max is None:
            return self.cube[self.current_z, :, :]

        z1 = max(0, int(np.floor(self.spec_min)))
        z2 = min(self.cube.shape[0], int(np.ceil(self.spec_max)) + 1)

        if z2 <= z1:
            return self.cube[self.current_z, :, :]

        subcube = self.cube[z1:z2, :, :]

        if self.image_mode == "mean selected region":
            return np.nanmean(subcube, axis=0)

        if self.image_mode == "median selected region":
            return np.nanmedian(subcube, axis=0)

        return self.cube[self.current_z, :, :]

    def compute_wavelength_axis(self):
        if self.header is None or self.cube is None:
            self.wave = None
            return

        nz = self.cube.shape[0]

        crval3 = self.header.get("CRVAL3", None)
        cd3_3 = self.header.get("CD3_3", self.header.get("CDELT3", None))
        crpix3 = self.header.get("CRPIX3", 1.0)

        if crval3 is None or cd3_3 is None:
            self.wave = np.arange(nz, dtype=float)
            return

        pix = np.arange(nz, dtype=float) + 1.0
        self.wave = crval3 + (pix - crpix3) * cd3_3

    def get_current_lambda(self):
        if self.wave is None:
            return None

        if self.current_z < 0 or self.current_z >= len(self.wave):
            return None

        return float(self.wave[self.current_z])

    def lambda_to_zpix(self, lam):
        if self.wave is None:
            return int(round(lam))

        return int(np.argmin(np.abs(self.wave - lam)))

    def reset_zoom(self):
        # Reset image zoom completely.
        self.image_xlim = None
        self.image_ylim = None

        # Reset only the spectral x zoom.
        # The y axis is always auto-scaled anyway.
        self.spectrum_xlim = None
        self.spectrum_ylim = None

        self.update_image(keep_zoom=False)
        self.update_spectrum(keep_zoom=False)

    def update_current_values_label(self):
        lam = self.get_current_lambda()

        z_txt = str(self.current_z)
        lam_txt = "none" if lam is None else f"{lam:.3f}"

        if self.selected_x is None or self.selected_y is None:
            x_txt = "none"
            y_txt = "none"
        else:
            x_txt = f"{self.selected_x:.2f}"
            y_txt = f"{self.selected_y:.2f}"

        self.current_values_label.setText(
            f"Current values: z = {z_txt} | lambda = {lam_txt} | x = {x_txt} | y = {y_txt}"
        )

    def update_image(self, keep_zoom=True):
        if self.cube is None:
            return

        # Save current visible limits before clearing the axis.
        if keep_zoom and self.image_ax.has_data():
            xlim = self.image_ax.get_xlim()
            ylim = self.image_ax.get_ylim()
        else:
            xlim = None
            ylim = None

        image = self.get_current_image()

        self.image_ax.clear()
        
        finite_positive = np.isfinite(image) & (image > 0)

        if np.any(finite_positive):
            vmax = np.nanmax(image[finite_positive])
            positive_values = image[finite_positive]

            vmin = np.nanmin(positive_values)

            if not np.isfinite(vmin) or vmin <= 0:
                vmin = vmax * 1e-4

            if vmin >= vmax:
                vmin = 1e-4

            self.image_ax.imshow(
                image,
                origin="lower",
                norm=LogNorm(vmin=vmin, vmax=vmax),
            )
        else:
            self.image_ax.imshow(image, origin="lower")
            
        self.image_ax.set_xlabel("x [pix]")
        self.image_ax.set_ylabel("y [pix]")

        lam = self.get_current_lambda()

        if self.image_mode == "slice":
            if lam is None:
                self.image_ax.set_title(f"Slice z = {self.current_z}")
            else:
                self.image_ax.set_title(f"Slice z = {self.current_z} | lambda = {lam:.3f}")
        elif self.spec_min is not None and self.spec_max is not None:
            self.image_ax.set_title(
                f"{self.image_mode}: z = {self.spec_min:.1f} - {self.spec_max:.1f}"
            )

        if self.selected_x is not None and self.selected_y is not None:
            self.image_ax.plot(
                self.selected_x,
                self.selected_y,
                marker="+",
                markersize=14,
                markeredgewidth=2,
            )
            if self.aperture_radius > 0:
                circle = plt.Circle(
                    (self.selected_x, self.selected_y),
                    self.aperture_radius,
                    fill=False,
                    linewidth=1.5,
                )
                self.image_ax.add_patch(circle)

        # Restore the exact zoom/pan view after redrawing.
        if keep_zoom and xlim is not None and ylim is not None:
            self.image_ax.set_xlim(xlim)
            self.image_ax.set_ylim(ylim)

        self.image_canvas.draw_idle()
        self.update_current_values_label()

    def update_aperture_radius(self, value):
        self.aperture_radius = float(value)
        self.update_image(keep_zoom=True)
        self.update_spectrum(keep_zoom=True)
    
    def update_spectrum(self, keep_zoom=True):
        if self.cube is None:
            return

        # Preserve only the spectral x range. The y range is always recomputed
        # after plotting so the full spectrum remains visible at each selected position.
        if keep_zoom and self.spectrum_ax.has_data():
            xlim = self.spectrum_ax.get_xlim()
        else:
            xlim = None

        self.spectrum_ax.clear()

        nz = self.cube.shape[0]

        if self.wave is None:
            xaxis = np.arange(nz)
            xlabel = "Spectral pixel"
            current_x = self.current_z
        else:
            xaxis = self.wave
            xlabel = "Wavelength"
            current_x = self.get_current_lambda()

        if self.selected_x is None or self.selected_y is None:
            spectrum = np.nanmedian(self.cube, axis=(1, 2))
            label = "median cube spectrum"
        else:
            x = int(round(self.selected_x))
            y = int(round(self.selected_y))

            if 0 <= x < self.cube.shape[2] and 0 <= y < self.cube.shape[1]:

                if self.aperture_radius > 0:
                    yy, xx = np.indices(self.cube.shape[1:])
                    rr = np.sqrt((xx - self.selected_x) ** 2 + (yy - self.selected_y) ** 2)
                    mask = rr <= self.aperture_radius

                    if np.any(mask):
                        spectrum = np.nanmean(self.cube[:, mask], axis=1)
                        label = f"mean spectrum within r={self.aperture_radius:.1f} pix"
                    else:
                        spectrum = self.cube[:, y, x]
                        label = f"spectrum at x={x}, y={y}"
                else:
                    spectrum = self.cube[:, y, x]
                    label = f"spectrum at x={x}, y={y}"

            else:
                spectrum = np.nanmedian(self.cube, axis=(1, 2))
                label = "median cube spectrum"

        self.spectrum_ax.plot(xaxis, spectrum, drawstyle="steps-mid", lw=1)

        if current_x is not None:
            self.spectrum_ax.axvline(current_x, linestyle="--", lw=1)

        self.spectrum_ax.set_xlabel(xlabel)
        self.spectrum_ax.set_ylabel("Flux")
        self.spectrum_ax.set_title(label)

        if self.spec_min is not None and self.spec_max is not None:
            if self.wave is None:
                x1 = self.spec_min
                x2 = self.spec_max
            else:
                x1 = self.wave[int(self.spec_min)]
                x2 = self.wave[int(self.spec_max)]

            self.spectrum_ax.axvspan(x1, x2, alpha=0.2)

        # Restore only the spectral x zoom. Then autoscale y to show the full spectrum.
        if keep_zoom and xlim is not None:
            self.spectrum_ax.set_xlim(xlim)

        self.spectrum_ax.relim()
        self.spectrum_ax.autoscale_view(scalex=False, scaley=True)
        self.spectrum_ylim = self.spectrum_ax.get_ylim()

        self.spectrum_canvas.draw_idle()
        self.update_current_values_label()


    def on_image_click(self, event):
        if self.cube is None:
            return

        if event.xdata is None or event.ydata is None:
            return

        # Do not select a source while matplotlib zoom/pan is active.
        mode = self.image_toolbar.mode
        if mode:
            return

        # Save current zoom before changing the selected pixel.
        image_xlim = self.image_ax.get_xlim()
        image_ylim = self.image_ax.get_ylim()
        spectrum_xlim = self.spectrum_ax.get_xlim() if self.spectrum_ax.has_data() else None

        self.selected_x = float(event.xdata)
        self.selected_y = float(event.ydata)

        self.source_label.setText(
            f"Selected source: x={self.selected_x:.2f}, y={self.selected_y:.2f}"
        )

        self.update_image(keep_zoom=False)
        self.image_ax.set_xlim(image_xlim)
        self.image_ax.set_ylim(image_ylim)
        self.image_canvas.draw_idle()

        self.update_spectrum(keep_zoom=False)
        if spectrum_xlim is not None:
            self.spectrum_ax.set_xlim(spectrum_xlim)
            self.spectrum_ax.relim()
            self.spectrum_ax.autoscale_view(scalex=False, scaley=True)
            self.spectrum_canvas.draw_idle()

        self.update_current_values_label()

    def on_spectral_region_selected(self, xmin, xmax):
        if self.cube is None:
            return

        if self.wave is None:
            zmin = int(round(min(xmin, xmax)))
            zmax = int(round(max(xmin, xmax)))
        else:
            zmin = self.lambda_to_zpix(min(xmin, xmax))
            zmax = self.lambda_to_zpix(max(xmin, xmax))

        zmin = max(0, zmin)
        zmax = min(self.cube.shape[0] - 1, zmax)

        self.spec_min = min(zmin, zmax)
        self.spec_max = max(zmin, zmax)

        lam_min = self.wave[self.spec_min] if self.wave is not None else self.spec_min
        lam_max = self.wave[self.spec_max] if self.wave is not None else self.spec_max

        self.selection_label.setText(
            f"Selected spectral region: z = {self.spec_min} - {self.spec_max} | "
            f"lambda = {lam_min:.3f} - {lam_max:.3f}"
        )

        self.update_spectrum(keep_zoom=True)
        self.update_image(keep_zoom=True)

    def open_action_dialog(self, action_name):
        if self.cube_path is None:
            QMessageBox.warning(self, "No cube", "Load a FITS cube first.")
            return

        if not self.cubex_root:
            QMessageBox.warning(self, "CubEx path missing", "Set the CubEx root directory first.")
            return

        defaults = CUBEX_ACTIONS[action_name]

        params = dict(defaults["params"])
        
        if action_name == "CreateMask":
            cube_dir = os.path.dirname(self.cube_path)
            cube_root = os.path.splitext(os.path.basename(self.cube_path))[0]

            params["input_image"] = os.path.join(cube_dir, cube_root + ".IM.fits")
            params["output_mask"] = os.path.join(cube_dir, "SourceMask.fits")

        if action_name == "Binarize3DMask":
            params["mask3d"] = self.cube_path

        if action_name == "CreateMaps":
            cube_dir = os.path.dirname(self.cube_path)
            cube_root = os.path.splitext(os.path.basename(self.cube_path))[0]

            params["cube"] = self.cube_path
            params["SBmap"] = os.path.join(cube_dir, cube_root + "_sb.fits")
            params["KinMap"] = os.path.join(cube_dir, cube_root + "_kin.fits")

        if action_name == "CubePSFSub" and self.selected_x is not None and self.selected_y is not None:
            params["x"] = f"{self.selected_x:.2f}"
            params["y"] = f"{self.selected_y:.2f}"

        if action_name in ["CubeBKGSub", "CubePSFSub"] and self.spec_min is not None and self.spec_max is not None:
            params["maskpix"] = f"{int(self.spec_min)} {int(self.spec_max)}"

        if action_name == "CubeSel" and self.spec_min is not None and self.spec_max is not None:
            params["zmin"] = str(int(self.spec_min))
            params["zmax"] = str(int(self.spec_max))
        
        if action_name == "CubEx":
            params["InpFile"] = self.cube_path

            cube_dir = os.path.dirname(self.cube_path)
            cube_root = os.path.splitext(os.path.basename(self.cube_path))[0]

            params["Catalogue"] = os.path.join(cube_dir, cube_root + ".cat")


        action_config = {
            **defaults,
            "params": params,
        }

        dialog = CubExActionDialog(
            parent=self,
            action_name=action_name,
            action_config=action_config,
            cube_path=self.cube_path,
            cubex_root=self.cubex_root,
        )

        if dialog.exec() == QDialog.Accepted:
            out_path = dialog.output_path
            params_used = dialog.params_used
            command_used = dialog.command_used

            self.output_label.setText(f"Last output: {out_path}")

            self.save_action_to_registry(
                action_name=action_name,
                input_cube=dialog.input_cube_path,
                output_cube=out_path,
                params=params_used,
                command=command_used,
            )

            if out_path and os.path.exists(out_path) and out_path.lower().endswith(".fits"):
                self.add_loaded_file(out_path)

                if dialog.open_output_after_run:
                    self.load_cube(out_path, add_to_list=True, reset_zoom=True)
    
    def compact_right_panel_text(self):
        widgets = [
            self.cubex_path_label,
            self.table_label,
            self.info_label,
            self.selection_label,
            self.source_label,
            self.output_label,
            self.current_values_label,
            self.aperture_label,
        ]

        for widget in widgets:
            widget.setWordWrap(True)
            widget.setStyleSheet("font-size: 10px;")

        self.open_button.setStyleSheet("font-size: 10px;")
        self.open_extra_button.setStyleSheet("font-size: 10px;")
        self.reload_button.setStyleSheet("font-size: 10px;")
        self.remove_loaded_button.setStyleSheet("font-size: 10px;")
        self.cubex_path_button.setStyleSheet("font-size: 10px;")
        self.table_button.setStyleSheet("font-size: 10px;")
        self.actions_button.setStyleSheet("font-size: 10px;")
        self.apply_region_button.setStyleSheet("font-size: 10px;")
        self.cube_selector.setStyleSheet("font-size: 10px;")
        self.image_mode_combo.setStyleSheet("font-size: 10px;")
        self.aperture_radius_box.setStyleSheet("font-size: 10px;")
    
    def save_action_to_registry(self, action_name, input_cube, output_cube, params, command):
        if self.registry_table_path is None:
            return

        import csv

        cube_name = os.path.splitext(os.path.basename(input_cube))[0]

        row_dict = {
            "CubeName": cube_name,
            "CubePath": input_cube,
            "LastAction": action_name,
            "LastOutput": output_cube or "",
            "LastCommand": command or "",
        }

        for key, value in params.items():
            col = safe_column_name(f"{action_name}_{key}")
            row_dict[col] = value

        rows = []
        fieldnames = []

        if os.path.exists(self.registry_table_path):
            with open(self.registry_table_path, "r", newline="") as f:
                reader = csv.DictReader(f)
                fieldnames = list(reader.fieldnames or [])
                rows = list(reader)

        for key in row_dict:
            if key not in fieldnames:
                fieldnames.append(key)

        found = False

        for row in rows:
            if row.get("CubeName", "") == cube_name:
                row.update(row_dict)
                found = True
                break

        if not found:
            new_row = {key: "" for key in fieldnames}
            new_row.update(row_dict)
            rows.append(new_row)

        for row in rows:
            for key in fieldnames:
                if key not in row:
                    row[key] = ""

        with open(self.registry_table_path, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)
            
            
        
        
class CubExActionDialog(QDialog):
    def __init__(self, parent, action_name, action_config, cube_path, cubex_root):
        super().__init__(parent)

        self.action_name = action_name
        self.action_config = action_config
        self.cube_path = cube_path
        self.cubex_root = cubex_root

        self.output_path = None
        self.input_cube_path = cube_path
        self.params_used = {}
        self.command_used = ""
        self.open_output_after_run = False

        self.param_widgets = {}

        self.setWindowTitle(action_name)
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)

        form = QFormLayout()

        self.input_cube = QLineEdit(self.cube_path)
        form.addRow("Input cube", self.input_cube)

        default_out = self.default_output_path()
        self.output_file = QLineEdit(default_out)

        if self.action_name != "CubEx":
            form.addRow("Output file", self.output_file)

        for key, value in self.action_config["params"].items():
            widget = QLineEdit(str(value))
            self.param_widgets[key] = widget
            form.addRow(key, widget)

        self.open_output_checkbox = QCheckBox("Open output after completion")
        self.open_output_checkbox.setChecked(True)

        if self.action_name != "CubEx":
            form.addRow("", self.open_output_checkbox)

        layout.addLayout(form)

        self.command_preview = QLineEdit()
        self.command_preview.setReadOnly(True)

        layout.addWidget(QLabel("Command preview"))
        layout.addWidget(self.command_preview)

        button_bar = QHBoxLayout()

        preview_button = QPushButton("Preview")
        preview_button.clicked.connect(self.update_command_preview)

        run_button = QPushButton("OK / Apply")
        run_button.clicked.connect(self.run_action)

        cancel_button = QPushButton("Cancel")
        cancel_button.clicked.connect(self.reject)

        button_bar.addWidget(preview_button)
        button_bar.addWidget(run_button)
        button_bar.addWidget(cancel_button)

        layout.addLayout(button_bar)

        self.update_command_preview()

    def default_output_path(self):
        cube = self.cube_path
        root, ext = os.path.splitext(cube)

        suffix = self.action_config.get("suffix", "")

        if self.action_name == "CubeSel":
            zmin = self.action_config["params"].get("zmin", "")
            zmax = self.action_config["params"].get("zmax", "")
            if zmin and zmax:
                return f"{root}_sel{zmin}_{zmax}.fits"

        if suffix:
            return f"{root}{suffix}"

        return ""

    def collect_params(self):
        return {key: widget.text().strip() for key, widget in self.param_widgets.items()}

    def build_command(self):
        params = self.collect_params()
        if self.is_special_action():
            return []
        exe_rel = self.action_config["executable"]

        if exe_rel == "CubEx":
            executable = os.path.join(self.cubex_root, "CubEx")
        else:
            executable = os.path.join(self.cubex_root, exe_rel)

        if self.action_name == "CubEx":
            parfile = self.write_cubex_parameter_file(params)
            cmd = [executable, parfile]
            return cmd

        cmd = [
            executable,
            "-cube",
            self.input_cube.text().strip(),
            "-out",
            self.output_file.text().strip(),
        ]

        for key, value in params.items():
            value = str(value).strip()

            if value in ["", "None", "none", "??", "null"]:
                continue

            cmd.append(f"-{key}")
            cmd.append(value)

        return cmd

    def is_special_action(self):
        return bool(self.action_config.get("special", False))

    def update_command_preview(self):
        if self.is_special_action():
            params = self.collect_params()

            if self.action_name == "CreateMask":
                txt = (
                    f"CubEx -cube {params.get('input_image')} "
                    f"-MultiExt {params.get('MultiExt')} "
                    f"-f {params.get('ApplyFilter')} "
                    f"-fv {params.get('ApplyFilterVar')} "
                    f"-fsr {params.get('FilterXYRad')} "
                    f"-sn {params.get('SN_Threshold')} "
                    f"-n {params.get('MinNVox')} ; "
                    f"mv input_image.Objects_Id.fits {params.get('output_mask')}"
                )

            elif self.action_name == "Binarize3DMask":
                txt = (
                    f"Open {params.get('mask3d')} and set selected_id={params.get('selected_id')} "
                    f"to 1, all other values to 0. File is overwritten."
                )

            elif self.action_name == "CreateMaps":
                txt = (
                    f"Create SB map {params.get('SBmap')} and kinematic map "
                    f"{params.get('KinMap')} from cube={params.get('cube')} "
                    f"and mask3d={params.get('mask3d')}"
                )

            else:
                txt = f"Special action: {self.action_name}"

            self.command_preview.setText(txt)
            return

        cmd = self.build_command()
        self.command_preview.setText(" ".join(shlex.quote(x) for x in cmd))

    def run_action(self):
        self.update_command_preview()

        if self.is_special_action():
            self.run_special_action()
            return

        cmd = self.build_command()
        cmd_txt = " ".join(shlex.quote(x) for x in cmd)

        print("\n========== Running CubEx action ==========")
        print(cmd_txt)
        print("==========================================\n")

        try:
            result = subprocess.run(
                cmd,
                check=True,
                cwd=self.cubex_root,
                capture_output=True,
                text=True,
            )

            if result.stdout:
                print(result.stdout)

            if result.stderr:
                print(result.stderr)

        except FileNotFoundError:
            QMessageBox.critical(
                self,
                "Executable not found",
                f"Cannot find executable:\n{cmd[0]}",
            )
            return

        except subprocess.CalledProcessError as exc:
            msg = f"Command failed with exit code {exc.returncode}\n\nCommand:\n{cmd_txt}"

            if exc.stdout:
                msg += f"\n\nSTDOUT:\n{exc.stdout}"

            if exc.stderr:
                msg += f"\n\nSTDERR:\n{exc.stderr}"

            QMessageBox.critical(self, "CubEx error", msg)
            return

        self.input_cube_path = self.input_cube.text().strip()
        self.params_used = self.collect_params()
        self.command_used = cmd_txt

        if self.action_name != "CubEx":
            self.output_path = self.output_file.text().strip()
            self.open_output_after_run = self.open_output_checkbox.isChecked()
        else:
            self.output_path = getattr(self, "generated_parfile", None)
            self.open_output_after_run = False

        QMessageBox.information(
            self,
            "Done",
            f"{self.action_name} completed.\n\nCommand:\n{cmd_txt}",
        )

        self.accept()

    
    def write_cubex_parameter_file(self, params):
        input_cube = self.input_cube.text().strip()
        cube_dir = os.path.dirname(input_cube)
        cube_root = os.path.splitext(os.path.basename(input_cube))[0]

        par_path = os.path.join(cube_dir, f"{cube_root}_CubEx.par")

        params = dict(params)

        if not params.get("InpFile", "").strip():
            params["InpFile"] = input_cube

        source_mask = params.get("SourceMask", "").strip().lower()

        if source_mask in ["", "none", "??", "null"]:
            params.pop("SourceMask", None)
            params.pop("MaskOnly", None)
            params.pop("UnMask", None)

        skip_if_empty = {
            "Catalogue",
            "zmin",
            "zmax",
            "lmin",
            "lmax",
            "VarFile",
            "LayerMaskList",
            "ObjMaskList",
            "AssocCatalogue",
            "NegCatalogue",
            "CheckCube",
            "SourceMask",
            "MaskOnly",
            "UnMask",
        }

        string_params = {
            "InpFile",
            "Catalogue",
            "VarFile",
            "RescaleVarArea",
            "RescalingVarOutFile",
            "RescalingVarInpFile",
            "EstVarOutFile",
            "NegCatalogue",
            "AssocCatalogue",
            "InpCat",
            "InpCatOnly",
            "IdCube",
            "CheckCube",
            "CheckCubeFMT",
            "CheckCubeType",
            "SourceMask",
            "MaskOnly",
            "UnMask",
            "LayerMaskList",
            "ObjMaskList",
        }

        with open(par_path, "w") as f:
            f.write("# CubEx parameter file generated by AutomatiCubEx\n")
            f.write("# This file was generated from the GUI.\n\n")

            for key, value in params.items():
                value = str(value).strip()

                if key in skip_if_empty and value in ["", "None", "none", "??", "null"]:
                    continue

                if value == "":
                    continue

                if key in string_params:
                    if value not in ["??"] and not value.startswith('"') and not value.startswith("'"):
                        value = f'"{value}"'

                f.write(f"{key} = {value}\n")

        self.generated_parfile = par_path
        return par_path
    def run_special_action(self):
        params = self.collect_params()

        try:
            if self.action_name == "CreateMask":
                self.run_create_mask(params)

            elif self.action_name == "Binarize3DMask":
                self.run_binarize_3d_mask(params)

            elif self.action_name == "CreateMaps":
                self.run_create_maps(params)

            else:
                raise ValueError(f"Unknown special action: {self.action_name}")

        except Exception as exc:
            QMessageBox.critical(self, self.action_name, str(exc))
            return

        self.input_cube_path = params.get(
            "input_cube",
            params.get("input_image", params.get("cube", params.get("mask3d", self.cube_path)))
        )
        self.params_used = params
        self.command_used = self.command_preview.text()

        if self.action_name == "CreateMask":
            self.output_path = params.get("output_mask", "")
        elif self.action_name == "CreateMaps":
            self.output_path = params.get("SBmap", "")
        elif self.action_name == "Binarize3DMask":
            self.output_path = params.get("mask3d", "")
        else:
            self.output_path = ""

        self.open_output_after_run = False

        QMessageBox.information(
            self,
            "Done",
            f"{self.action_name} completed."
        )

        self.accept()

    def run_create_mask(self, params):
        input_image = params["input_image"].strip()
        output_mask = params["output_mask"].strip()

        if not input_image:
            raise ValueError("input_image is empty.")

        if not os.path.exists(input_image):
            raise FileNotFoundError(
                f"Input image does not exist:\n{input_image}\n\n"
                "Create it first using the Cube2Im action."
            )

        if not output_mask:
            output_mask = os.path.join(os.path.dirname(input_image), "SourceMask.fits")

        cubex = os.path.join(self.cubex_root, "CubEx")

        cmd = [
            cubex,
            "-cube", input_image,
            "-MultiExt", params.get("MultiExt", ".false."),
            "-f", params.get("ApplyFilter", ".true."),
            "-fv", params.get("ApplyFilterVar", ".true."),
            "-fsr", params.get("FilterXYRad", "1"),
            "-sn", params.get("SN_Threshold", "5"),
            "-n", params.get("MinNVox", "80"),
        ]

        print("\n========== CreateMask ==========")
        print(" ".join(shlex.quote(x) for x in cmd))

        subprocess.run(
            cmd,
            check=True,
            cwd=os.path.dirname(input_image),
        )

        root, _ = os.path.splitext(input_image)
        objects_id = root + ".Objects_Id.fits"

        if not os.path.exists(objects_id):
            raise FileNotFoundError(f"Objects_Id file not found:\n{objects_id}")

        if os.path.exists(output_mask):
            os.remove(output_mask)

        shutil.move(objects_id, output_mask)

        self.command_preview.setText(
            " ; ".join([
                " ".join(shlex.quote(x) for x in cmd),
                f"mv {shlex.quote(objects_id)} {shlex.quote(output_mask)}",
            ])
        )

    def run_binarize_3d_mask(self, params):
        mask3d = params["mask3d"].strip()
        selected_id = params["selected_id"].strip()

        if not mask3d:
            raise ValueError("mask3d is empty.")

        if not selected_id:
            raise ValueError("selected_id is empty.")

        selected_id = float(selected_id)

        with fits.open(mask3d, mode="update", memmap=False) as hdul:
            hdu_index = None

            for i, hdu in enumerate(hdul):
                if hdu.data is not None and hdu.data.ndim == 3:
                    hdu_index = i
                    break

            if hdu_index is None:
                raise ValueError(f"No 3D image found in {mask3d}")

            data = hdul[hdu_index].data
            hdul[hdu_index].data = np.where(data == selected_id, 1, 0).astype(np.int16)
            hdul.flush()

        self.command_preview.setText(
            f"Binarized {mask3d}: value {selected_id:g} -> 1, all other values -> 0"
        )

    def run_create_maps(self, params):
        cube = params["cube"].strip()
        mask3d = params["mask3d"].strip()
        sbmap = params["SBmap"].strip()
        kinmap = params["KinMap"].strip()

        if not cube:
            raise ValueError("cube is empty.")

        if not mask3d:
            raise ValueError("mask3d is empty.")

        if not sbmap:
            root, _ = os.path.splitext(cube)
            sbmap = root + "_sb.fits"

        if not kinmap:
            root, _ = os.path.splitext(cube)
            kinmap = root + "_kin.fits"

        cube2im = os.path.join(self.cubex_root, "Tools", "Cube2Im")

        cmd_sb = [
            cube2im,
            "-cube", cube,
            "-idcube", mask3d,
            "-id", params.get("id", "1"),
            "-idpad", params.get("idpad", "-1"),
            "-out", sbmap,
            "-nl", params.get("nl", "-1"),
            "-nlpad", params.get("nlpad", "3"),
            "-imtype", "flux",
            "-sbscale", params.get("sbscale", ".true."),
            "-gsm", params.get("gsm", "1"),
        ]

        cmd_kin = [
            cube2im,
            "-cube", cube,
            "-idcube", mask3d,
            "-id", params.get("id", "1"),
            "-idpad", params.get("idpad", "-1"),
            "-out", kinmap,
            "-nlpad", params.get("nlpad2", "0"),
            "-nl", params.get("nl2", "0"),
            "-imtype", "vmap",
            "-sbscale", ".true.",
            "-gsm", params.get("gsm2", "2"),
            "-writeNaN", ".true.",
            "-vzerotype", "lambda",
        ]

        vzero = params.get("vzero", "").strip()
        if vzero:
            cmd_kin.extend(["-vzero", vzero])

        print("\n========== CreateMaps ==========")
        print(" ".join(shlex.quote(x) for x in cmd_sb))
        subprocess.run(cmd_sb,check=True,cwd=os.path.dirname(cube))

        print(" ".join(shlex.quote(x) for x in cmd_kin))
        subprocess.run(cmd_kin,check=True,cwd=os.path.dirname(cube))

        self.command_preview.setText(
            " ; ".join([
                " ".join(shlex.quote(x) for x in cmd_sb),
                " ".join(shlex.quote(x) for x in cmd_kin),
            ])
        )



if __name__ == "__main__":
    app = QApplication(sys.argv)

    viewer = CubeViewer()
    viewer.resize(1800, 1000)
    viewer.show()

    sys.exit(app.exec())
