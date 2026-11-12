# -*- coding: utf-8 -*-
import os
import re

ICONS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "icons", "os")

FAMILY_COLORS = {
    "windows": "#0078d4",
    "linux":   "#f2b824",
    "bsd":     "#ab2b28",
    "other":   "#8b949e",
}


def _p(**kw):
    return {
        "vcpu": kw.get("vcpu", 2), "ram": kw.get("ram", 2048), "disk": kw.get("disk", 20),
        "firmware": kw.get("firmware", "bios"), "tpm": kw.get("tpm", False),
        "machine": kw.get("machine", "pc"), "bus": kw.get("bus", "virtio"),
        "net": kw.get("net", "virtio"), "video": kw.get("video", "virtio"),
        "hints": kw.get("hints", []),
    }


OS_DB = {
    "windows-11":   ("Windows 11", "windows-11", "windows", _p(vcpu=4, ram=4096, disk=64, firmware="uefi", tpm=True, machine="q35", bus="sata", net="e1000e", video="qxl", hints=["win_modern", "win11"])),
    "windows-10":   ("Windows 10", "windows-10", "windows", _p(vcpu=4, ram=4096, disk=64, firmware="bios", machine="pc", bus="sata", net="e1000e", video="qxl", hints=["win_modern"])),
    "windows-8":    ("Windows 8", "windows-8", "windows", _p(vcpu=2, ram=2048, disk=40, firmware="bios", machine="pc", bus="sata", net="e1000e", video="qxl", hints=["win_modern"])),
    "windows-8.1":  ("Windows 8.1", "windows-8", "windows", _p(vcpu=2, ram=2048, disk=40, firmware="bios", machine="pc", bus="sata", net="e1000e", video="qxl", hints=["win_modern"])),
    "windows-7":    ("Windows 7", "windows-7", "windows", _p(vcpu=2, ram=2048, disk=40, firmware="bios", machine="pc", bus="ide", net="e1000", video="vga", hints=["win_legacy"])),
    "windows-vista": ("Windows Vista", "windows-vista", "windows", _p(vcpu=2, ram=2048, disk=40, firmware="bios", machine="pc", bus="ide", net="e1000", video="vga", hints=["win_legacy"])),
    "windows-xp":   ("Windows XP", "windows-xp", "windows", _p(vcpu=1, ram=1024, disk=20, firmware="bios", machine="pc", bus="ide", net="rtl8139", video="vga", hints=["win_legacy"])),
    "windows-2000": ("Windows 2000", "windows-flag", "windows", _p(vcpu=1, ram=512, disk=16, firmware="bios", machine="pc", bus="ide", net="rtl8139", video="vga", hints=["win_legacy"])),
    "windows-me":   ("Windows ME", "windows-flag", "windows", _p(vcpu=1, ram=256, disk=10, firmware="bios", machine="pc", bus="ide", net="rtl8139", video="vga", hints=["win_legacy"])),
    "windows-98":   ("Windows 98", "windows-98", "windows", _p(vcpu=1, ram=256, disk=10, firmware="bios", machine="pc", bus="ide", net="rtl8139", video="vga", hints=["win_legacy"])),
    "windows-95":   ("Windows 95", "windows-95", "windows", _p(vcpu=1, ram=128, disk=8, firmware="bios", machine="pc", bus="ide", net="rtl8139", video="vga", hints=["win_legacy"])),
    "windows-nt":   ("Windows NT", "windows-nt", "windows", _p(vcpu=1, ram=128, disk=8, firmware="bios", machine="pc", bus="ide", net="rtl8139", video="vga", hints=["win_legacy"])),
    "ubuntu":      ("Ubuntu", "ubuntu", "linux", _p(firmware="uefi")),
    "debian":      ("Debian", "debian", "linux", _p(firmware="uefi")),
    "fedora":      ("Fedora", "fedora", "linux", _p(firmware="uefi", ram=4096, disk=30)),
    "arch":        ("Arch Linux", "archlinux", "linux", _p(firmware="uefi")),
    "opensuse":    ("openSUSE", "opensuse", "linux", _p(firmware="uefi", ram=4096, disk=30)),
    "astra":       ("Astra Linux", "astra-linux", "linux", _p(firmware="uefi")),
    "void":        ("Void Linux", "voidlinux", "linux", _p()),
    "gentoo":      ("Gentoo", "gentoo", "linux", _p()),
    "mint":        ("Linux Mint", "linuxmint", "linux", _p(firmware="uefi", ram=4096)),
    "manjaro":     ("Manjaro", "manjaro", "linux", _p(firmware="uefi", ram=4096)),
    "nixos":       ("NixOS", "nixos", "linux", _p(firmware="uefi", ram=4096)),
    "endeavouros": ("EndeavourOS", "endeavouros", "linux", _p(firmware="uefi")),
    "almalinux":   ("AlmaLinux", "almalinux", "linux", _p()),
    "rocky":       ("Rocky Linux", "rockylinux", "linux", _p()),
    "centos":      ("CentOS", "centos", "linux", _p()),
    "slackware":   ("Slackware", "slackware", "linux", _p()),
    "zorin":       ("Zorin OS", "zorin", "linux", _p(firmware="uefi", ram=4096)),
    "popos":       ("Pop!_OS", "popos", "linux", _p(firmware="uefi", ram=4096, disk=30)),
    "cachyos":     ("CachyOS", "cachyos", "linux", _p(firmware="uefi", ram=4096)),
    "mxlinux":     ("MX Linux", "mxlinux", "linux", _p()),
    "garuda":      ("Garuda Linux", "garudalinux", "linux", _p(firmware="uefi", ram=4096, disk=40)),
    "linux":       ("Linux (generic)", "linux", "linux", _p(firmware="uefi")),
    "freebsd":     ("FreeBSD", "freebsd", "bsd", _p(firmware="uefi", bus="virtio", video="vga", hints=["bsd"])),
    "openbsd":     ("OpenBSD", "openbsd", "bsd", _p(bus="virtio", video="vga", hints=["bsd"])),
    "netbsd":      ("NetBSD", "netbsd", "bsd", _p(bus="virtio", video="vga", hints=["bsd"])),
    "android":     ("Android x86", "android", "other", _p(bus="sata", net="e1000", video="vga", hints=["android"])),
    "other":       (None, "other", "other", _p()),
}

