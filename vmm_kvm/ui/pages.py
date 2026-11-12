# -*- coding: utf-8 -*-
import os

from PySide6.QtCore import QUrl, Qt, Signal
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (QCheckBox, QComboBox, QFormLayout,
                               QGridLayout, QGroupBox, QHBoxLayout, QLabel,
                               QLineEdit, QListWidget, QListWidgetItem,
                               QProgressBar, QPushButton, QTableWidget,
                               QVBoxLayout, QTableWidgetItem, QWidget)

from .. import i18n, osdata
from . import theme, widgets
from .dialogs import (AddSSHDialog, FilePickerDialog, NewNetworkDialog,
                      NewPoolDialog, ServicesDialog, show_error, show_info)

T = lambda key, **kw: i18n.t(key, **kw)


def _item(text):
    it = QTableWidgetItem(str(text))
    it.setFlags(it.flags() & ~Qt.ItemIsEditable)
    return it


class NetworksPage(QWidget):
    def __init__(self, backend, parent=None):
        super().__init__(parent)
        self.b = backend
        v = QVBoxLayout(self)
        v.setContentsMargins(14, 10, 14, 10)
        top = QHBoxLayout()
        title = QLabel(T("pgnet.title"))
        title.setObjectName("H1")
        top.addWidget(title)
        top.addStretch(1)
        b_new = QPushButton(T("pgnet.new"))
        b_new.setObjectName("Accent")
        b_new.clicked.connect(self._new_net)
        top.addWidget(b_new)
        v.addLayout(top)

        self.tbl = QTableWidget(0, 5)
        self.tbl.setHorizontalHeaderLabels([T("pgnet.name"), T("pgnet.state"),
                                            T("pgnet.mode"), T("pgnet.bridge"),
                                            T("pgnet.autostart")])
        self.tbl.horizontalHeader().setStretchLastSection(True)
        self.tbl.verticalHeader().setVisible(False)
        self.tbl.setColumnWidth(0, 160)
        v.addWidget(self.tbl, 1)

        row = QHBoxLayout()
        self.chk_auto = QCheckBox(T("pgnet.autostart"))
        self.chk_auto.toggled.connect(self._toggle_auto)
        b_start = QPushButton(T("act.start"))
        b_start.clicked.connect(lambda: self._act("start"))
        b_stop = QPushButton(T("act.stop"))
        b_stop.clicked.connect(lambda: self._act("stop"))
        row.addWidget(self.chk_auto)
        row.addWidget(b_start)
        row.addWidget(b_stop)
        row.addStretch(1)
        hint = QLabel("session: user-сеть QEMU (SLIRP) · system: NAT 192.168.122.0/24 (dnsmasq/passt)")
        hint.setObjectName("Muted")
        row.addWidget(hint)
        v.addLayout(row)
        self._loading = False

    def refresh(self):
        self._loading = True
        try:
            nets = self.b.networks()
        except Exception:
            nets = []
        self.tbl.setRowCount(0)
        for n in nets:
            r = self.tbl.rowCount()
            self.tbl.insertRow(r)
            self.tbl.setItem(r, 0, _item(n["name"]))
            self.tbl.setItem(r, 1, _item(T("pgnet.active") if n["active"] else T("pgnet.inactive")))
            self.tbl.setItem(r, 2, _item(n["mode"]))
            self.tbl.setItem(r, 3, _item(n["bridge"]))
            self.tbl.setItem(r, 4, _item("✓" if n["autostart"] else "-"))
            self.tbl.item(r, 1).setForeground(Qt.green if n["active"] else theme.MUTED)
        self._loading = False

    def _sel_name(self):
        r = self.tbl.currentRow()
        if r < 0:
            show_info(self, T("m.please_select"))
            return None
        it = self.tbl.item(r, 0)
        return it.text() if it else None

    def _toggle_auto(self, on):
        if self._loading:
            return
        name = self._sel_name()
        if name:
            try:
                self.b.net_autostart(name, on)
                self.refresh()
            except Exception as e:
                show_error(self, e)

    def _act(self, what):
        name = self._sel_name()
        if not name:
            return
        try:
            (self.b.net_start if what == "start" else self.b.net_stop)(name)
            self.refresh()
        except Exception as e:
            show_error(self, e)

    def _new_net(self):
        dlg = NewNetworkDialog(self)
        if dlg.exec():
            val = dlg.values()
            if val["name"] and val["cidr"]:
                try:
                    self.b.net_create_nat(val["name"], val["cidr"])
                    self.refresh()
                except Exception as e:
                    show_error(self, e)


