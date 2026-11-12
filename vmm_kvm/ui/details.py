# -*- coding: utf-8 -*-
import os

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (QCheckBox, QComboBox, QFormLayout, QGridLayout,
                               QHBoxLayout, QLabel, QListWidget,
                               QListWidgetItem, QMenu, QPushButton, QSpinBox,
                               QSlider, QTableWidget, QTabWidget, QVBoxLayout,
                               QWidget)

from .. import i18n
from . import theme, widgets
from .dialogs import (AddDiskDialog, FilePickerDialog, SnapshotDialog,
                      confirm, show_error, show_info)

T = lambda key, **kw: i18n.t(key, **kw)
VIDEOS = ["virtio", "qxl", "vga", "cirrus"]
BUS_OPTS = ["virtio", "sata", "ide", "scsi"]
NIC_MODELS = ["virtio", "e1000", "e1000e", "rtl8139"]


class DetailsPanel(QWidget):
    changed = Signal()

    def __init__(self, backend, cfg):
        super().__init__()
        self.b = backend
        self.cfg = cfg
        self.vm = None
        self.hw_base = None
        self.setMinimumWidth(440)
        self.v = QVBoxLayout(self)
        self.v.setContentsMargins(4, 4, 4, 4)

        head = QWidget()
        h = QHBoxLayout(head)
        h.setContentsMargins(6, 4, 6, 4)
        self.icon_lbl = QLabel()
        self.icon_lbl.setFixedSize(46, 46)
        self.title_lbl = QLabel(T("det.no_vm"))
        self.title_lbl.setObjectName("H1")
        self.state_box = QVBoxLayout()
        self.state_box.setContentsMargins(0, 0, 0, 0)
        self.title_lbl.setWordWrap(True)
        h.addWidget(self.icon_lbl)
        hb = QVBoxLayout()
        hb.setContentsMargins(0, 0, 0, 0)
        hb.addWidget(self.title_lbl)
        self.state_slot = QHBoxLayout()
        hb.addLayout(self.state_slot)
        h.addLayout(hb, 1)
        self.v.addWidget(head)

        self.tabs = QTabWidget()
        self.v.addWidget(self.tabs, 1)

        self.tab_overview = QWidget()
        ov = QVBoxLayout(self.tab_overview)
        self.info_form = QFormLayout()
        self.info_form.setSpacing(7)
        ov.addLayout(self.info_form)
        self.cpu_spark = widgets.Sparkline(theme.ACCENT, 100, 64)
        self.ram_spark = widgets.Sparkline(theme.GREEN, None, 64)
        self.cpu_cap = QLabel(T("det.cpu_mem"))
        ov.addWidget(self.cpu_cap)
        ov.addWidget(self.cpu_spark)
        self.ram_cap = QLabel(T("pgstats.mem"))
        ov.addWidget(self.ram_cap)
        ov.addWidget(self.ram_spark)
        brow = QHBoxLayout()
        self.btn_start = QPushButton("  " + T("act.start"))
        self.btn_start.setObjectName("Accent")
        self.btn_start.clicked.connect(self._start)
        self.btn_console = QPushButton(T("act.console"))
        self.btn_console.clicked.connect(self._console)
        self.btn_stop = QPushButton(T("act.stop"))
        self.btn_stop.clicked.connect(self._stop)
        brow.addWidget(self.btn_start)
        brow.addWidget(self.btn_console)
        brow.addWidget(self.btn_stop)
        brow.addStretch(1)
        ov.addLayout(brow)
        ov.addStretch(1)

        self.tab_hw = QWidget()
        hw = QVBoxLayout(self.tab_hw)
        self.hw_form = QFormLayout()
        self.hw_form.setSpacing(9)
        hw.addLayout(self.hw_form)
        lim = backend.host_limits()
        self.f_vcpu = QSpinBox(); self.f_vcpu.setRange(1, lim["cpus"])
        self.f_ram = QSpinBox(); self.f_ram.setRange(16, lim["ram_mb"]); self.f_ram.setSingleStep(256)
        self.f_ram.setToolTip(T("det.ram_max", ram=widgets.fmt_mb(lim["ram_mb"])))
        self.f_ram_s = QSlider(Qt.Horizontal); self.f_ram_s.setRange(16, lim["ram_mb"])
        self.f_ram.valueChanged.connect(self._ram_sync)
        self.f_ram_s.valueChanged.connect(self._ram_sync_s)
        ram_row = QWidget()
        rr = QHBoxLayout(ram_row); rr.setContentsMargins(0, 0, 0, 0)
        rr.addWidget(self.f_ram, 1); rr.addWidget(self.f_ram_s, 2)
        self.f_kvm = QCheckBox(T("det.accel"))
        self.f_tcg = QCheckBox(T("det.tcg"))
        self.f_kvm.toggled.connect(lambda on: on and self.f_tcg.setChecked(False))
        self.f_tcg.toggled.connect(lambda on: on and self.f_kvm.setChecked(False))
        self.f_machine = QComboBox(); self.f_machine.addItems(["q35", "pc"])
        self.f_fw = QComboBox()
        self.f_fw.addItem(T("det.bios"), "bios")
        self.f_fw.addItem(T("det.uefi"), "uefi")
        self.f_tpm = QCheckBox(T("det.tpm"))
        self.f_video = QComboBox(); self.f_video.addItems(VIDEOS)
        self.f_auto = QCheckBox(T("det.autostart"))
        self.hw_form.addRow(T("det.vcpu"), self.f_vcpu)
        self.hw_form.addRow(T("det.ram_mb"), ram_row)
        self.f_ram_max = QLabel(T("det.ram_max", ram=widgets.fmt_mb(lim["ram_mb"])))
        self.f_ram_max.setObjectName("Muted")
        self.hw_form.addRow("", self.f_ram_max)
        self.hw_form.addRow("", self.f_kvm)
        self.hw_form.addRow("", self.f_tcg)
        self.hw_form.addRow(T("det.machine"), self.f_machine)
        self.hw_form.addRow(T("det.firmware"), self.f_fw)
        self.hw_form.addRow("", self.f_tpm)
        self.hw_form.addRow(T("det.video"), self.f_video)
        self.hw_form.addRow("", self.f_auto)
        self.hw_note = QLabel("")
        self.hw_note.setObjectName("Muted")
        self.hw_note.setWordWrap(True)
        hw.addWidget(self.hw_note)
        hw.addStretch(1)
        hrow = QHBoxLayout()
        self.btn_apply = QPushButton(T("act.apply"))
        self.btn_apply.setObjectName("Accent")
        self.btn_apply.clicked.connect(self._apply_hw)
        self.btn_reset = QPushButton(T("act.discard"))
        self.btn_reset.clicked.connect(lambda: self._fill_hw())
        hrow.addStretch(1)
        hrow.addWidget(self.btn_reset)
        hrow.addWidget(self.btn_apply)
        hw.addLayout(hrow)

        self.tab_net = QWidget()
        nv = QVBoxLayout(self.tab_net)
        self.net_tbl = QTableWidget(0, 3)
        self.net_tbl.setHorizontalHeaderLabels([T("det.mac"), T("det.model"), T("det.source")])
        self.net_tbl.horizontalHeader().setStretchLastSection(True)
        self.net_tbl.setColumnWidth(0, 150)
        self.net_tbl.setColumnWidth(1, 90)
        self.net_tbl.verticalHeader().setVisible(False)
        nv.addWidget(self.net_tbl, 1)
        nrow = QGridLayout()
        nrow.setSpacing(6)
        self.net_model = QComboBox()
        self.net_model.addItems(NIC_MODELS)
        b_add = QPushButton(T("act.add"))
        b_add.clicked.connect(self._nic_add)
        b_del = QPushButton(T("act.remove"))
        b_del.clicked.connect(self._nic_del)
        b_mod = QPushButton(T("det.model_apply"))
        b_mod.clicked.connect(self._nic_model)
        nrow.addWidget(self.net_model, 0, 0)
        nrow.addWidget(b_mod, 0, 1)
        nrow.addWidget(b_add, 1, 0)
        nrow.addWidget(b_del, 1, 1)
        nv.addLayout(nrow)

        self.tab_disk = QWidget()
        dv = QVBoxLayout(self.tab_disk)
        self.disk_tbl = QTableWidget(0, 3)
        self.disk_tbl.setHorizontalHeaderLabels([T("det.dev"), T("det.bus"), T("det.file")])
        self.disk_tbl.horizontalHeader().setStretchLastSection(True)
        self.disk_tbl.verticalHeader().setVisible(False)
        self.disk_tbl.setColumnWidth(0, 100)
        self.disk_tbl.setColumnWidth(1, 70)
        dv.addWidget(self.disk_tbl, 1)
        drow = QGridLayout()
        drow.setSpacing(6)
        b_disk = QPushButton(T("det.add_disk"))
        b_disk.clicked.connect(self._disk_add)
        b_iso = QPushButton(T("det.attach_iso"))
        b_iso.clicked.connect(self._iso_attach)
        b_ej = QPushButton(T("det.eject_iso"))
        b_ej.clicked.connect(self._iso_eject)
        b_rmd = QPushButton(T("act.remove"))
        b_rmd.setObjectName("Danger")
        b_rmd.clicked.connect(self._disk_del)
        drow.addWidget(b_disk, 0, 0)
        drow.addWidget(b_iso, 0, 1)
        drow.addWidget(b_ej, 1, 0)
        drow.addWidget(b_rmd, 1, 1)
        dv.addLayout(drow)
        self.disk_tbl.setContextMenuPolicy(Qt.CustomContextMenu)
        self.disk_tbl.customContextMenuRequested.connect(self._disk_menu)

        self.tab_snap = QWidget()
        sv = QVBoxLayout(self.tab_snap)
        self.snap_list = QListWidget()
        sv.addWidget(self.snap_list, 1)
        srow = QHBoxLayout()
        b_new = QPushButton(T("det.new_snap"))
        b_new.setObjectName("Accent")
        b_new.clicked.connect(self._snap_new)
        b_rev = QPushButton(T("det.revert"))
        b_rev.clicked.connect(self._snap_revert)
        b_dels = QPushButton(T("act.remove"))
        b_dels.setObjectName("Danger")
        b_dels.clicked.connect(self._snap_del)
        srow.addWidget(b_new)
        srow.addWidget(b_rev)
        srow.addStretch(1)
        srow.addWidget(b_dels)
        sv.addLayout(srow)

        self.tabs.addTab(self.tab_overview, T("det.overview"))
        self.tabs.addTab(self.tab_hw, T("det.hw"))
        self.tabs.addTab(self.tab_net, T("det.net"))
        self.tabs.addTab(self.tab_disk, T("det.disks"))
        self.tabs.addTab(self.tab_snap, T("det.snaps"))
        self.tabs.setEnabled(False)
        self._fill_overview_static(None)

    def set_vm(self, vm):
        self.vm = vm
        if not vm:
            self.icon_lbl.clear()
            self.title_lbl.setText(T("det.no_vm"))
            self._set_state_slot(None)
            self.tabs.setEnabled(False)
            return
        self.icon_lbl.setPixmap(widgets.chip_pixmap(vm.os_id, 44))
        self.title_lbl.setText(vm.name)
        self._set_state_slot(widgets.state_label(vm.state))
        self.tabs.setEnabled(True)
        self._fill_overview_static(vm)
        self._fill_hw()
        self._fill_net()
        self._fill_disk()
        self._fill_snaps()

    def _set_state_slot(self, lbl):
        while self.state_slot.count():
            it = self.state_slot.takeAt(0)
            if it.widget():
                it.widget().deleteLater()
        if lbl:
            self.state_slot.addWidget(lbl)
            self.state_slot.addStretch(1)

    def _fill_overview_static(self, vm):
        while self.info_form.rowCount():
            self.info_form.removeRow(self.info_form.rowCount() - 1)
        if not vm:
            return
        self.info_form.addRow(T("det.os"), QLabel(vm.os_name))
        vcpu_txt = str(vm.vcpus)
        mem_txt = widgets.fmt_mb(vm.maxmem_mb)
        if vm.state in (1, 2, 3, 7):
            live_v = getattr(vm, "live_vcpus", vm.vcpus)
            live_m = getattr(vm, "live_maxmem_mb", vm.maxmem_mb)
            if live_v != vm.vcpus:
                vcpu_txt = "%d (%s %d)" % (vm.vcpus, T("det.now"), live_v)
            if live_m != vm.maxmem_mb:
                mem_txt = "%s (%s %s)" % (widgets.fmt_mb(vm.maxmem_mb), T("det.now"),
                                          widgets.fmt_mb(live_m))
        self.info_form.addRow(T("det.vcpu"), QLabel(vcpu_txt))
        self.info_form.addRow(T("pgstats.mem"), QLabel(mem_txt))
        self.info_form.addRow(T("det.uuid"), QLabel(vm.uuid))
        self.info_form.addRow(T("act.autostart"), QLabel("✓" if vm.autostart else "-"))

    def update_stats(self, st, cpu_hist, ram_hist):
        if not self.vm:
            return
        self.cpu_spark.set_data(cpu_hist)
        used = st["mem"]
        self.ram_spark.set_data(ram_hist, max_val=st["max"] or 1)
        self.cpu_cap.setText("%s: %.0f%%" % (T("pgstats.cpu"), st["cpu"]))
        self.ram_cap.setText("%s: %s / %s" % (T("pgstats.mem"),
                                               widgets.fmt_mb(used), widgets.fmt_mb(st["max"])))
        if st["state"] != (self.vm.state if hasattr(self, "vm") else None):
            self._set_state_slot(widgets.state_label(st["state"]))

    def _sel(self):
        return self.vm.name if self.vm else None

    def _wrap(self, fn, *a, **kw):
        try:
            fn(*a, **kw)
            self.changed.emit()
            return True
        except Exception as e:
            show_error(self, e)
            return False

    def _start(self):
        if self._sel():
            self._wrap(self.b.start, self._sel())

    def _stop(self):
        if self._sel() and confirm(self, T("act.stop") + "?"):
            self._wrap(self.b.shutdown, self._sel())

    def _console(self):
        if not self._sel():
            return
        try:
            exe, args = self.b.console_cmd(self.vm)
            from PySide6.QtCore import QProcess
            QProcess.startDetached(exe, args)
        except Exception as e:
            show_error(self, T("m.console_fail", e=str(e)) + "\n" + T("m.install_viewer"))

    def _ram_sync(self, v):
        if self.f_ram_s.value() != v and self.f_ram_s.maximum() >= v:
            self.f_ram_s.blockSignals(True)
            self.f_ram_s.setValue(v)
            self.f_ram_s.blockSignals(False)

    def _ram_sync_s(self, v):
        if self.f_ram.value() != v:
            self.f_ram.blockSignals(True)
            self.f_ram.setValue(v)
            self.f_ram.blockSignals(False)

    def _fill_hw(self):
        if not self._sel():
            return
        try:
            hw = self.b.hw_read(self._sel())
        except Exception as e:
            show_error(self, e)
            return
        self.hw_base = hw
        self.f_vcpu.setValue(hw["vcpu"])
        self.f_ram.setValue(hw["ram"])
        self.f_ram_s.setValue(hw["ram"])
        self.f_kvm.setChecked(hw["kvm"])
        self.f_tcg.setChecked(not hw["kvm"])
        mi = self.f_machine.findText(hw["machine"])
        if mi < 0:
            self.f_machine.addItem(hw["machine"])
            mi = self.f_machine.findText(hw["machine"])
        self.f_machine.setCurrentIndex(mi)
        self.f_fw.setCurrentIndex(1 if hw["uefi"] else 0)
        self.f_tpm.setChecked(hw["tpm"])
        vi = self.f_video.findText(hw["video"])
        self.f_video.setCurrentIndex(vi if vi >= 0 else 2)
        self.f_auto.setChecked(hw["autostart"])
        self.hw_note.setText(T("det.live_note") if self.vm.running else T("det.off_note"))

    def _apply_hw(self):
        if not self._sel():
            return
        vals = {
            "vcpu": self.f_vcpu.value(),
            "ram": self.f_ram.value(),
            "kvm": self.f_kvm.isChecked(),
            "machine": self.f_machine.currentText(),
            "uefi": self.f_fw.currentData() == "uefi",
            "tpm": self.f_tpm.isChecked(),
            "video": self.f_video.currentText(),
            "autostart": self.f_auto.isChecked(),
        }
        if not self._sel():
            return
        try:
            res = self.b.hw_apply(self._sel(), vals)
            if res and res.get("deferred"):
                show_info(self, T("det.deferred"))
            self.changed.emit()
        except Exception as e:
            show_error(self, e)

    def _fill_net(self):
        if not self._sel():
            return
        try:
            nics = self.b.nics_read(self._sel())
        except Exception:
            nics = []
        self.net_tbl.setRowCount(0)
        for n in nics:
            r = self.net_tbl.rowCount()
            self.net_tbl.insertRow(r)
            for c, val in enumerate((n["mac"], n["model"], n["source"] + (" (%s)" % n["kind"] if n["kind"] else ""))):
                self.net_tbl.setItem(r, c, _tw_item(val))

    def _nic_cur_mac(self):
        r = self.net_tbl.currentRow()
        if r < 0:
            return None
        it = self.net_tbl.item(r, 0)
        return it.text() if it else None

    def _nic_add(self):
        if self._sel():
            self._wrap(self.b.nic_add, self._sel(), self.net_model.currentText())

    def _nic_del(self):
        mac = self._nic_cur_mac()
        if mac and self._sel():
            self._wrap(self.b.nic_remove, self._sel(), mac)

    def _nic_model(self):
        mac = self._nic_cur_mac()
        if mac and self._sel():
            self._wrap(self.b.nic_set_model, self._sel(), mac, self.net_model.currentText())

    def _fill_disk(self):
        if not self._sel():
            return
        try:
            disks = self.b.disks_read(self._sel())
        except Exception:
            disks = []
        self.disk_tbl.setRowCount(0)
        for d in disks:
            r = self.disk_tbl.rowCount()
            self.disk_tbl.insertRow(r)
            name = d["target"] + (" (ISO)" if d["device"] == "cdrom" else "")
            self.disk_tbl.setItem(r, 0, _tw_item(name))
            self.disk_tbl.setItem(r, 1, _tw_item(d["bus"]))
            fit = _tw_item(d["file"] or "-")
            fit.setToolTip(d["file"] or "")
            self.disk_tbl.setItem(r, 2, fit)

    def _disk_cur_target(self):
        r = self.disk_tbl.currentRow()
        if r < 0:
            return None
        it = self.disk_tbl.item(r, 0)
        return it.text().replace(" (ISO)", "") if it else None

    def _disk_add(self):
        if not self._sel():
            return
        dlg = AddDiskDialog(self)
        if dlg.exec() and dlg.values()["size_gb"]:
            self._wrap(self.b.add_disk, self._sel(), dlg.values()["size_gb"], dlg.values()["bus"])

    def _iso_attach(self):
        if not self._sel():
            return
        dlg = FilePickerDialog(self, self.b._paths()["iso"], mode="file",
                               name_filters=("*.iso",))
        if dlg.exec() and dlg.result_path:
            self._wrap(self.b.attach_iso, self._sel(), dlg.result_path)

    def _iso_eject(self):
        if self._sel():
            self._wrap(self.b.attach_iso, self._sel(), None)

    def _disk_del(self):
        tgt = self._disk_cur_target()
        if tgt and self._sel():
            if confirm(self, T("act.remove") + ": " + tgt + "?"):
                self._wrap(self.b.remove_disk, self._sel(), tgt)

    def _disk_menu(self, pos):
        if not self._sel():
            return
        tgt = self._disk_cur_target()
        if not tgt:
            return
        m = QMenu(self)
        sub = m.addMenu(T("det.bus") + ": " + tgt)
        for bus in BUS_OPTS:
            act = sub.addAction(bus)
            act.triggered.connect(lambda _=False, b=bus: self._wrap(self.b.set_disk_bus, self._sel(), tgt, b))
        m.exec(self.disk_tbl.mapToGlobal(pos))

    def _fill_snaps(self):
        if not self._sel():
            return
        try:
            snaps = self.b.snapshots(self._sel())
        except Exception:
            snaps = []
        self.snap_list.clear()
        if not snaps:
            it = QListWidgetItem(T("det.no_snaps"))
            it.setFlags(Qt.NoItemFlags)
            self.snap_list.addItem(it)
            return
        for s in snaps:
            when = s["created"]
            txt = s["name"] + ("  ·  " + s["desc"] if s["desc"] else "")
            it = QListWidgetItem(txt)
            it.setData(Qt.UserRole, s["name"])
            self.snap_list.addItem(it)

    def _snap_cur(self):
        it = self.snap_list.currentItem()
        return it.data(Qt.UserRole) if it and it.data(Qt.UserRole) else None

    def _snap_new(self):
        if not self._sel():
            return
        dlg = SnapshotDialog(self, self.vm.name)
        if dlg.exec():
            v = dlg.values()
            if v["name"]:
                self._wrap(self.b.snap_create, self._sel(), v["name"], v["desc"])

    def _snap_revert(self):
        s = self._snap_cur()
        if s and self._sel():
            self._wrap(self.b.snap_revert, self._sel(), s)

    def _snap_del(self):
        s = self._snap_cur()
        if s and self._sel() and confirm(self, T("act.remove") + ": " + s + "?"):
            self._wrap(self.b.snap_delete, self._sel(), s)


def _tw_item(text):
    from PySide6.QtWidgets import QTableWidgetItem
    it = QTableWidgetItem(text)
    it.setFlags(it.flags() & ~Qt.ItemIsEditable)
    return it
