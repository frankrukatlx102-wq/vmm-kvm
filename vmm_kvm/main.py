# -*- coding: utf-8 -*-
import os
import sys


def run(smoke=False):
    from PySide6.QtCore import QTimer
    from PySide6.QtGui import QIcon
    from PySide6.QtWidgets import QApplication

    from . import config, i18n
    from .ui.main_window import MainWindow
    from .ui.theme import apply_theme

    cfg = config.load()
    i18n.set_lang(cfg.get("lang") or i18n.autodetect())

    app = QApplication(sys.argv)
    app.setApplicationName("VMM-KVM")
    app.setApplicationDisplayName("VMM-KVM")
    app.setDesktopFileName("vmm-kvm")
    apply_theme(app)
    icon = os.path.join(os.path.dirname(__file__), "assets", "icons", "app.svg")
    if os.path.exists(icon):
        app.setWindowIcon(QIcon(icon))

    win = MainWindow(cfg, smoke=smoke)
    win.show()
    if smoke:
        QTimer.singleShot(1500, app.quit)

    rc = app.exec()
    config.save(cfg)
    return rc
