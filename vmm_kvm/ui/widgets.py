# -*- coding: utf-8 -*-
import os

from PySide6.QtCore import QByteArray, QPointF, QRectF, Qt
from PySide6.QtGui import (QColor, QFont, QIcon, QPainter, QPainterPath, QPen,
                           QPixmap, QPolygonF)
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtWidgets import QLabel, QWidget

from .. import osdata
from . import theme

GLYPHS = {
    "play":   '<path d="M8 5v14l11-7z"/>',
    "stop":   '<rect x="6" y="6" width="12" height="12" rx="2"/>',
    "pause":  '<rect x="6" y="5" width="4" height="14" rx="1"/><rect x="14" y="5" width="4" height="14" rx="1"/>',
    "restart": '<path d="M12 5V2L7 6l5 4V7c3.3 0 6 2.7 6 6s-2.7 6-6 6-6-2.7-6-6H4c0 4.4 3.6 8 8 8s8-3.6 8-8-3.6-8-8-8z"/>',
    "power":  '<path d="M11 3h2v9h-2zM6.2 6.8a8 8 0 1 0 11.6 0l-1.4 1.4a6 6 0 1 1-8.8 0z"/>',
    "camera": '<path d="M9 3l-2 2H4a2 2 0 0 0-2 2v10a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2V7a2 2 0 0 0-2-2h-3l-2-2H9zm3 5a5 5 0 1 1 0 10 5 5 0 0 1 0-10zm0 2a3 3 0 1 0 0 6 3 3 0 0 0 0-6z"/>',
    "search": '<path d="M10 4a6 6 0 1 0 3.7 10.7l4.8 4.8 1.4-1.4-4.8-4.8A6 6 0 0 0 10 4zm0 2a4 4 0 1 1 0 8 4 4 0 0 1 0-8z"/>',
    "plus":   '<path d="M11 5h2v6h6v2h-6v6h-2v-6H5v-2h6z"/>',
    "monitor": '<path d="M4 4h16a2 2 0 0 1 2 2v9a2 2 0 0 1-2 2h-6v3h3v2H7v-2h3v-3H4a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2zm0 2v9h16V6H4z"/>',
    "check":  '<path d="M9.5 16.2 5.3 12l-1.4 1.4 5.6 5.6 12-12L20.1 5.6z"/>',
    "vm":     '<path d="M4 3h16a2 2 0 0 1 2 2v10a2 2 0 0 1-2 2h-6v2h3v2H7v-2h3v-2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2zm0 2v10h16V5H4z"/>',
    "net":    '<path d="M12 2a4 4 0 0 1 4 4 4 4 0 0 1-3 3.9V13h4a3 3 0 0 1 3 3v2h2v4h-4v-4h-2v4h-8v-4H8v4H4v-4h2v-2a3 3 0 0 1 3-3h4v-3.1A4 4 0 0 1 12 2z"/>',
    "disk":   '<path d="M4 4h16a2 2 0 0 1 2 2v12a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2zm2 5h12V6H6v3zm0 4h4v-2H6v2zm0 3h4v-2H6v2z"/>',
    "gear":   '<path d="M12 8a4 4 0 1 0 0 8 4 4 0 0 0 0-8zm9.4 5.4-2.1.5a7.6 7.6 0 0 1-.8 1.9l1.1 1.9-2 2-1.9-1.1c-.6.4-1.2.6-1.9.8l-.5 2.1h-2.8l-.5-2.1a7.6 7.6 0 0 1-1.9-.8L4.2 20l-2-2 1.1-1.9c-.4-.6-.6-1.2-.8-1.9l-2.1-.5v-2.8l2.1-.5c.2-.7.4-1.3.8-1.9L2.2 5l2-2 1.9 1.1c.6-.4 1.2-.6 1.9-.8l.5-2.1h2.8l.5 2.1c.7.2 1.3.4 1.9.8L15.8 3l2 2-1.1 1.9c.4.6.6 1.2.8 1.9l2.1.5v2.8z"/>',
    "chart":  '<path d="M4 20V4h2v14h14v2H4zm4-3V9h2v8H8zm4 0V5h2v12h-2zm4 0v-6h2v6h-2z"/>',
    "snap":   '<path d="M12 4a8 8 0 1 0 8 8h-2a6 6 0 1 1-6-6V4zm-1 3h2v5h4v2h-6V7z"/>',
}


