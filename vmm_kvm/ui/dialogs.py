# -*- coding: utf-8 -*-
import os

from PySide6.QtCore import QDir, QProcess, Qt
from PySide6.QtWidgets import (QDialog, QDialogButtonBox, QFileSystemModel,
                               QFormLayout, QHBoxLayout, QHeaderView, QLabel,
                               QLineEdit, QListWidget, QListWidgetItem,
                               QMessageBox, QPlainTextEdit, QPushButton,
                               QTreeView, QVBoxLayout)


def confirm(parent, text, title=None):
    from .. import i18n
    r = QMessageBox.question(parent, title or i18n.t("m.confirm"), text,
                             QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
    return r == QMessageBox.Yes


def show_error(parent, text, title=None):
    from .. import i18n
    QMessageBox.critical(parent, title or i18n.t("m.err"), str(text))


def show_info(parent, text, title=None):
    from .. import i18n
    QMessageBox.information(parent, title or i18n.t("m.info"), str(text))


class FormDialog(QDialog):

    def __init__(self, parent, title):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setMinimumWidth(420)
        self.form = QFormLayout(self)
        self.form.setSpacing(10)
        bb = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        bb.accepted.connect(self.accept)
        bb.rejected.connect(self.reject)
        self._extra = QVBoxLayout()
        self.form.addRow(self._extra)
        self.form.addRow(bb)

    def add_line(self, label, value="", placeholder=""):
        e = QLineEdit(value)
        e.setPlaceholderText(placeholder)
        self.form.addRow(label, e)
        return e

    def add_row(self, label, widget):
        self.form.addRow(label, widget)


class ServicesDialog(QDialog):

    def __init__(self, parent, backend):
        super().__init__(parent)
        from .. import i18n
        self.backend = backend
        self.setWindowTitle(i18n.t("pgset.services"))
        self.setMinimumSize(640, 420)
        v = QVBoxLayout(self)
        hint = QLabel(i18n.t("pgset.services_hint"))
        hint.setWordWrap(True)
        v.addWidget(hint)
        self.log = QPlainTextEdit()
        self.log.setReadOnly(True)
        v.addWidget(self.log, 1)
        row = QHBoxLayout()
        self.btn = QPushButton(i18n.t("pgset.services"))
        self.btn.setObjectName("Accent")
        self.btn.clicked.connect(self.run)
        close = QPushButton(i18n.t("act.close"))
        close.clicked.connect(self.reject)
        self.status = QLabel("")
        row.addWidget(self.status)
        row.addStretch(1)
        row.addWidget(self.btn)
        row.addWidget(close)
        v.addLayout(row)
        self.proc = None

    def run(self):
        from .. import i18n
        cmd = self.backend.services_command()
        self.log.clear()
        self.status.setText("")
        self.btn.setEnabled(False)
        self.proc = QProcess(self)
        self.proc.setProcessChannelMode(QProcess.MergedChannels)
        self.proc.readyReadStandardOutput.connect(self._read)
        self.proc.finished.connect(self._done)
        self.status.setText(i18n.t("m.reconnecting"))
        self.proc.start(cmd[0], cmd[1:])

    def _read(self):
        data = bytes(self.proc.readAllStandardOutput()).decode("utf-8", "replace")
        self.log.appendPlainText(data.rstrip())

    def _done(self, code, status):
        from .. import i18n
        self.btn.setEnabled(True)
        self.status.setText(i18n.t("dlg.services_done", c=str(code)))
        self.proc = None


class AddSSHDialog(FormDialog):
    def __init__(self, parent):
        from .. import i18n
        super().__init__(parent, "")
        self.setWindowTitle(i18n.t("dlg.ssh_title"))
        self.name_e = self.add_line(i18n.t("dlg.ssh_name"), "")
        self.uri_e = self.add_line(i18n.t("dlg.ssh_uri"), "", "qemu+ssh://user@host/system")

    def values(self):
        return {"name": self.name_e.text().strip() or self.uri_e.text().strip(),
                "uri": self.uri_e.text().strip()}


class NewPoolDialog(FormDialog):
    def __init__(self, parent, default_path=""):
        super().__init__(parent, "")
        from .. import i18n
        self.setWindowTitle(i18n.t("dlg.pool_title"))
        self.name_e = self.add_line(i18n.t("dlg.pool_name"), "")
        row = QHBoxLayout()
        self.path_e = QLineEdit(default_path)
        btn = QPushButton(i18n.t("pgset.pick_folder"))
        btn.clicked.connect(self._pick)
        row.addWidget(self.path_e, 1)
        row.addWidget(btn)
        self.add_row(i18n.t("dlg.pool_path"), row)

    def _pick(self):
        dlg = FilePickerDialog(self, self.path_e.text() or "~", mode="dir")
        if dlg.exec() and dlg.result_path:
            self.path_e.setText(dlg.result_path)

    def values(self):
        return {"name": self.name_e.text().strip(), "path": self.path_e.text().strip()}


class NewNetworkDialog(FormDialog):
    def __init__(self, parent):
        super().__init__(parent, "")
        from .. import i18n
        self.setWindowTitle(i18n.t("dlg.net_title"))
        self.name_e = self.add_line(i18n.t("dlg.net_name"), "", "vmm-net")
        self.cidr_e = self.add_line(i18n.t("dlg.net_cidr"), "", "192.168.50.0/24")

    def values(self):
        return {"name": self.name_e.text().strip(), "cidr": self.cidr_e.text().strip()}


class SnapshotDialog(FormDialog):
    def __init__(self, parent, vm_name):
        super().__init__(parent, "")
        from .. import i18n
        self.setWindowTitle(i18n.t("dlg.snap_title"))
        self.name_e = self.add_line(i18n.t("dlg.snap_name"), vm_name + "-snap")
        self.desc_e = self.add_line(i18n.t("dlg.snap_desc"), "")

    def values(self):
        return {"name": self.name_e.text().strip(), "desc": self.desc_e.text().strip()}


class AddDiskDialog(FormDialog):
    def __init__(self, parent):
        super().__init__(parent, "")
        from .. import i18n
        from PySide6.QtWidgets import QComboBox, QSpinBox
        self.setWindowTitle(i18n.t("det.add_disk"))
        self.size = QSpinBox()
        self.size.setRange(1, 4096)
        self.size.setValue(20)
        self.bus = QComboBox()
        self.bus.addItems(["virtio", "sata", "ide", "scsi"])
        self.add_row(i18n.t("det.size"), self.size)
        self.add_row(i18n.t("det.bus"), self.bus)

    def values(self):
        return {"size_gb": self.size.value(), "bus": self.bus.currentText()}


class _FsModel(QFileSystemModel):

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        from .. import i18n
        if role == Qt.DisplayRole and orientation == Qt.Horizontal:
            return {0: i18n.t("fp.col_name"), 1: i18n.t("fp.col_size"),
                    2: "", 3: i18n.t("fp.col_date")}.get(section, "")
        return super().headerData(section, orientation, role)


class FilePickerDialog(QDialog):

    def __init__(self, parent, start_dir, mode="file", name_filters=("*.iso",), title=None):
        super().__init__(parent)
        from .. import i18n
        self.mode = mode
        self.result_path = None
        self.setWindowTitle(title or (i18n.t("fp.title_file") if mode == "file"
                                      else i18n.t("fp.title_dir")))
        self.setMinimumSize(780, 500)
        v = QVBoxLayout(self)
        v.setSpacing(8)

        top = QHBoxLayout()
        self.up_btn = QPushButton(i18n.t("fp.up"))
        self.up_btn.clicked.connect(self._up)
        self.path_e = QLineEdit()
        self.path_e.returnPressed.connect(lambda: self._set_dir(self.path_e.text()))
        top.addWidget(self.up_btn)
        top.addWidget(self.path_e, 1)
        v.addLayout(top)

        mid = QHBoxLayout()
        self.places = QListWidget()
        self.places.setFixedWidth(168)
        places = [(i18n.t("fp.home"), os.path.expanduser("~"))]
        if mode == "file":
            places.append((i18n.t("fp.iso_place"), start_dir))
        for root in ("/", "/mnt", "/media", "/run/media"):
            if os.path.isdir(root):
                places.append((root, root))
        for label, path in places:
            it = QListWidgetItem(label)
            it.setData(Qt.UserRole, path)
            self.places.addItem(it)
        self.places.itemClicked.connect(lambda it: self._set_dir(it.data(Qt.UserRole)))
        mid.addWidget(self.places)

        self.model = _FsModel(self)
        self.model.setFilter(QDir.AllDirs | QDir.Files | QDir.NoDotAndDotDot)
        self.model.setRootPath(QDir.rootPath())
        if mode == "file":
            self.model.setNameFilters(list(name_filters))
            try:
                self.model.setNameFilterDisables(False)
            except AttributeError:
                pass
        self.tree = QTreeView()
        self.tree.setModel(self.model)
        self.tree.setSelectionMode(QTreeView.SingleSelection)
        self.tree.setColumnHidden(2, True)
        self.tree.header().setSectionResizeMode(0, QHeaderView.Stretch)
        self.tree.setColumnWidth(1, 90)
        self.tree.setColumnWidth(3, 140)
        self.tree.doubleClicked.connect(self._dbl)
        self.tree.selectionModel().currentChanged.connect(self._cur)
        mid.addWidget(self.tree, 1)
        v.addLayout(mid, 1)

        bottom = QHBoxLayout()
        self.name_e = QLineEdit()
        self.name_e.setReadOnly(True)
        if mode == "file":
            self.name_e.setPlaceholderText(i18n.t("fp.selected_ph"))
        b_cancel = QPushButton(i18n.t("act.cancel"))
        b_cancel.clicked.connect(self.reject)
        b_ok = QPushButton(i18n.t("fp.select"))
        b_ok.setObjectName("Accent")
        b_ok.clicked.connect(self._accept)
        bottom.addWidget(self.name_e, 1)
        bottom.addWidget(b_cancel)
        bottom.addWidget(b_ok)
        v.addLayout(bottom)

        start = os.path.abspath(os.path.expanduser(start_dir or "~"))
        if not os.path.isdir(start):
            start = os.path.dirname(start)
        if not os.path.isdir(start):
            start = os.path.expanduser("~")
        self._set_dir(start)

    def _set_dir(self, path):
        path = os.path.abspath(os.path.expanduser((path or "").strip() or "~"))
        if not os.path.isdir(path):
            path = os.path.dirname(path) or os.path.expanduser("~")
        self._dir = path
        self.path_e.setText(path)
        self.tree.setRootIndex(self.model.index(path))
        self.name_e.setText("" if self.mode == "file" else path)

    def _up(self):
        parent = os.path.dirname(self._dir.rstrip("/")) or "/"
        self._set_dir(parent)

    def _cur(self, cur, prev=None):
        if not cur or not cur.isValid():
            return
        path = self.model.filePath(cur)
        if os.path.isdir(path):
            self.name_e.setText(path if self.mode == "dir" else "")
        else:
            self.name_e.setText(path)

    def _dbl(self, idx):
        path = self.model.filePath(idx)
        if os.path.isdir(path):
            self._set_dir(path)
        else:
            self.name_e.setText(path)
            self._accept()

    def _accept(self):
        if self.mode == "dir":
            path = self.name_e.text().strip()
            self.result_path = path if path and os.path.isdir(path) else self._dir
            super().accept()
            return
        path = self.name_e.text().strip()
        if not path:
            return
        if os.path.isdir(path):
            self._set_dir(path)
            return
        self.result_path = path
        super().accept()