class StoragePage(QWidget):
    def __init__(self, backend, cfg, parent=None):
        super().__init__(parent)
        self.b = backend
        self.cfg = cfg
        v = QVBoxLayout(self)
        v.setContentsMargins(14, 10, 14, 10)
        title = QLabel(T("pgstore.title"))
        title.setObjectName("H1")
        v.addWidget(title)

        base_box = QGroupBox(T("pgstore.base"))
        bv = QVBoxLayout(base_box)
        self.base_lbl = QLabel("")
        self.base_lbl.setTextInteractionFlags(Qt.TextSelectableByMouse)
        bv.addWidget(self.base_lbl)
        st = QLabel(T("pgstore.struct"))
        st.setObjectName("Muted")
        st.setWordWrap(True)
        bv.addWidget(st)
        brow = QHBoxLayout()
        b_open = QPushButton(T("act.open_folder"))
        b_open.clicked.connect(self._open_dir)
        b_recreate = QPushButton(T("pgstore.recreate"))
        b_recreate.clicked.connect(self._recreate)
        brow.addWidget(b_open)
        brow.addWidget(b_recreate)
        brow.addStretch(1)
        bv.addLayout(brow)
        v.addWidget(base_box)

        self.tbl = QTableWidget(0, 6)
        self.tbl.setHorizontalHeaderLabels([T("pgstore.pool"), T("pgstore.type"),
                                            T("pgstore.state"), T("pgstore.used"),
                                            T("pgstore.total"), T("pgstore.path")])
        self.tbl.horizontalHeader().setStretchLastSection(True)
        self.tbl.verticalHeader().setVisible(False)
        v.addWidget(self.tbl, 1)

        row = QHBoxLayout()
        b_act = QPushButton(T("pgstore.activate"))
        b_act.clicked.connect(lambda: self._pool(True))
        b_deact = QPushButton(T("pgstore.deactivate"))
        b_deact.clicked.connect(lambda: self._pool(False))
        b_new = QPushButton(T("pgstore.new"))
        b_new.setObjectName("Accent")
        b_new.clicked.connect(self._new_pool)
        row.addWidget(b_act)
        row.addWidget(b_deact)
        row.addStretch(1)
        row.addWidget(b_new)
        v.addLayout(row)

    def refresh(self):
        from .. import config
        p = config.paths(self.cfg)
        self.base_lbl.setText(p["base"])
        try:
            pools = self.b.pools()
        except Exception:
            pools = []
        self.tbl.setRowCount(0)
        for pl in pools:
            r = self.tbl.rowCount()
            self.tbl.insertRow(r)
            self.tbl.setItem(r, 0, _item(pl["name"]))
            self.tbl.setItem(r, 1, _item(pl["type"]))
            self.tbl.setItem(r, 2, _item(T("pgnet.active") if pl["active"] else T("pgnet.inactive")))
            self.tbl.setItem(r, 3, _item(widgets.fmt_gb_from_kib(pl["alloc"])))
            self.tbl.setItem(r, 4, _item(widgets.fmt_gb_from_kib(pl["cap"])))
            self.tbl.setItem(r, 5, _item(pl["path"]))

    def _open_dir(self):
        from .. import config
        p = config.paths(self.cfg)
        QDesktopServices.openUrl(QUrl.fromLocalFile(p["base"]))

    def _recreate(self):
        from .. import config
        config.paths(self.cfg)
        show_info(self, "OK: " + self.cfg.get("base_dir", ""))

    def _sel(self):
        r = self.tbl.currentRow()
        return self.tbl.item(r, 0).text() if r >= 0 and self.tbl.item(r, 0) else None

    def _pool(self, start):
        name = self._sel()
        if not name:
            return
        try:
            (self.b.pool_start if start else self.b.pool_stop)(name)
            self.refresh()
        except Exception as e:
            show_error(self, e)

    def _new_pool(self):
        from .. import config
        dlg = NewPoolDialog(self, config.paths(self.cfg)["base"])
        if dlg.exec():
            val = dlg.values()
            if val["name"] and val["path"]:
                try:
                    self.b.pool_create_dir(val["name"], val["path"])
                    self.refresh()
                except Exception as e:
                    show_error(self, e)