FAMILY_ORDER = {"windows": 0, "linux": 1, "bsd": 2, "other": 3}
GROUP_BY_FAMILY = {"windows": "wiz.g_windows", "linux": "wiz.g_linux", "bsd": "wiz.g_bsd", "other": "wiz.g_other"}

HINTS = {
    "win_modern": {
        "ru": [
            "1) Скачайте virtio-win ISO (драйверы для Windows): https://fedorapeople.org/groups/virt/virtio-win/direct-downloads/stable-virtio/virtio-win.iso",
            "2) Подключите этот ISO вторым CD-ROM во вкладке «Диски» (кнопка «Подключить ISO»).",
            "3) В гостевой Windows откройте Диспетчер устройств и обновите драйверы «Неизвестных устройств» с этого CD: viostor (диск), netkvm (сеть), qxl (видео), Balloon (память).",
            "4) Установите Spice guest tools, буфер обмена и автоподстройка окна: https://spice-space.org/download/windows/spice-guest-tools/spice-guest-tools-latest.exe",
            "5) (Опционально) QEMU Guest Agent с того же CD: qemu-ga-x86_64.msi, корректное выключение и статус ВМ.",
            "Совет: шина диска SATA и сеть e1000e уже выбраны так, чтобы установка прошла вообще без дополнительных драйверов.",
        ],
        "en": [
            "1) Download the virtio-win ISO (Windows drivers): https://fedorapeople.org/groups/virt/virtio-win/direct-downloads/stable-virtio/virtio-win.iso",
            "2) Attach that ISO as a second CD-ROM in the 'Disks' tab.",
            "3) In the guest: Device Manager → update the 'Unknown devices' from that CD: viostor (disk), netkvm (network), qxl (video), Balloon (memory).",
            "4) Install Spice guest tools (clipboard + display resize): https://spice-space.org/download/windows/spice-guest-tools/spice-guest-tools-latest.exe",
            "5) (Optional) QEMU Guest Agent from the same CD: qemu-ga-x86_64.msi.",
            "Tip: SATA disk and e1000e NIC are preselected, so installation works with zero extra drivers.",
        ],
        "zh": [
            "1) 下载 virtio-win ISO（Windows 驱动）：https://fedorapeople.org/groups/virt/virtio-win/direct-downloads/stable-virtio/virtio-win.iso",
            "2) 在“磁盘”标签中把该 ISO 作为第二个 CD-ROM 挂载。",
            "3) 在客户机中：设备管理器 → 用该 CD 更新“未知设备”驱动：viostor（磁盘）、netkvm（网络）、qxl（显卡）、Balloon（内存）。",
            "4) 安装 Spice guest tools（剪贴板 + 分辨率自适应）：https://spice-space.org/download/windows/spice-guest-tools/spice-guest-tools-latest.exe",
            "5) （可选）同一 CD 中的 QEMU Guest Agent：qemu-ga-x86_64.msi。",
            "提示：已预设 SATA 磁盘和 e1000e 网卡，无需额外驱动即可完成安装。",
        ],
        "pt": [
            "1) Baixe o ISO virtio-win (drivers do Windows): https://fedorapeople.org/groups/virt/virtio-win/direct-downloads/stable-virtio/virtio-win.iso",
            "2) Anexe o ISO como um segundo CD-ROM na aba 'Discos'.",
            "3) No convidado: Gerenciador de Dispositivos → atualize os 'Dispositivos desconhecidos' com o CD: viostor (disco), netkvm (rede), qxl (vídeo), Balloon (memória).",
            "4) Instale o Spice guest tools (área de transferência + redimensionamento): https://spice-space.org/download/windows/spice-guest-tools/spice-guest-tools-latest.exe",
            "5) (Opcional) QEMU Guest Agent no mesmo CD: qemu-ga-x86_64.msi.",
            "Dica: disco SATA e rede e1000e já pré-selecionados, a instalação funciona sem drivers extras.",
        ],
        "es": [
            "1) Descargue el ISO virtio-win (controladores de Windows): https://fedorapeople.org/groups/virt/virtio-win/direct-downloads/stable-virtio/virtio-win.iso",
            "2) Adjunte ese ISO como segundo CD-ROM en la pestaña 'Discos'.",
            "3) En el invitado: Administrador de dispositivos → actualice los 'Dispositivos desconocidos' con ese CD: viostor (disco), netkvm (red), qxl (vídeo), Balloon (memoria).",
            "4) Instale Spice guest tools (portapapeles + cambio de resolución): https://spice-space.org/download/windows/spice-guest-tools/spice-guest-tools-latest.exe",
            "5) (Opcional) QEMU Guest Agent del mismo CD: qemu-ga-x86_64.msi.",
            "Consejo: disco SATA y red e1000e ya preseleccionados: la instalación funciona sin controladores extra.",
        ],
    },
    "win11": {
        "ru": ["Windows 11 требует: UEFI + Secure Boot, TPM 2.0, ≥2 vCPU, ≥4 ГБ ОЗУ. UEFI и TPM 2.0 (swtpm) включены автоматически, просто вставьте ISO и ставьте."],
        "en": ["Windows 11 requires: UEFI + Secure Boot, TPM 2.0, >=2 vCPU, >=4 GB RAM. UEFI and TPM 2.0 (swtpm) are enabled automatically, just attach the ISO and install."],
        "zh": ["Windows 11 需要：UEFI + Secure Boot、TPM 2.0、≥2 vCPU、≥4 GB 内存。UEFI 和 TPM 2.0（swtpm）已自动启用，挂载 ISO 即可安装。"],
        "pt": ["O Windows 11 exige: UEFI + Secure Boot, TPM 2.0, >=2 vCPU, >=4 GB de RAM. UEFI e TPM 2.0 (swtpm) são ativados automaticamente, basta anexar o ISO e instalar."],
        "es": ["Windows 11 requiere: UEFI + Secure Boot, TPM 2.0, >=2 vCPU, >=4 GB de RAM. UEFI y TPM 2.0 (swtpm) se activan automáticamente: solo adjunte el ISO e instale."],
    },
    "win_legacy": {
        "ru": [
            "Windows XP–7: выбраны IDE/шина SATA и сеть e1000/rtl8139, установка идёт без дополнительных драйверов.",
            "Видеокарта VGA совместима со стандартными драйверами Windows.",
            "При желании ускорения: virtio-win ISO содержит драйверы и для Vista/7 (устанавливать после ОС).",
        ],
        "en": [
            "Windows XP–7: IDE/SATA bus and e1000/rtl8139 NIC are preselected, installs with no extra drivers.",
            "VGA video works with the standard Windows drivers.",
            "Optionally: the virtio-win ISO also has drivers for Vista/7 (install after the OS).",
        ],
        "zh": [
            "Windows XP–7：已预选 IDE/SATA 磁盘总线和 e1000/rtl8139 网卡，无需额外驱动即可安装。",
            "VGA 显卡与 Windows 自带驱动兼容。",
            "可选：virtio-win ISO 也包含 Vista/7 驱动（装好系统后再安装）。",
        ],
        "pt": [
            "Windows XP–7: barramento IDE/SATA e rede e1000/rtl8139 pré-selecionados, instala sem drivers extras.",
            "Vídeo VGA funciona com os drivers padrão do Windows.",
            "Opcional: o ISO virtio-win também tem drivers para Vista/7 (instalar após o SO).",
        ],
        "es": [
            "Windows XP–7: bus IDE/SATA y red e1000/rtl8139 preseleccionados: instala sin controladores extra.",
            "El vídeo VGA funciona con los controladores estándar de Windows.",
            "Opcional: el ISO virtio-win también incluye controladores para Vista/7 (instalar tras el SO).",
        ],
    },
    "linux": {
        "ru": [
            "Linux: драйверы virtio встроены в ядро, диск и сеть подхватятся сразу, ничего ставить не нужно.",
            "После установки желательно поставить пакет qemu-guest-agent, корректное выключение и статус в менеджере.",
            "Для буфера обмена с SPICE: spice-vdagent (обычно ставится автоматически в DE).",
        ],
        "en": [
            "Linux: virtio drivers are built into the kernel, disk and network work out of the box.",
            "After install, add the qemu-guest-agent package for clean shutdown and VM status.",
            "For SPICE clipboard: spice-vdagent (usually installed automatically in desktop environments).",
        ],
        "zh": [
            "Linux：virtio 驱动已内置内核，磁盘和网络开箱即用。",
            "安装后建议安装 qemu-guest-agent 软件包，以获得干净关机和虚拟机状态。",
            "SPICE 剪贴板支持：spice-vdagent（桌面环境通常已自动安装）。",
        ],
        "pt": [
            "Linux: drivers virtio já vêm no kernel, disco e rede funcionam de imediato.",
            "Após instalar, adicione o pacote qemu-guest-agent para desligamento limpo e status da VM.",
            "Para área de transferência com SPICE: spice-vdagent (normalmente automático em DEs).",
        ],
        "es": [
            "Linux: los controladores virtio vienen en el kernel: disco y red funcionan de inmediato.",
            "Tras instalar, añada el paquete qemu-guest-agent para un apagado limpio y el estado de la VM.",
            "Para portapapeles con SPICE: spice-vdagent (normalmente se instala solo en los entornos de escritorio).",
        ],
    },
    "bsd": {
        "ru": [
            "FreeBSD: virtio (vtnet/virtio_blk) включён в ядро GENERIC, работает из коробки.",
            "OpenBSD: драйвер virtio(4) включён по умолчанию, работает из коробки.",
            "NetBSD: virtio (ld_virtio/vioif) есть в ядре GENERIC (8+).",
            "Графика: стандартный видеорежим, консоль видна сразу после запуска.",
        ],
        "en": [
            "FreeBSD: virtio (vtnet/virtio_blk) is in the GENERIC kernel, works out of the box.",
            "OpenBSD: the virtio(4) driver is enabled by default, works out of the box.",
            "NetBSD: virtio (ld_virtio/vioif) is in the GENERIC kernel (8+).",
            "Video: standard display mode, the console is visible right after start.",
        ],
        "zh": [
            "FreeBSD：GENERIC 内核已含 virtio（vtnet/virtio_blk），开箱即用。",
            "OpenBSD：默认启用 virtio(4) 驱动，开箱即用。",
            "NetBSD：GENERIC 内核（8+）已含 virtio（ld_virtio/vioif）。",
            "显卡：标准显示模式，启动后立即可见控制台。",
        ],
        "pt": [
            "FreeBSD: virtio (vtnet/virtio_blk) já está no kernel GENERIC, funciona de imediato.",
            "OpenBSD: o driver virtio(4) é habilitado por padrão, funciona de imediato.",
            "NetBSD: virtio (ld_virtio/vioif) está no kernel GENERIC (8+).",
            "Vídeo: modo de exibição padrão, o console aparece logo após o início.",
        ],
        "es": [
            "FreeBSD: virtio (vtnet/virtio_blk) está en el kernel GENERIC: funciona de inmediato.",
            "OpenBSD: el controlador virtio(4) está habilitado por defecto: funciona de inmediato.",
            "NetBSD: virtio (ld_virtio/vioif) está en el kernel GENERIC (8+).",
            "Vídeo: modo estándar, la consola se ve justo tras el inicio.",
        ],
    },
    "android": {
        "ru": ["Android x86: выбрана BIOS-загрузка. Если экран остаётся чёрным, смените видеокарту на VGA во вкладке «Железо».", "Сеть: e1000. Образы: android-x86.org."],
        "en": ["Android x86: BIOS boot is preselected. If the screen stays black, switch the video card to VGA in the 'Hardware' tab.", "NIC: e1000. Images: android-x86.org."],
        "zh": ["Android x86：已预选 BIOS 启动。若屏幕黑屏，请在“硬件”标签中把显卡改为 VGA。", "网卡：e1000。镜像：android-x86.org。"],
        "pt": ["Android x86: boot por BIOS pré-selecionado. Se a tela ficar preta, mude a placa de vídeo para VGA na aba 'Hardware'.", "Rede: e1000. Imagens: android-x86.org."],
        "es": ["Android x86: arranque BIOS preseleccionado. Si la pantalla queda en negro, cambie la tarjeta de vídeo a VGA en la pestaña 'Hardware'.", "Red: e1000. Imágenes: android-x86.org."],
    },
}

