#!/usr/bin/env bash
set -e

APP_DIR="$(cd "$(dirname "$0")" && pwd)"
BIN_DIR="$HOME/.local/bin"
DESKTOP_DIR="$HOME/.local/share/applications"
ICON_DIR="$HOME/.local/share/icons/hicolor/scalable/apps"
PNG_DIR="$HOME/.local/share/icons/hicolor/256x256/apps"

if [ "$1" = "--uninstall" ]; then
    rm -f "$DESKTOP_DIR/vmm-kvm.desktop" "$ICON_DIR/vmm-kvm.svg" \
          "$PNG_DIR/vmm-kvm.png" "$BIN_DIR/vmm-kvm"
    command -v update-desktop-database >/dev/null && update-desktop-database -q "$DESKTOP_DIR" || true
    echo "VMM-KVM удалён из меню приложений."
    exit 0
fi

chmod +x "$APP_DIR/vmm-kvm"
mkdir -p "$BIN_DIR" "$DESKTOP_DIR" "$ICON_DIR" "$PNG_DIR"

ln -sf "$APP_DIR/vmm-kvm" "$BIN_DIR/vmm-kvm"
cp -f "$APP_DIR/vmm_kvm/assets/icons/app.svg" "$ICON_DIR/vmm-kvm.svg"
if command -v rsvg-convert >/dev/null 2>&1; then
    rsvg-convert -w 256 -h 256 "$APP_DIR/vmm_kvm/assets/icons/app.svg" \
        -o "$PNG_DIR/vmm-kvm.png" 2>/dev/null || true
fi

cat > "$DESKTOP_DIR/vmm-kvm.desktop" <<EOF
[Desktop Entry]
Type=Application
Name=VMM-KVM
GenericName=Virtual Machine Manager
Comment=QEMU/KVM virtual machines (libvirt)
Comment[ru]=Виртуальные машины QEMU/KVM (libvirt)
Comment[zh]=QEMU/KVM 虚拟机（libvirt）
Comment[pt]=Máquinas virtuais QEMU/KVM (libvirt)
Comment[es]=Máquinas virtuales QEMU/KVM (libvirt)
Exec=$APP_DIR/vmm-kvm
TryExec=$APP_DIR/vmm-kvm
Path=$APP_DIR
Icon=vmm-kvm
Terminal=false
Categories=System;Emulator;
Keywords=vm;virtual;qemu;kvm;libvirt;
StartupNotify=true
StartupWMClass=VMM-KVM
EOF
chmod +x "$DESKTOP_DIR/vmm-kvm.desktop"

command -v update-desktop-database >/dev/null && update-desktop-database -q "$DESKTOP_DIR" || true
command -v kbuildsycoca6 >/dev/null && kbuildsycoca6 --noincremental >/dev/null 2>&1 || true

echo "Готово: VMM-KVM появился в меню приложений (поиск: VMM)."
echo "Ярлык: $DESKTOP_DIR/vmm-kvm.desktop"
echo "Команда: vmm-kvm (если ~/.local/bin есть в PATH)"
