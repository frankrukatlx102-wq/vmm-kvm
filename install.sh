#!/usr/bin/env bash
set -e

if [ "$EUID" -ne 0 ]; then
    echo "Нужны права администратора, перезапускаю через sudo..."
    exec sudo bash "$0" "$@"
fi

ID=$( . /etc/os-release; echo "${ID_LIKE:-} ${ID}" )

APT=(qemu-kvm libvirt-daemon-system libvirt-clients ovmf swtpm virt-viewer
     python3-pyside6 python3-libvirt passt dnsmasq-base)
DNF=(qemu-kvm libvirt virt-viewer swtpm edk2-ovmf passt
     python3-pyside6 python3-libvirt dnsmasq)
PAC=(qemu-desktop libvirt virt-viewer swtpm edk2-ovmf passt
     python-libvirt pyside6 dnsmasq)
ZY=(qemu-kvm libvirt virt-viewer swtpm ovmf passt
    python3-PySide6 python3-libvirt-python dnsmasq)

case "$ID" in
    *debian*|*ubuntu*|*mint*)
        apt-get update
        apt-get install -y "${APT[@]}"
        ;;
    *fedora*|*rhel*|*centos*)
        dnf install -y "${DNF[@]}"
        ;;
    *arch*|*cachyos*|*manjaro*|*endeavouros*|*garuda*|*artix*)
        pacman -Sy --needed --noconfirm "${PAC[@]}"
        ;;
    *suse*)
        zypper --non-interactive install "${ZY[@]}"
        ;;
    *)
        echo "Неизвестный дистрибутив: $ID"
        echo "Поставьте вручную: qemu-kvm libvirt ovmf swtpm virt-viewer passt dnsmasq python-pyside6 python-libvirt"
        exit 1
        ;;
esac

echo
echo "Готово! Запуск приложения:"
echo "  cd $(cd "$(dirname "$0")" && pwd) && ./vmm-kvm"