OS_LIST = [(osid, v[0], v[1], v[2], v[3]) for osid, v in OS_DB.items()]
_OS_SORTED = sorted(OS_LIST, key=lambda x: (FAMILY_ORDER[x[3]], x[1] or x[0]))


def entry(osid):
    e = OS_DB.get(osid)
    if not e:
        return OS_DB["other"]
    return e


def name(osid):
    e = entry(osid)
    return e[0] or osid


def profile(osid):
    return entry(osid)[3]


def family(osid):
    return entry(osid)[2]


def icon_of(osid):
    return entry(osid)[1]


def icon_path(icon_id):
    if not icon_id:
        return None
    for ext in (".svg", ".png"):
        p = os.path.join(ICONS_DIR, icon_id + ext)
        if os.path.exists(p):
            return p
    return None


def os_list():
    return _OS_SORTED


def by_family(fam):
    return [o for o in _OS_SORTED if o[3] == fam]


def hint(osid, lang="en"):
    keys = profile(osid).get("hints") or []
    if not keys and family(osid) == "linux":
        keys = ["linux"]
    out = []
    for k in keys:
        h = HINTS.get(k, {})
        out.extend(h.get(lang) or h.get("en") or [])
    return out


_NAME_RULES = [
    (r"win\s*11|windows\s*11|win11", "windows-11"),
    (r"win\s*10|windows\s*10|win10", "windows-10"),
    (r"win\s*8\.?1|windows\s*8\.?1", "windows-8.1"),
    (r"win\s*8|windows\s*8", "windows-8"),
    (r"win\s*7|windows\s*7|win7", "windows-7"),
    (r"vista", "windows-vista"),
    (r"xp", "windows-xp"),
    (r"2000", "windows-2000"),
    (r"\bme\b|millennium", "windows-me"),
    (r"98", "windows-98"),
    (r"95", "windows-95"),
    (r"\bnt\b", "windows-nt"),
    (r"ubuntu", "ubuntu"), (r"debian", "debian"), (r"fedora", "fedora"),
    (r"arch", "arch"), (r"opensuse|open ?suse|\bsuse\b", "opensuse"),
    (r"astra", "astra"), (r"void", "void"), (r"gentoo", "gentoo"),
    (r"\bmint\b", "mint"), (r"manjaro", "manjaro"), (r"nixos|\bnix\b", "nixos"),
    (r"endeavouros|endeavour", "endeavouros"), (r"alma", "almalinux"),
    (r"rocky", "rocky"), (r"centos", "centos"), (r"slackware", "slackware"),
    (r"zorin", "zorin"), (r"pop_?os|pop!_os", "popos"),
    (r"cachyos|cachy", "cachyos"), (r"\bmx\b", "mxlinux"), (r"garuda", "garuda"),
    (r"freebsd", "freebsd"), (r"openbsd", "openbsd"), (r"netbsd", "netbsd"),
    (r"android", "android"),
]


def guess_by_name(vm_name):
    s = (vm_name or "").lower()
    for rx, osid in _NAME_RULES:
        if re.search(rx, s):
            return osid
    return "other"
