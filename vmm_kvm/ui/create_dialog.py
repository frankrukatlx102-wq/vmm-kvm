# -*- coding: utf-8 -*-
import os
import re

from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QCursor, QIcon
from PySide6.QtWidgets import (QCheckBox, QComboBox, QDialog,
                               QFormLayout, QHBoxLayout, QLabel, QLineEdit,
                               QMenu, QPlainTextEdit, QPushButton, QSizePolicy,
                               QSpinBox, QToolButton, QVBoxLayout)

from .. import config, i18n, osdata
from . import theme, widgets
from .dialogs import AddSSHDialog, FilePickerDialog, show_error, show_info

T = lambda key, **kw: i18n.t(key, **kw)

_VER_RX = re.compile(r"(\d+\.\d+(?:\.\d+)?)")
_PLATFORM_RX = re.compile(r"(x86[_-]64|amd64|x64|i[36]86|arm64|aarch64)", re.I)
_SANITIZE = re.compile(r"[^a-z0-9.+-]+")


def _detect(iso_path):
    fn = os.path.basename((iso_path or "").strip())
    osid = None
    if fn:
        g = osdata.guess_by_name(fn)
        if g != "other":
            osid = g
    clean = _PLATFORM_RX.sub(" ", fn)
    m = _VER_RX.search(clean)
    ver = m.group(1) if m else ""
    return osid, ver


def _auto_name(osid, ver, iso_path):
    if osid:
        return (osid + "-" + ver) if ver else osid
    stem = os.path.splitext(os.path.basename(iso_path or ""))[0].lower()
    return _SANITIZE.sub("-", stem).strip("-")[:40]


