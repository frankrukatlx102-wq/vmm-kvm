# VMM-KVM

![License](https://img.shields.io/badge/license-GPL--3.0-blue)
![Python](https://img.shields.io/badge/python-3.10%2B-blue)
![Qt](https://img.shields.io/badge/Qt-PySide6-41cd52)
![Platform](https://img.shields.io/badge/platform-Linux-lightgrey)

A simple dark-themed manager for QEMU/KVM virtual machines on Linux. Built with PySide6 and libvirt, works the same on Arch, Ubuntu, Fedora and openSUSE.

## Features

- **One-screen VM creation**: paste an ISO path or pick one from the iso folder, the name is filled automatically, the OS is detected from the ISO filename (Ubuntu 24.04, Windows 11, Debian 12.5 and so on) or chosen manually, and the profile sets UEFI, TPM 2.0, disk bus and chipset.
- **Real host limits**: RAM and vCPU controls are capped by the actual host memory and CPU count, so you cannot assign more than the machine has. Current limits are shown right in the form.
- **Hardware tab**: vCPU, RAM, KVM acceleration or QEMU (TCG) emulation, Q35 or i440fx chipset, BIOS or UEFI/OVMF, TPM 2.0, video model (virtio, qxl, vga, cirrus), autostart. RAM and vCPU are applied live when the guest supports it, otherwise the app tells you a reboot is needed.
- **Honest shutdown**: ACPI shutdown request first, then a 15 second wait, then an offer to force the VM off. Reboot works the same way with a hard reset fallback.
- **Disks**: add qcow2 disks, attach or eject ISOs, change the bus, remove devices.
- **Networks**: per-VM NIC list with model switching (virtio, e1000, e1000e, rtl8139), libvirt networks with start, stop, autostart and NAT network creation.
- **Storage pools**: list and activate libvirt pools, create directory pools.
- **Snapshots**: create, revert and delete.
- **SSH hosts**: connect to remote libvirt over `qemu+ssh://` and switch the target host right inside the create dialog.
- **Console**: virt-viewer or remote-viewer for SPICE and VNC.
- **One-click services**: enables libvirtd, adds your user to the libvirt and kvm groups, installs a polkit rule and starts the default NAT network (asks for the admin password).
- **OS icons**: Windows NT to 11, popular Linux distributions, FreeBSD, OpenBSD, NetBSD.
- **Five languages**: English, Russian, Chinese, Portuguese (BR), Spanish.
- **Windows 11 ready**: UEFI, Secure Boot capable OVMF and emulated TPM 2.0 through swtpm.

## Requirements

- Linux with KVM enabled (`/dev/kvm` present)
- QEMU, libvirt, swtpm, OVMF firmware, virt-viewer, PySide6

The app works in two modes:

- **session** (default): no root needed, VMs live in your home directory, networking uses QEMU user mode (SLIRP).
- **system**: libvirt system daemon, NAT and bridges, VMs can start before login.

## Install

### Quick start

```bash
git clone https://github.com/frankrukatlx102-wq/vmm-kvm.git
cd vmm-kvm
sudo ./install.sh        # installs dependencies for your distribution
./install-desktop.sh     # adds the app to the application menu
vmm-kvm                  # or launch it from the menu: VMM-KVM
```

`install.sh` detects apt, dnf, pacman or zypper and installs the missing packages.

### Manual dependency install

Arch / CachyOS / Manjaro:

```bash
sudo pacman -S qemu-desktop libvirt virt-viewer swtpm edk2-ovmf passt pyside6 libvirt-python
```

Ubuntu / Debian:

```bash
sudo apt install qemu-kvm libvirt-daemon-system libvirt-clients ovmf swtpm virt-viewer passt python3-pyside6 python3-libvirt
```

Fedora:

```bash
sudo dnf install qemu-kvm libvirt virt-viewer swtpm edk2-ovmf passt python3-pyside6 python3-libvirt
```

openSUSE:

```bash
sudo zypper install qemu-kvm libvirt virt-viewer swtpm ovmf passt python3-PySide6 python3-libvirt-python
```

### Run from source

```bash
./vmm-kvm
# or
python3 -m vmm_kvm
```

### Desktop integration

```bash
./install-desktop.sh            # shortcut, icon and a vmm-kvm command in ~/.local/bin
./install-desktop.sh --uninstall
```

## Usage

1. Click **Create VM**.
2. Paste the path to the installer ISO, use the arrow button to pick from `~/VirtualMachines/iso`, or use the file picker. The OS and version are detected from the filename; pick another OS manually if needed.
3. Adjust vCPU, RAM and disk size. The host limits are shown below the fields, and attempts to exceed them are clamped.
4. Leave KVM acceleration on if `/dev/kvm` exists. Turning it off falls back to QEMU (TCG) emulation.
5. Click **Create** and start the VM. The console opens in virt-viewer.

While a VM is running:

- RAM and vCPU changes are saved and applied live when the guest supports it, otherwise you get a note that a reboot is required.
- Shut down sends an ACPI request, waits 15 seconds and offers a force off if the guest does not respond. Install `qemu-guest-agent` (and `acpid` on minimal installs) inside the guest for clean shutdowns.
- Snapshots, extra disks and ISO changes work from their tabs.

### Services and system mode

Open **Settings** and press **Enable services**. It runs through pkexec and:

- enables and starts `libvirtd`
- adds your user to the `libvirt` and `kvm` groups
- installs a polkit rule so the system connection works without a password
- enables autostart for the default NAT network

Log out and back in after the first run so the new group membership applies.

### SSH hosts

Settings, SSH hosts, **Add SSH**, then enter a URI such as `qemu+ssh://user@host/system`. Saved hosts are also available from the arrow menu next to **SSH** in the create dialog.

## Data layout

The base folder is `~/VirtualMachines` by default and can be changed in Settings.

```
~/VirtualMachines/
├── vms/          disk images, one folder per VM
├── iso/          installer images
├── snapshots/    snapshot storage
└── logs/         logs
```

## Languages

The interface is translated into English, Russian, Chinese, Portuguese (BR) and Spanish. Choose the language in Settings. The app picks the system language on first start.

## Troubleshooting

- **Cannot connect to the system daemon**: open Settings and press Enable services, then log out and back in.
- **Windows 11 refuses to install**: make sure UEFI and TPM 2.0 are enabled in the Hardware tab and the `swtpm` package is installed.
- **Black console window**: install `virt-viewer` (includes `remote-viewer`).
- **No network inside a VM in session mode**: session networking uses QEMU user mode. For NAT and bridges switch to system mode and enable services.
- **Shutdown button asks about force off**: the guest ignores ACPI. Install `qemu-guest-agent` and `acpid` inside the guest.

## Project layout

```
vmm-kvm/
├── vmm-kvm                 launcher
├── install.sh              dependency installer for apt, dnf, pacman, zypper
├── install-desktop.sh      desktop shortcut and icon
├── vmm_kvm/
│   ├── backend.py          libvirt layer: XML, disks, networks, pools, snapshots, services
│   ├── osdata.py           OS profiles, icons and driver hints
│   ├── i18n.py             translations
│   ├── config.py           ~/.config/vmm-kvm/config.json
│   ├── main.py             entry point
│   └── ui/                 PySide6 interface
└── vmm_kvm/assets/icons/   app icon and OS logos
```

## License

GPL-3.0. See [LICENSE](LICENSE).