def glyph_icon(name, color=None, size=18):
    color = color or theme.TEXT
    svg = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" '
           'fill="%s">%s</svg>' % (color, GLYPHS.get(name, GLYPHS["vm"])))
    renderer = QSvgRenderer(QByteArray(svg.encode()))
    pm = QPixmap(size, size)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing)
    renderer.render(p, QRectF(0, 0, size, size))
    p.end()
    return QIcon(pm)


def badge_icon(letter, color, size=64):
    pm = QPixmap(size, size)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing)
    p.setPen(Qt.NoPen)
    p.setBrush(QColor(color))
    p.drawEllipse(4, 4, size - 8, size - 8)
    p.setPen(QColor("#0a141f"))
    f = QFont()
    f.setPixelSize(int(size * 0.45))
    f.setBold(True)
    p.setFont(f)
    p.drawText(pm.rect(), Qt.AlignCenter, (letter or "?").upper()[:2])
    p.end()
    return QIcon(pm)


def os_icon(osid):
    icon_id = osdata.icon_of(osid)
    path = osdata.icon_path(icon_id)
    if path:
        return QIcon(path)
    fam = osdata.family(osid)
    color = osdata.FAMILY_COLORS.get(fam, "#8b949e")
    letter = "?" if osid == "other" else (osid[:2] or "?")
    return badge_icon(letter, color)


def chip_pixmap(osid, size=40):
    base = QPixmap(size, size)
    base.fill(Qt.transparent)
    p = QPainter(base)
    p.setRenderHint(QPainter.Antialiasing)
    p.setPen(Qt.NoPen)
    p.setBrush(QColor(theme.CARD2))
    p.drawRoundedRect(QRectF(0, 0, size, size), 10, 10)
    p.end()
    icon = os_icon(osid)
    pm = icon.pixmap(size - 10, size - 10)
    p2 = QPainter(base)
    x = (size - pm.width()) // 2
    y = (size - pm.height()) // 2
    p2.drawPixmap(x, y, pm)
    p2.end()
    return base


class Sparkline(QWidget):

    def __init__(self, color=theme.ACCENT, max_val=100.0, height=34, parent=None):
        super().__init__(parent)
        self._data = []
        self._color = QColor(color)
        self._max = max_val
        self.setFixedHeight(height)
        self.setMinimumWidth(60)

    def set_data(self, data, max_val=None):
        self._data = list(data)[-60:]
        if max_val:
            self._max = max_val
        self.update()

    def paintEvent(self, ev):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()
        p.setPen(QPen(QColor(theme.BORDER), 1))
        p.drawLine(0, h - 1, w, h - 1)
        if not self._data:
            p.end()
            return
        peak = max(self._max, max(self._data) * 1.15, 1e-6)
        n = len(self._data)
        step = w / max(1, n - 1) if n > 1 else w
        pts = [QPointF(i * step, h - 2 - (v / peak) * (h - 5)) for i, v in enumerate(self._data)]
        path = QPainterPath()
        path.moveTo(pts[0])
        for pt in pts[1:]:
            path.lineTo(pt)
        p.setPen(QPen(self._color, 1.6))
        p.drawPath(path)
        fill = QPainterPath(path)
        fill.lineTo(pts[-1].x(), h - 1)
        fill.lineTo(pts[0].x(), h - 1)
        fill.closeSubpath()
        c = QColor(self._color)
        c.setAlpha(42)
        p.setPen(Qt.NoPen)
        p.setBrush(c)
        p.drawPath(fill)
        p.end()


def state_label(state):
    from .. import i18n
    if state == 1:
        color, key = theme.GREEN, "st.running"
    elif state == 3:
        color, key = theme.AMBER, "st.paused"
    elif state in (4, 5, 6):
        color, key = theme.MUTED, "st.shutoff"
    else:
        color, key = theme.MUTED, "st.other"
    lbl = QLabel("● " + i18n.t(key) if key != "st.other" else "● " + i18n.t("st.other", s=str(state)))
    lbl.setStyleSheet("color: %s; font-size: 12px;" % color)
    return lbl


def fmt_mb(mb):
    from .. import i18n
    if mb >= 1024:
        v = mb / 1024.0
        num = ("%d" % round(v)) if v >= 10 else ("%.1f" % v)
        return "%s %s" % (num, i18n.t("unit.gb"))
    return "%d %s" % (mb, i18n.t("unit.mb"))


def fmt_gb_from_kib(kib):
    from .. import i18n
    if not kib:
        return "-"
    gb = kib / (1024 * 1024.0)
    num = ("%d" % round(gb)) if gb >= 10 else ("%.1f" % gb)
    return "%s %s" % (num, i18n.t("unit.gb"))