class SettingsPage(QWidget):
    lang_changed = Signal()
    reconnected = Signal(object)

    def __init__(self, backend, cfg, parent=None):
        super().__init__(parent)
        self.b = backend
        self.cfg = cfg
        v = QVBoxLayout(self)
        v.setContentsMargins(14, 10, 14, 10)
        title = QLabel(T("pgset.title"))
        title.setObjectName("H1")
        v.addWidget(title)

        g1 = QGroupBox(T("pgset.lang"))
        f1 = QHBoxLayout(g1)
        self.lang_combo = QComboBox()
        for code in i18n.LANGS:
            self.lang_combo.addItem(i18n.LANG_NAMES[code], code)
        cur = i18n.cur()
        idx = self.lang_combo.findData(cur)
        self.lang_combo.setCurrentIndex(idx if idx >= 0 else 1)
        self.lang_combo.currentIndexChanged.connect(self._lang)
        f1.addWidget(self.lang_combo)
        f1.addStretch(1)
        v.addWidget(g1)

        g2 = QGroupBox(T("pgset.conn"))
        f2 = QVBoxLayout(g2)
        row2 = QHBoxLayout()
        self.conn_combo = QComboBox()
        self.conn_combo.addItem(T("pgset.session"), "session")
        self.conn_combo.addItem(T("pgset.system"), "system")
        cc = self.conn_combo.findData(self.cfg.get("connection", "session"))
        self.conn_combo.setCurrentIndex(cc if cc >= 0 else 0)
        self.conn_combo.currentIndexChanged.connect(lambda _=0: self._reconnect())
        b_rec = QPushButton(T("pgset.reconnect"))
        b_rec.clicked.connect(lambda: self._reconnect())
        self.conn_lbl = QLabel("")
        self.conn_lbl.setObjectName("Muted")
        row2.addWidget(self.conn_combo)
        row2.addWidget(b_rec)
        row2.addWidget(self.conn_lbl, 1)
        f2.addLayout(row2)

        ssh_lbl = QLabel(T("pgset.ssh"))
        f2.addWidget(ssh_lbl)
        self.ssh_list = QListWidget()
        self.ssh_list.setMaximumHeight(110)
        f2.addWidget(self.ssh_list)
        srow = QHBoxLayout()
        b_ssh_add = QPushButton(T("pgset.ssh_add"))
        b_ssh_add.clicked.connect(self._ssh_add)
        b_ssh_del = QPushButton(T("pgset.ssh_del"))
        b_ssh_del.clicked.connect(self._ssh_del)
        b_ssh_conn = QPushButton(T("act.connect"))
        b_ssh_conn.setObjectName("Accent")
        b_ssh_conn.clicked.connect(self._ssh_conn)
        srow.addWidget(b_ssh_add)
        srow.addWidget(b_ssh_del)
        srow.addStretch(1)
        srow.addWidget(b_ssh_conn)
        f2.addLayout(srow)
        v.addWidget(g2)

        g3 = QGroupBox(T("pgset.base"))
        f3 = QHBoxLayout(g3)
        self.base_edit = QLineEdit(self.cfg.get("base_dir", ""))
        b_pick = QPushButton(T("pgset.pick_folder"))
        b_pick.clicked.connect(self._pick_base)
        b_apply = QPushButton(T("act.apply"))
        b_apply.setObjectName("Accent")
        b_apply.clicked.connect(self._apply_base)
        f3.addWidget(self.base_edit, 1)
        f3.addWidget(b_pick)
        f3.addWidget(b_apply)
        v.addWidget(g3)

        g4 = QGroupBox(T("pgset.services"))
        f4 = QVBoxLayout(g4)
        self.services_btn = QPushButton(T("pgset.services"))
        self.services_btn.setObjectName("Accent")
        self.services_btn.clicked.connect(self._services)
        hint = QLabel(T("pgset.services_hint"))
        hint.setObjectName("Muted")
        hint.setWordWrap(True)
        f4.addWidget(hint)
        f4.addWidget(self.services_btn)
        v.addWidget(g4)

        g5 = QGroupBox(T("pgset.check"))
        f5 = QVBoxLayout(g5)
        self.check_btn = QPushButton(T("pgset.check_btn"))
        self.check_btn.clicked.connect(self._check)
        self.check_lbl = QLabel("")
        self.check_lbl.setWordWrap(True)
        self.check_lbl.setTextInteractionFlags(Qt.TextSelectableByMouse)
        f5.addWidget(self.check_btn)
        f5.addWidget(self.check_lbl)
        v.addWidget(g5)
        v.addStretch(1)
        self._fill_ssh()

    def _fill_ssh(self):
        self.ssh_list.clear()
        for h in self.cfg.get("ssh_hosts", []):
            it = QListWidgetItem("%s  ·  %s" % (h.get("name", ""), h.get("uri", "")))
            it.setData(Qt.UserRole, h)
            self.ssh_list.addItem(it)

    def _lang(self):
        code = self.lang_combo.currentData()
        self.cfg["lang"] = code
        i18n.set_lang(code)
        self.lang_changed.emit()

    def _reconnect(self, kind=None):
        kind = kind or self.conn_combo.currentData()
        self.cfg["connection"] = kind
        self.reconnected.emit()

    def _pick_base(self):
        start = os.path.expanduser(self.cfg.get("base_dir", "~"))
        dlg = FilePickerDialog(self, start, mode="dir")
        if dlg.exec() and dlg.result_path:
            self.base_edit.setText(dlg.result_path)

    def _apply_base(self):
        self.cfg["base_dir"] = self.base_edit.text().strip() or "~/VirtualMachines"
        from .. import config
        config.paths(self.cfg)
        show_info(self, "OK: " + self.cfg["base_dir"])

    def _ssh_add(self):
        dlg = AddSSHDialog(self)
        if dlg.exec():
            v = dlg.values()
            if v["uri"]:
                hosts = self.cfg.setdefault("ssh_hosts", [])
                hosts.append(v)
                self._fill_ssh()

    def _ssh_del(self):
        it = self.ssh_list.currentItem()
        if it:
            self.cfg.get("ssh_hosts", []).remove(it.data(Qt.UserRole))
            self._fill_ssh()

    def _ssh_conn(self):
        it = self.ssh_list.currentItem()
        if not it:
            return
        h = it.data(Qt.UserRole)
        self.reconnected.emit(h)

    def _services(self):
        dlg = ServicesDialog(self, self.b)
        dlg.exec()

    def _check(self):
        lines = []
        for name, ok in self.b.check_deps():
            lines.append("%s: %s" % (name, "✓ " + T("chk.ok") if ok else "✗ " + T("chk.missing")))
        self.check_lbl.setText("\n".join(lines))