class CreateDialog(QDialog):
    def __init__(self, parent, backend, cfg, switch_conn=None):
        super().__init__(parent)
        self.b = backend
        self.cfg = cfg
        self.switch_conn = switch_conn
        self.result_name = None
        self.name_touched = False
        self.os_touched = False
        self.res_touched = False
        self._res_lock = False

        self.setWindowTitle(T("cd.title"))
        self.setMinimumWidth(640)
        v = QVBoxLayout(self)
        v.setSpacing(10)

        form = QFormLayout()
        form.setSpacing(10)
        form.setFieldGrowthPolicy(QFormLayout.AllNonFixedFieldsGrow)

        iso_row = QHBoxLayout()
        self.iso_e = QLineEdit()
        self.iso_e.setPlaceholderText(T("cd.iso_ph"))
        self.iso_e.setMinimumWidth(80)
        b_iso_list = QToolButton()
        b_iso_list.setObjectName("TbBtn")
        b_iso_list.setIcon(QIcon(os.path.join(os.path.dirname(__file__), "..",
                                              "assets", "icons", "arrow-down.svg")))
        b_iso_list.setToolTip(T("cd.iso_list"))
        b_iso_list.clicked.connect(self._iso_menu)
        b_iso_list.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        b_browse = QPushButton(T("pgset.pick_folder"))
        b_browse.clicked.connect(self._browse_iso)
        b_browse.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        b_browse.setMinimumWidth(
            b_browse.fontMetrics().horizontalAdvance(b_browse.text()) + 44)
        iso_row.addWidget(self.iso_e, 1)
        iso_row.addWidget(b_iso_list)
        iso_row.addWidget(b_browse)
        form.addRow(T("cd.iso"), iso_row)

        self.name_e = QLineEdit()
        self.name_e.textEdited.connect(self._name_edited)
        form.addRow(T("det.name"), self.name_e)

        os_row = QHBoxLayout()
        self.os_combo = QComboBox()
        self.os_combo.setIconSize(QSize(20, 20))
        self._fill_os()
        self.os_combo.activated.connect(self._os_activated)
        self.detect_lbl = QLabel("")
        self.detect_lbl.setObjectName("Muted")
        os_row.addWidget(self.os_combo, 1)
        os_row.addWidget(self.detect_lbl, 2)
        form.addRow(T("det.os"), os_row)
        v.addLayout(form)

        hw = QHBoxLayout()
        hw.setSpacing(16)
        self.f_vcpu = QSpinBox()
        lim = self.b.host_limits()
        self.f_vcpu.setRange(1, lim["cpus"])
        self.f_ram = QSpinBox()
        self.f_ram.setRange(64, lim["ram_mb"])
        self.f_ram.setSingleStep(256)
        self.f_disk = QSpinBox()
        self.f_disk.setRange(1, 4096)
        for spin in (self.f_vcpu, self.f_ram, self.f_disk):
            spin.valueChanged.connect(self._res_edited)
        self.f_vcpu.setFixedWidth(96)
        self.f_ram.setFixedWidth(136)
        self.f_disk.setFixedWidth(112)
        for label, wdg in ((T("det.vcpu"), self.f_vcpu),
                           (T("det.ram_mb"), self.f_ram),
                           (T("cd.disk"), self.f_disk)):
            col = QVBoxLayout()
            lbl = QLabel(label)
            lbl.setObjectName("Muted")
            col.addWidget(lbl)
            col.addWidget(wdg)
            hw.addLayout(col)
        self.f_kvm = QCheckBox(T("det.accel"))
        kvm_ok = os.path.exists("/dev/kvm")
        self.f_kvm.setChecked(kvm_ok)
        self.f_kvm.setEnabled(kvm_ok)
        if not kvm_ok:
            self.f_kvm.setToolTip(T("cd.kvm_na"))
        kv = QVBoxLayout()
        kv.addWidget(QLabel(" "))
        kv.addWidget(self.f_kvm)
        hw.addLayout(kv)
        hw.addStretch(1)
        v.addLayout(hw)
        self.host_lim_lbl = QLabel(T("cd.host_limits",
                                     ram=widgets.fmt_mb(lim["ram_mb"]),
                                     cpus=lim["cpus"]))
        self.host_lim_lbl.setObjectName("Muted")
        v.addWidget(self.host_lim_lbl)

        self.prof_lbl = QLabel("")
        self.prof_lbl.setObjectName("Muted")
        v.addWidget(self.prof_lbl)
        self.dir_lbl = QLabel("")
        self.dir_lbl.setObjectName("Muted")
        v.addWidget(self.dir_lbl)

        self.dr_btn = QToolButton()
        self.dr_btn.setObjectName("TbBtn")
        self.dr_btn.setText(T("cd.drivers"))
        self.dr_btn.setCheckable(True)
        self.dr_btn.setToolButtonStyle(Qt.ToolButtonTextOnly)
        self.dr_txt = QPlainTextEdit()
        self.dr_txt.setReadOnly(True)
        self.dr_txt.setMaximumHeight(130)
        self.dr_txt.setVisible(False)
        self.dr_btn.toggled.connect(self.dr_txt.setVisible)
        v.addWidget(self.dr_btn, 0, Qt.AlignLeft)
        v.addWidget(self.dr_txt)

        v.addStretch(1)

        foot = QHBoxLayout()
        self.host_lbl = QLabel("")
        self.host_lbl.setObjectName("Muted")
        b_ssh = QToolButton()
        b_ssh.setObjectName("TbBtn")
        b_ssh.setText(T("cd.ssh"))
        b_ssh.clicked.connect(self._ssh_menu)
        b_cancel = QPushButton(T("act.cancel"))
        b_cancel.clicked.connect(self.reject)
        b_create = QPushButton(T("act.create"))
        b_create.setObjectName("Accent")
        b_create.setDefault(True)
        b_create.clicked.connect(self._create)
        foot.addWidget(self.host_lbl, 1)
        foot.addWidget(b_ssh)
        foot.addWidget(b_cancel)
        foot.addWidget(b_create)
        v.addLayout(foot)

        self.iso_e.textChanged.connect(self._iso_changed)
        self._refresh_host()
        self._refresh_profile(apply_res=True)
        self.layout().activate()
        self.adjustSize()
        lm = self.layout().minimumSize()
        self.setMinimumSize(max(640, lm.width()), lm.height())

    def _fill_os(self):
        self.os_combo.clear()
        self.os_combo.addItem(widgets.os_icon("other"), T("cd.other"), "other")
        for fam in ("windows", "linux", "bsd", "other"):
            items = [o for o in osdata.by_family(fam) if o[1]]
            if fam == "other":
                items = [o for o in items if o[0] != "other"]
            if not items:
                continue
            self.os_combo.insertSeparator(self.os_combo.count())
            for osid, name, icon, fam_, prof in items:
                self.os_combo.addItem(widgets.os_icon(osid), name, osid)
        self.os_combo.setCurrentIndex(0)

    def _os_activated(self, idx):
        self.os_touched = True
        osid = self.os_combo.itemData(idx) or "other"
        if not self.name_touched:
            self.name_e.setText(_auto_name(osid, "", ""))
        self.detect_lbl.setText("")
        self.res_touched = False
        self._refresh_profile(apply_res=True)

    def _res_edited(self, *_):
        if not self._res_lock:
            self.res_touched = True

    def _refresh_profile(self, apply_res):
        osid = self.os_combo.currentData() or "other"
        prof = osdata.profile(osid)
        if apply_res and not self.res_touched:
            self._res_lock = True
            self.f_vcpu.setValue(prof["vcpu"])
            self.f_ram.setValue(prof["ram"])
            self.f_disk.setValue(prof["disk"])
            self._res_lock = False
        parts = ["UEFI" if prof["firmware"] == "uefi" else "BIOS"]
        if prof["tpm"]:
            parts.append("TPM 2.0")
        parts += [prof["bus"], prof["machine"], prof["net"]]
        self.prof_lbl.setText(T("cd.profile", p=" · ".join(parts)))
        if self.b._remote_target():
            self.dir_lbl.setText(T("cd.dir_note_remote"))
        else:
            self.dir_lbl.setText(T("cd.dir_note", dir=self.b._paths()["vms"]))
        hints = osdata.hint(osid, i18n.cur())
        self.dr_txt.setPlainText("\n".join(hints))
        self.dr_btn.setVisible(bool(hints))
        if not hints:
            self.dr_btn.setChecked(False)
            self.dr_txt.setVisible(False)

    def _iso_menu(self):
        m = QMenu(self)
        files = self.b.iso_files()
        base = self.b._paths()["iso"]
        if not files:
            act = m.addAction(T("cd.iso_none"))
            act.setEnabled(False)
        for f in files:
            act = m.addAction(f)
            act.setData(os.path.join(base, f))
        chosen = m.exec(QCursor.pos())
        if chosen and chosen.data():
            self.iso_e.setText(chosen.data())

    def _browse_iso(self):
        base = self.b._paths()["iso"]
        dlg = FilePickerDialog(self, base, mode="file", name_filters=("*.iso",))
        if dlg.exec() and dlg.result_path:
            self.iso_e.setText(dlg.result_path)

    def _name_edited(self):
        self.name_touched = True

    def _iso_changed(self, text):
        text = (text or "").strip()
        osid, ver = _detect(text)
        shown = osdata.name(osid) + ((" " + ver) if ver else "")
        if osid:
            self.detect_lbl.setText(T("cd.detect_ok", os=shown))
            if not self.os_touched:
                idx = self.os_combo.findData(osid)
                if idx >= 0:
                    self.os_combo.blockSignals(True)
                    self.os_combo.setCurrentIndex(idx)
                    self.os_combo.blockSignals(False)
                    self._refresh_profile(apply_res=True)
        else:
            self.detect_lbl.setText(T("cd.detect_fail") if text else "")
        if not self.name_touched:
            self.name_e.setText(_auto_name(osid, ver, text))

    def _ssh_menu(self):
        m = QMenu(self)
        add_act = m.addAction(T("pgset.ssh_add"))
        m.addSeparator()
        for h in self.cfg.get("ssh_hosts", []):
            act = m.addAction(h.get("name") or h.get("uri"))
            act.setData(h.get("uri"))
        chosen = m.exec(QCursor.pos())
        if not chosen:
            return
        if chosen is add_act:
            dlg = AddSSHDialog(self)
            if dlg.exec():
                val = dlg.values()
                if val["uri"]:
                    self.cfg.setdefault("ssh_hosts", []).append(val)
                    config.save(self.cfg)
                    self._do_switch(val["uri"])
        elif chosen.data():
            self._do_switch(chosen.data())

    def _do_switch(self, uri):
        if self.switch_conn and self.switch_conn(uri):
            self._refresh_host()
            self.iso_e.clear()

    def _refresh_host(self):
        remote = self.b._remote_target()
        if remote:
            user, host = remote
            uri = "qemu+ssh://%s@%s" % (user, host) if user else "qemu+ssh://%s" % host
            self.host_lbl.setText(T("cd.host_remote", uri=uri))
        else:
            self.host_lbl.setText(T("cd.host_local",
                                    mode=self.cfg.get("connection", "session")))

    def _create(self):
        name = self.name_e.text().strip()
        if not name:
            show_info(self, T("cd.need_name"))
            return
        if self.b._name_taken(name):
            show_info(self, T("cd.dup"))
            return
        params = {
            "name": name,
            "os_id": self.os_combo.currentData() or "other",
            "vcpu": self.f_vcpu.value(),
            "ram": self.f_ram.value(),
            "disk": self.f_disk.value(),
            "iso": self.iso_e.text().strip(),
            "firmware": "auto",
            "autostart": False,
            "kvm": self.f_kvm.isChecked(),
        }
        try:
            self.b.create_vm(params)
        except Exception as e:
            show_error(self, e)
            return
        self.result_name = name
        self.accept()
