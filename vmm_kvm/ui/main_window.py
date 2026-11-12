# -*- coding: utf-8 -*-
import json
import os
import subprocess

from PySide6.QtCore import QSize, Qt, QTimer
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (QButtonGroup, QFrame, QHBoxLayout, QLabel,
                               QLineEdit, QListWidget, QListWidgetItem,
                               QMainWindow, QMenu, QStackedWidget, QSplitter,
                               QToolButton, QVBoxLayout, QWidget)

from .. import backend as be_mod
from .. import config, i18n, osdata
from . import theme, widgets
from .create_dialog import CreateDialog
from .details import DetailsPanel
from .dialogs import SnapshotDialog, confirm, show_error, show_info
from .pages import NetworksPage, SettingsPage, StatsPage, StoragePage

T = lambda key, **kw: i18n.t(key, **kw)

SHUTDOWN_WAIT = 15


class MainWindow(QMainWindow):
    def __init__(self, cfg, smoke=False):
        super().__init__()
        self.cfg = cfg
        self.smoke = smoke
        self.b = be_mod.Backend(cfg)
        self.vms = []
        self.stats_map = {}
        self.hist = {}
        self.cards = {}
        self.selected_uuid = None
        self._by_uuid = {}
        self.paths = config.paths(cfg)
        self._connect_initial()

        self.setWindowTitle("VMM-KVM")
        self.resize(int(cfg["win"].get("w", 1280)), int(cfg["win"].get("h", 800)))
        self._build()
        self._nav(0)

        self.t_stats = QTimer(self)
        self.t_stats.timeout.connect(self._tick_stats)
        self.t_stats.start(1500)
        self.t_scan = QTimer(self)
        self.t_scan.timeout.connect(self.refresh_all)
        self.t_scan.start(8000)
        self.refresh_all()

    def _connect_initial(self):
        self.conn_kind = self.cfg.get("connection", "session")
        try:
            self.b.connect(self.conn_kind)
            return
        except Exception:
            pass
        if self.conn_kind != "session":
            try:
                self.b.connect("session")
                self.conn_kind = "session"
                return
            except Exception:
                pass
        self.b.conn = None

    def reconnect(self, kind=None, uri=None):
        self.b.close()
        try:
            target = self.b.connect(kind, uri)
            if kind:
                self.cfg["connection"] = kind
            self.conn_kind = kind or ("custom" if uri else self.conn_kind)
            self.conn_lbl.setText(T("m.connected", uri=target))
        except Exception as e:
            self.b.conn = None
            show_error(self, T("m.conn_failed", e=str(e)))
        self.refresh_all()

    def _build(self):
        central = QWidget()
        root = QHBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        root.addWidget(self._build_sidebar())
        root.addWidget(self._build_right(), 1)
        self.setCentralWidget(central)

    def _build_sidebar(self):
        side = QFrame()
        side.setObjectName("Sidebar")
        side.setFixedWidth(236)
        v = QVBoxLayout(side)
        v.setContentsMargins(10, 12, 10, 10)
        v.setSpacing(6)
        logo_row = QHBoxLayout()
        logo = QLabel()
        logo.setPixmap(QIcon(os.path.join(os.path.dirname(__file__), "..",
                                          "assets", "icons", "app.svg")).pixmap(26, 26))
        title = QLabel("VMM-KVM")
        title.setObjectName("SideTitle")
        logo_row.addWidget(logo)
        logo_row.addWidget(title)
        logo_row.addStretch(1)
        v.addLayout(logo_row)

        self.nav_group = QButtonGroup(self)
        self.nav_group.setExclusive(True)
        self.nav_group.idClicked.connect(self._nav)
        for idx, (key, glyph) in enumerate((("nav.vms", "vm"), ("nav.network", "net"),
                                            ("nav.storage", "disk"), ("nav.settings", "gear"),
                                            ("nav.stats", "chart"))):
            btn = QToolButton()
            btn.setObjectName("NavBtn")
            btn.setText("  " + T(key))
            btn.setIcon(widgets.glyph_icon(glyph, theme.ACCENT if idx == 0 else theme.MUTED))
            btn.setCheckable(True)
            btn.setChecked(idx == 0)
            self.nav_group.addButton(btn, idx)
            v.addWidget(btn)
        v.addStretch(1)
        self.svc_lbl = QLabel("")
        self.svc_lbl.setObjectName("SideStatus")
        self.conn_lbl = QLabel(self.b.uri() or "-")
        self.conn_lbl.setObjectName("SideStatus")
        self.conn_lbl.setWordWrap(True)
        k_lbl = QLabel(T("host.kernel", k=os.uname().release))
        k_lbl.setObjectName("SideStatus")
        v.addWidget(self.svc_lbl)
        v.addWidget(self.conn_lbl)
        v.addWidget(k_lbl)
        return side

    def _build_right(self):
        col = QWidget()
        v = QVBoxLayout(col)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(0)

        bar = QFrame()
        bar.setObjectName("Toolbar")
        hb = QHBoxLayout(bar)
        hb.setContentsMargins(12, 8, 12, 8)
        hb.setSpacing(8)
        self.b_new = self._tb_btn("plus", T("act.new"), self._open_create, accent=True)
        self.b_start = self._tb_btn("play", T("act.start"), lambda: self._vm_op("start"))
        self.b_stop = self._tb_btn("power", T("act.stop"), self._shutdown_selected)
        self.b_reboot = self._tb_btn("restart", T("act.reboot"), self._reboot_selected)
        self.b_snap = self._tb_btn("camera", T("act.snapshot"), self._quick_snapshot)
        self.b_console = self._tb_btn("monitor", T("act.console"), lambda: self._vm_op("console"))
        self.search_e = QLineEdit()
        self.search_e.setPlaceholderText(T("act.search_ph"))
        self.search_e.setClearButtonEnabled(True)
        self.search_e.setFixedWidth(240)
        self.search_e.addAction(widgets.glyph_icon("search", theme.MUTED), QLineEdit.LeadingPosition)
        self.search_e.textChanged.connect(self._filter_list)
        hb.addWidget(self.b_new)
        hb.addWidget(self.b_start)
        hb.addWidget(self.b_stop)
        hb.addWidget(self.b_reboot)
        hb.addWidget(self.b_snap)
        hb.addWidget(self.b_console)
        hb.addStretch(1)
        hb.addWidget(self.search_e)
        v.addWidget(bar)

        self.stack = QStackedWidget()
        self.page_vms = QWidget()
        pv = QVBoxLayout(self.page_vms)
        pv.setContentsMargins(8, 8, 8, 8)
        self.empty_lbl = QLabel(
            "<b>%s</b><br><span style='color:%s'>%s</span>" % (
                T("m.no_vms"), theme.MUTED, T("m.no_vms_hint")))
        self.empty_lbl.setAlignment(Qt.AlignCenter)
        self.empty_lbl.setVisible(False)
        self.split = QSplitter(Qt.Horizontal)
        self.listw = QListWidget()
        self.listw.setContextMenuPolicy(Qt.CustomContextMenu)
        self.listw.customContextMenuRequested.connect(self._vm_menu)
        self.listw.currentItemChanged.connect(self._on_select)
        self.details = DetailsPanel(self.b, self.cfg)
        self.details.changed.connect(self.refresh_all)
        self.split.addWidget(self.listw)
        self.split.addWidget(self.details)
        self.split.setStretchFactor(0, 1)
        self.split.setStretchFactor(1, 0)
        self.split.setSizes([900, 470])
        pv.addWidget(self.empty_lbl, 1)
        pv.addWidget(self.split, 0)
        self.split.hide()
        self.stack.addWidget(self.page_vms)
        self.page_net = NetworksPage(self.b)
        self.stack.addWidget(self.page_net)
        self.page_store = StoragePage(self.b, self.cfg)
        self.stack.addWidget(self.page_store)
        self.page_set = SettingsPage(self.b, self.cfg)
        self.page_set.lang_changed.connect(self._lang_changed)
        self.page_set.reconnected.connect(self._reconn_from_settings)
        self.stack.addWidget(self.page_set)
        self.page_stats = StatsPage(self.b)
        self.stack.addWidget(self.page_stats)
        v.addWidget(self.stack, 1)
        return col

    def _tb_btn(self, glyph, text, slot, accent=False):
        btn = QToolButton()
        btn.setObjectName("TbAccent" if accent else "TbBtn")
        btn.setText(text if accent else "  " + text)
        btn.setIcon(widgets.glyph_icon(glyph, "#062a26" if accent else theme.ACCENT))
        btn.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        btn.clicked.connect(slot)
        return btn

    def _nav(self, idx):
        self.stack.setCurrentIndex([0, 1, 2, 3, 4][idx] if idx < 5 else 0)
        page = self.stack.currentWidget()
        if hasattr(page, "refresh"):
            page.refresh()
        if page is self.page_stats:
            self._update_stats_page()

    def _open_create(self):
        dlg = CreateDialog(self, self.b, self.cfg, self._switch_conn)
        dlg.exec()
        if dlg.result_name:
            show_info(self, T("m.created", name=dlg.result_name))
            self.refresh_all()
            for uuid, vm in self._by_uuid.items():
                if vm.name == dlg.result_name:
                    self.selected_uuid = uuid
                    self._rebuild_list()
                    self.details.set_vm(self._sel_vm())
                    self._update_toolbar()
                    break

    def _switch_conn(self, uri):
        self.reconnect(uri=uri)
        return self.b.conn is not None

    def _lang_changed(self):
        config.save(self.cfg)
        show_info(self, T("m.lang_restart"))

    def _reconn_from_settings(self, arg=None):
        if isinstance(arg, dict):
            self.reconnect(uri=arg.get("uri"))
        else:
            self.reconnect(kind=self.cfg.get("connection", "session"))

    def refresh_all(self):
        if self.b.conn:
            try:
                self.vms = self.b.domains()
            except Exception:
                self.vms = []
        else:
            self.vms = []
        self._by_uuid = {vm.uuid: vm for vm in self.vms}
        self._rebuild_list()
        self.details.set_vm(self._sel_vm())
        self._update_toolbar()
        svc = self._svc_text()
        self.svc_lbl.setText(svc)
        page = self.stack.currentWidget()
        if page in (self.page_net, self.page_store):
            page.refresh()
        self._update_stats_page()

    def _rebuild_list(self):
        self.listw.blockSignals(True)
        keep = self.selected_uuid
        self.listw.clear()
        self.cards = {}
        filt = self.search_e.text().lower() if hasattr(self, "search_e") else ""
        for vm in self.vms:
            if filt and filt not in vm.name.lower():
                continue
            st = self.stats_map.get(vm.uuid, {"cpu": 0.0, "mem": 0,
                                              "max": vm.maxmem_mb, "state": vm.state})
            it = QListWidgetItem()
            it.setData(Qt.UserRole, vm.uuid)
            card = self._build_card(vm, st)
            it.setSizeHint(QSize(card.sizeHint().width(), card.sizeHint().height() + 6))
            self.listw.addItem(it)
            self.listw.setItemWidget(it, card)
            self.cards[vm.uuid] = card
            if vm.uuid == keep:
                self.listw.setCurrentItem(it)
        self.listw.blockSignals(False)
        if not self.listw.currentItem():
            self.selected_uuid = None
        has_items = self.listw.count() > 0
        self.empty_lbl.setVisible(not has_items)
        self.split.setVisible(has_items)

    def _build_card(self, vm, st):
        card = QWidget()
        h = QHBoxLayout(card)
        h.setContentsMargins(10, 8, 10, 8)
        h.setSpacing(12)
        icon = QLabel()
        icon.setPixmap(widgets.chip_pixmap(vm.os_id, 40))
        icon.setFixedSize(44, 44)
        icon.setAlignment(Qt.AlignCenter)
        h.addWidget(icon)

        col1 = QVBoxLayout()
        name = QLabel(vm.name)
        name.setStyleSheet("font-weight: bold; font-size: 14px; background: transparent;")
        col1.addWidget(name)
        col1.addWidget(widgets.state_label(vm.state))
        h.addLayout(col1, 0)

        card.cpu_v = card.ram_v = card.cpu_spark = card.ram_spark = None
        col2 = QVBoxLayout()
        if vm.running:
            cpu_row = QHBoxLayout()
            cpu_l = QLabel("CPU")
            cpu_l.setObjectName("Muted")
            cpu_l.setStyleSheet("background: transparent;")
            cpu_v = QLabel("%.0f%%" % st["cpu"])
            cpu_v.setStyleSheet("color: %s; background: transparent;" % theme.ACCENT)
            spark = widgets.Sparkline(theme.ACCENT, 100, 30)
            spark.setStyleSheet("background: transparent;")
            hist = self.hist.setdefault(vm.uuid, {"cpu": [], "ram": []})
            spark.set_data(hist["cpu"])
            cpu_row.addWidget(cpu_l)
            cpu_row.addWidget(cpu_v)
            cpu_row.addWidget(spark, 1)
            col2.addLayout(cpu_row)
            ram_row = QHBoxLayout()
            ram_l = QLabel("RAM")
            ram_l.setObjectName("Muted")
            ram_l.setStyleSheet("background: transparent;")
            ram_v = QLabel("%s/%s" % (widgets.fmt_mb(st["mem"]), widgets.fmt_mb(st["max"])))
            ram_v.setStyleSheet("color: %s; background: transparent;" % theme.GREEN)
            rspark = widgets.Sparkline(theme.GREEN, st["max"] or 1, 30)
            rspark.setStyleSheet("background: transparent;")
            rspark.set_data(hist["ram"])
            ram_row.addWidget(ram_l)
            ram_row.addWidget(ram_v)
            ram_row.addWidget(rspark, 1)
            col2.addLayout(ram_row)
            h.addLayout(col2, 1)
            badge = QToolButton()
            badge.setObjectName("TbBtn")
            badge.setText("SPICE/VNC")
            badge.clicked.connect(lambda _=False, n=vm.name: self._console(n))
            h.addWidget(badge)
            card.cpu_v, card.ram_v, card.cpu_spark, card.ram_spark = cpu_v, ram_v, spark, rspark
        else:
            spec = QLabel(T("vm.spec", v=vm.vcpus, r=widgets.fmt_mb(vm.maxmem_mb),
                            d=self._disk_gb(vm)))
            spec.setObjectName("Muted")
            spec.setStyleSheet("background: transparent;")
            col2.addWidget(spec)
            col2.addStretch(1)
            h.addLayout(col2, 1)
        card.setObjectName("VMCard")
        card.setStyleSheet(
            "QWidget#VMCard { background: %s; border: 1px solid %s; border-radius: 10px; }"
            % (theme.CARD, theme.BORDER))
        return card

    def _disk_gb(self, vm):
        try:
            for d in self.b.disks_read(vm.name):
                if d["device"] == "disk" and d["file"]:
                    gb = _file_gb(d["file"])
                    if gb:
                        return "%d %s" % (gb, i18n.t("unit.gb"))
        except Exception:
            pass
        return "-"

    def _filter_list(self, text):
        text = (text or "").lower()
        for i in range(self.listw.count()):
            it = self.listw.item(i)
            uuid = it.data(Qt.UserRole)
            vm = self._by_uuid.get(uuid)
            name = vm.name if vm else ""
            it.setHidden(bool(text) and text not in name.lower())

    def _on_select(self, cur, prev=None):
        uuid = cur.data(Qt.UserRole) if cur else None
        self.selected_uuid = uuid
        self.details.set_vm(self._sel_vm())
        self._update_toolbar()

    def _sel_vm(self):
        return self._by_uuid.get(self.selected_uuid)

    def _update_toolbar(self):
        vm = self._sel_vm()
        on = vm is not None
        self.b_start.setEnabled(on and vm.stopped)
        self.b_stop.setEnabled(on and vm.running)
        self.b_reboot.setEnabled(on and vm.running)
        self.b_snap.setEnabled(on)
        self.b_console.setEnabled(on and (vm.running or vm.paused))

    def _vm_menu(self, pos):
        it = self.listw.itemAt(pos)
        if not it:
            return
        self.listw.setCurrentItem(it)
        vm = self._sel_vm()
        if not vm:
            return
        m = QMenu(self)
        if vm.stopped:
            m.addAction(T("act.start"), lambda: self._do_op(vm, "start"))
        if vm.running:
            m.addAction(T("act.pause"), lambda: self._do_op(vm, "pause"))
        if vm.paused:
            m.addAction(T("act.resume"), lambda: self._do_op(vm, "resume"))
        if vm.running:
            m.addAction(T("act.stop"), lambda: self._stop_vm(vm))
            m.addAction(T("act.forceoff"),
                        lambda: confirm(self, T("m.confirm_force", name=vm.name))
                        and self._do_op(vm, "forceoff"))
            m.addAction(T("act.reboot"), lambda: self._reboot_vm(vm))
            m.addAction(T("act.reset"), lambda: self._do_op(vm, "reset"))
        if vm.running or vm.paused:
            m.addAction(T("act.console"), lambda: self._console(vm.name))
        m.addSeparator()
        m.addAction(T("act.autostart.off" if vm.autostart else "act.autostart.on"),
                    lambda: self._toggle_autostart(vm))
        m.addSeparator()
        m.addAction(T("act.delete"), lambda: self._delete(vm))
        m.exec(self.listw.mapToGlobal(pos))

    def _vm_op(self, what):
        vm = self._sel_vm()
        if not vm:
            show_info(self, T("m.please_select"))
            return
        self._do_op(vm, what)

    def _shutdown_selected(self):
        vm = self._sel_vm()
        if not vm:
            show_info(self, T("m.please_select"))
            return
        self._stop_vm(vm)

    def _reboot_selected(self):
        vm = self._sel_vm()
        if not vm:
            show_info(self, T("m.please_select"))
            return
        self._reboot_vm(vm)

    def _stop_vm(self, vm):
        try:
            self.b.shutdown(vm.name)
        except Exception as e:
            show_error(self, e)
            return
        self._wait_off(vm.name, SHUTDOWN_WAIT)

    def _wait_off(self, name, left):
        vm = next((v for v in self.b.domains() if v.name == name), None)
        if vm is None or vm.stopped:
            self.refresh_all()
            return
        if left <= 0:
            if confirm(self, T("m.shutdown_slow", name=name, s=SHUTDOWN_WAIT)):
                try:
                    self.b.forceoff(name)
                except Exception as e:
                    show_error(self, e)
            self.refresh_all()
            return
        QTimer.singleShot(1000, lambda: self._wait_off(name, left - 1))

    def _reboot_vm(self, vm):
        try:
            old_id = vm.dom.ID()
            self.b.reboot(vm.name)
        except Exception as e:
            show_error(self, e)
            return
        self._wait_reboot(vm.name, old_id, SHUTDOWN_WAIT)

    def _wait_reboot(self, name, old_id, left):
        d = None
        try:
            d = self.b.conn.lookupByName(name)
        except Exception:
            pass
        if d is None or not d.isActive():
            self.refresh_all()
            return
        try:
            if d.ID() != old_id:
                self.refresh_all()
                return
        except Exception:
            pass
        if left <= 0:
            if confirm(self, T("m.reboot_slow", name=name, s=SHUTDOWN_WAIT)):
                try:
                    self.b.reset(name)
                except Exception as e:
                    show_error(self, e)
            self.refresh_all()
            return
        QTimer.singleShot(1000, lambda: self._wait_reboot(name, old_id, left - 1))

    def _do_op(self, vm, what):
        try:
            if what == "start":
                self.b.start(vm.name)
            elif what == "shutdown":
                self.b.shutdown(vm.name)
            elif what == "forceoff":
                self.b.forceoff(vm.name)
            elif what == "reboot":
                self.b.reboot(vm.name)
            elif what == "reset":
                self.b.reset(vm.name)
            elif what == "pause":
                self.b.pause(vm.name)
            elif what == "resume":
                self.b.resume(vm.name)
            elif what == "console":
                self._console(vm.name)
        except Exception as e:
            show_error(self, e)
        self.refresh_all()

    def _delete(self, vm):
        if not confirm(self, T("m.confirm_del", name=vm.name)):
            return
        try:
            self.b.delete(vm.name)
            self.selected_uuid = None
        except Exception as e:
            show_error(self, e)
        self.refresh_all()

    def _toggle_autostart(self, vm):
        try:
            self.b.set_autostart(vm.name, not vm.autostart)
        except Exception as e:
            show_error(self, e)
        self.refresh_all()

    def _console(self, name):
        vm = next((v for v in self.vms if v.name == name), None)
        if not vm:
            return
        try:
            exe, args = self.b.console_cmd(vm)
            from PySide6.QtCore import QProcess
            QProcess.startDetached(exe, args)
        except Exception as e:
            show_error(self, T("m.console_fail", e=str(e)) + "\n" + T("m.install_viewer"))

    def _quick_snapshot(self):
        vm = self._sel_vm()
        if not vm:
            show_info(self, T("m.please_select"))
            return
        dlg = SnapshotDialog(self, vm.name)
        if dlg.exec():
            v = dlg.values()
            try:
                self.b.snap_create(vm.name, v["name"], v["desc"])
            except Exception as e:
                show_error(self, e)
            self.details.set_vm(vm)

    def _tick_stats(self):
        if not self.b.conn:
            return
        changed_state = False
        for vm in self.vms:
            try:
                st = self.b.stats(vm)
            except Exception:
                continue
            old = self.stats_map.get(vm.uuid, {}).get("state")
            if old is not None and old != st["state"]:
                changed_state = True
            self.stats_map[vm.uuid] = st
            hist = self.hist.setdefault(vm.uuid, {"cpu": [], "ram": []})
            if st["state"] == 1:
                hist["cpu"] = (hist["cpu"] + [st["cpu"]])[-60:]
                hist["ram"] = (hist["ram"] + [st["mem"]])[-60:]
            card = self.cards.get(vm.uuid)
            if card and card.cpu_spark:
                card.cpu_spark.set_data(hist["cpu"])
                card.ram_spark.set_data(hist["ram"], max_val=st["max"] or 1)
                card.cpu_v.setText("%.0f%%" % st["cpu"])
                card.ram_v.setText("%s/%s" % (widgets.fmt_mb(st["mem"]), widgets.fmt_mb(st["max"])))
        sel = self._sel_vm()
        if sel and sel.uuid in self.stats_map:
            h = self.hist.setdefault(sel.uuid, {"cpu": [], "ram": []})
            self.details.update_stats(self.stats_map[sel.uuid], h["cpu"], h["ram"])
        self._update_stats_page()
        if changed_state:
            self.refresh_all()

    def _update_stats_page(self):
        if self.stack.currentWidget() is not self.page_stats or not self.b.conn:
            return
        try:
            host = self.b.host_stats()
            self.page_stats.update(host, self.vms, self.stats_map)
        except Exception:
            pass

    def _svc_text(self):
        try:
            r = subprocess.run(["systemctl", "is-active", "libvirtd"],
                               capture_output=True, text=True, timeout=3)
            state = (r.stdout or "").strip()
        except Exception:
            state = ""
        if state == "active":
            return T("svc.on")
        if state == "inactive":
            return T("svc.off")
        return T("svc.checking")


def _file_gb(path):
    try:
        out = subprocess.run(["qemu-img", "info", "-U", "--output=json", path],
                             capture_output=True, text=True, timeout=5).stdout
        size = json.loads(out).get("virtual-size", 0)
        if size:
            return max(1, round(size / (1024 ** 3)))
    except Exception:
        pass
    try:
        return round(os.path.getsize(path) / (1024 ** 3))
    except OSError:
        return 0