class StatsPage(QWidget):
    def __init__(self, backend, parent=None):
        super().__init__(parent)
        self.b = backend
        v = QVBoxLayout(self)
        v.setContentsMargins(14, 10, 14, 10)
        title = QLabel(T("pgstats.title"))
        title.setObjectName("H1")
        v.addWidget(title)

        grid = QGridLayout()
        grid.setSpacing(12)
        self.cpu_spark = widgets.Sparkline(theme.ACCENT, 100, 80)
        self.cpu_lbl = QLabel("0%")
        self.cpu_lbl.setObjectName("H1")
        cpuw = QWidget()
        cv = QVBoxLayout(cpuw)
        cv.setContentsMargins(10, 8, 10, 8)
        cv.addWidget(self.cpu_lbl)
        cv.addWidget(self.cpu_spark)
        self.ram_bar = QProgressBar()
        self.ram_bar.setRange(0, 100)
        self.ram_lbl = QLabel("")
        ramw = QWidget()
        rv = QVBoxLayout(ramw)
        rv.setContentsMargins(10, 8, 10, 8)
        self.ram_lbl.setObjectName("H2")
        rv.addWidget(self.ram_lbl)
        rv.addWidget(self.ram_bar)
        self.node_lbl = QLabel("")
        self.node_lbl.setWordWrap(True)
        self.ver_lbl = QLabel("")
        self.ver_lbl.setObjectName("Muted")
        grid.addWidget(cpuw, 0, 0)
        grid.addWidget(ramw, 0, 1)
        grid.addWidget(self.node_lbl, 0, 2)
        grid.addWidget(self.ver_lbl, 1, 0, 1, 3)
        v.addLayout(grid)

        self.vms_lbl = QLabel(T("pgstats.vms"))
        self.vms_lbl.setObjectName("H2")
        v.addWidget(self.vms_lbl)
        self.tbl = QTableWidget(0, 3)
        self.tbl.setHorizontalHeaderLabels([T("det.name"), T("pgstats.cpu"), T("pgstats.mem")])
        self.tbl.horizontalHeader().setStretchLastSection(True)
        self.tbl.verticalHeader().setVisible(False)
        v.addWidget(self.tbl, 1)

    def update(self, host, vms, stats):
        self.cpu_lbl.setText("%.0f%%" % host["cpu"])
        total = host["mem_total"] or 1
        used = host["mem_used"]
        self.ram_bar.setValue(int(100 * used / total))
        self.ram_lbl.setText("%s / %s" % (widgets.fmt_mb(used), widgets.fmt_mb(total)))
        kvm_txt = T("pgstats.kvm_ok") if host["kvm"] else T("pgstats.kvm_no")
        self.node_lbl.setText(
            "%s\n%s\n%s\n%s" % (
                host.get("distro") or "Linux",
                T("host.kernel", k=host["kernel"]),
                T("pgstats.cpus", n=host["cpus"]),
                kvm_txt))
        vers = host.get("versions", {})
        def ver(num):
            if not num:
                return "-"
            return "%d.%d.%d" % (num // 1000000, (num % 1000000) // 1000, num % 1000)
        self.ver_lbl.setText("libvirt %s · QEMU %s · loadavg: %s" % (
            ver(vers.get("libvirt", 0)), ver(vers.get("qemu", 0)), host.get("load") or "-"))
        self.tbl.setRowCount(0)
        for vm in vms:
            st = stats.get(vm.uuid, {})
            if not st or st.get("state") not in (1, 3):
                continue
            r = self.tbl.rowCount()
            self.tbl.insertRow(r)
            self.tbl.setItem(r, 0, _item(vm.name))
            self.tbl.setItem(r, 1, _item("%.0f%%" % st["cpu"]))
            self.tbl.setItem(r, 2, _item(widgets.fmt_mb(st["mem"])))
        self.cpu_spark.set_data(self._hist(host["cpu"]))

    def _hist(self, v):
        if not hasattr(self, "_host_hist"):
            self._host_hist = []
        self._host_hist = (self._host_hist + [v])[-60:]
        return self._host_hist
