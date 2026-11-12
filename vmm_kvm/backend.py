# -*- coding: utf-8 -*-
import os
import random
import re
import shutil
import subprocess
import time
import xml.etree.ElementTree as ET

import libvirt

from . import osdata

NS_MARKER = "VMM-KVM:os="

STATE_RUNNING = 1
STATE_PAUSED = 3

OVMF_DIRS = [
    "/usr/share/OVMF", "/usr/share/OVMF/x64", "/usr/share/OVMF/x64/OVMF",
    "/usr/share/ovmf", "/usr/share/ovmf/x64",
    "/usr/share/edk2-ovmf", "/usr/share/edk2-ovmf/x64",
    "/usr/share/edk2/ovmf", "/usr/share/edk2/x64",
    "/usr/share/qemu", "/usr/share/qemu/ovmf",
]


class BackendError(Exception):
    pass


def find_ovmf(secure=False):
    codes, varses = [], []
    for d in OVMF_DIRS:
        if not os.path.isdir(d):
            continue
        try:
            files = os.listdir(d)
        except OSError:
            continue
        for f in files:
            fl = f.lower()
            if not fl.endswith(".fd"):
                continue
            p = os.path.join(d, f)
            if "code" in fl:
                codes.append(p)
            elif "var" in fl:
                varses.append(p)
            elif fl == "ovmf.fd":
                codes.append(p)
    if not codes:
        return None
    if secure:
        sec = [c for c in codes if "secboot" in os.path.basename(c).lower()]
        if sec:
            codes = sec
    code = codes[0]
    same = [v for v in varses if os.path.dirname(v) == os.path.dirname(code)]
    var = (same or varses or [None])[0]
    return code, var


def new_mac():
    return "52:54:00:%02x:%02x:%02x" % (random.randint(0, 255), random.randint(0, 255), random.randint(0, 255))


def mem_mib(el):
    if el is None or not el.text:
        return 0
    try:
        val = int(el.text)
    except ValueError:
        return 0
    unit = (el.get("unit") or "KiB").strip()
    if unit in ("KiB", "K", "k"):
        return val // 1024
    if unit in ("MiB", "M", "m"):
        return val
    if unit in ("GiB", "G", "g"):
        return val * 1024
    if unit == "bytes":
        return val // (1024 * 1024)
    return val // 1024


class VM:

    def __init__(self, backend, dom):
        self.b = backend
        self.dom = dom
        self.name = dom.name()
        self.uuid = dom.UUIDString()
        try:
            info = dom.info()
        except Exception:
            info = [5, 0, 0, 0, 0]
        self.state = info[0]
        self.live_maxmem_mb = int(info[1]) // 1024
        self.live_mem_mb = int(info[2]) // 1024
        self.live_vcpus = int(info[3])
        self.maxmem_mb = self.live_maxmem_mb
        self.mem_mb = self.live_mem_mb
        self.vcpus = self.live_vcpus
        try:
            cfg_root = ET.fromstring(backend._config_xml(dom))
            vcpu_el = cfg_root.find("vcpu")
            if vcpu_el is not None and vcpu_el.text:
                self.vcpus = int(vcpu_el.text)
            configured = mem_mib(cfg_root.find("memory"))
            if configured:
                self.maxmem_mb = configured
        except Exception:
            pass
        try:
            self.autostart = bool(dom.autostart())
        except Exception:
            self.autostart = False
        marker = backend._os_marker(self.dom)
        self.os_id = marker or osdata.guess_by_name(self.name)
        self.icon = osdata.icon_of(self.os_id)
        self.os_name = osdata.name(self.os_id)

    @property
    def running(self):
        return self.state == STATE_RUNNING

    @property
    def paused(self):
        return self.state == STATE_PAUSED

    @property
    def stopped(self):
        return self.state in (4, 5, 6)


class Backend:
    def __init__(self, cfg):
        self.cfg = cfg
        self.conn = None
        self.uri_kind = None
        self._cpu_cache = {}
        self._host_cpu_prev = None

    def connect(self, kind=None, uri=None):
        kind = kind or self.cfg.get("connection") or "session"
        target = uri or {"session": "qemu:///session", "system": "qemu:///system"}.get(kind)
        if not target:
            raise BackendError("unknown URI")
        try:
            self.conn = libvirt.open(target)
        except libvirt.libvirtError as e:
            self.conn = None
            raise BackendError(str(e))
        self.uri_kind = "custom" if uri else kind
        return target

    def close(self):
        if self.conn:
            try:
                self.conn.close()
            except Exception:
                pass
        self.conn = None

    def connected(self):
        return self.conn is not None

    def uri(self):
        try:
            return self.conn.getURI() if self.conn else ""
        except Exception:
            return ""

    def domains(self):
        if not self.conn:
            return []
        try:
            doms = self.conn.listAllDomains(0)
        except Exception:
            doms = []
        out = []
        for d in doms:
            try:
                out.append(VM(self, d))
            except Exception:
                pass
        out.sort(key=lambda v: v.name.lower())
        return out

    def _dom(self, name):
        d = self.conn.lookupByName(name)
        if d is None:
            raise BackendError("VM not found: " + name)
        return d

    def _os_marker(self, dom):
        try:
            xml = dom.XMLDesc(0)
            m = re.search(r"<description>([^<]*)</description>", xml)
            if m and NS_MARKER in m.group(1):
                osid = m.group(1).split(NS_MARKER, 1)[1].split("|", 1)[0].strip()
                if osid in osdata.OS_DB:
                    return osid
        except Exception:
            pass
        return None

    def _op(self, name, fn):
        try:
            fn()
        except libvirt.libvirtError as e:
            raise BackendError(str(e))

    def start(self, name):
        d = self._dom(name)
        self._ensure_default_network()
        self._op(name, d.create)

    def shutdown(self, name):
        self._op(name, self._dom(name).shutdown)

    def forceoff(self, name):
        self._op(name, self._dom(name).destroy)

    def reboot(self, name):
        self._op(name, self._dom(name).reboot)

    def reset(self, name):
        self._op(name, self._dom(name).reset)

    def pause(self, name):
        self._op(name, self._dom(name).suspend)

    def resume(self, name):
        self._op(name, self._dom(name).resume)

    def delete(self, name):
        d = self._dom(name)
        try:
            flags = (libvirt.VIR_DOMAIN_UNDEFINE_SNAPSHOTS_METADATA |
                     libvirt.VIR_DOMAIN_UNDEFINE_MANAGED_SAVE |
                     libvirt.VIR_DOMAIN_UNDEFINE_NVRAM)
            d.undefineFlags(flags)
            return
        except (AttributeError, libvirt.libvirtError):
            pass
        try:
            root = ET.fromstring(d.XMLDesc(0))
            osel = root.find("os")
            for tag in ("loader", "nvram", "firmware"):
                for e in osel.findall(tag):
                    osel.remove(e)
            osel.attrib.pop("firmware", None)
            self.conn.defineXML(ET.tostring(root, encoding="unicode"))
        except Exception:
            pass
        try:
            d.undefine()
        except libvirt.libvirtError as e:
            raise BackendError(str(e))

    def set_autostart(self, name, on):
        self._op(name, lambda: self._dom(name).setAutostart(1 if on else 0))

    def _iface_element(self, model, network="default", bridge=None, mac=None):
        itf = ET.Element("interface")
        if bridge:
            itf.set("type", "bridge")
            ET.SubElement(itf, "source").set("bridge", bridge)
        elif self._is_session():
            itf.set("type", "user")
        else:
            itf.set("type", "network")
            ET.SubElement(itf, "source").set("network", network)
        ET.SubElement(itf, "mac").set("address", mac or new_mac())
        ET.SubElement(itf, "model").set("type", model)
        return itf

    def _is_session(self):
        return "session" in (self.uri() or "")

    def _remote_target(self):
        m = re.match(r"qemu\+ssh://(?:([^@/]+)@)?([^/:]+)", self.uri() or "")
        return (m.group(1) or "", m.group(2)) if m else None

    def _ensure_default_network(self):
        if self._is_session():
            return
        try:
            nets = self.conn.listAllNetworks(0)
            for n in nets:
                if n.name() == "default" and not n.isActive():
                    n.create()
        except Exception:
            pass

    def stats(self, vm):
        try:
            info = vm.dom.info()
        except Exception:
            info = [5, 0, 0, 0, 0]
        state = info[0]
        if state != STATE_RUNNING:
            self._cpu_cache.pop(vm.uuid, None)
            return {"cpu": 0.0, "mem": 0, "max": int(info[1]) // 1024, "state": state}
        now = time.monotonic()
        prev = self._cpu_cache.get(vm.uuid)
        pct = 0.0
        if prev:
            wall = now - prev[0]
            dt = info[4] - prev[1]
            if wall > 0.01 and dt > 0:
                pct = 100.0 * dt / (wall * 1e9) / max(1, int(info[3]))
        self._cpu_cache[vm.uuid] = (now, info[4])
        return {"cpu": min(pct, 100.0), "mem": int(info[2]) // 1024,
                "max": int(info[1]) // 1024, "state": state}

    def _xml(self, dom, active=False):
        flags = 0
        if active:
            flags = libvirt.VIR_DOMAIN_XML_ACTIVE
        return dom.XMLDesc(flags)

    def _config_xml(self, dom):
        if dom.isActive():
            return dom.XMLDesc(libvirt.VIR_DOMAIN_XML_INACTIVE)
        return dom.XMLDesc(0)

    def _define(self, root):
        self.conn.defineXML(ET.tostring(root, encoding="unicode"))

    def _define_maybe_uefi(self, root, name, uefi, secure=False):
        try:
            self.conn.defineXML(ET.tostring(root, encoding="unicode"))
            return
        except libvirt.libvirtError:
            if not uefi:
                raise
        pair = find_ovmf(secure)
        if not pair:
            raise BackendError("UEFI firmware (OVMF) not found: install ovmf/edk2-ovmf")
        osel = root.find("os")
        osel.attrib.pop("firmware", None)
        for tag in ("loader", "nvram", "firmware"):
            for e in osel.findall(tag):
                osel.remove(e)
        loader = ET.Element("loader")
        loader.set("readonly", "yes")
        loader.set("type", "pflash")
        if secure:
            loader.set("secure", "yes")
        loader.text = pair[0]
        typel = osel.find("type")
        osel.insert(list(osel).index(typel) + 1, loader)
        if pair[1]:
            vm_dir = os.path.join(self._paths()["vms"], re.sub(r"[^\w.-]", "_", name))
            os.makedirs(vm_dir, exist_ok=True)
            dst = os.path.join(vm_dir, "nvram_VARS.fd")
            if not os.path.exists(dst):
                shutil.copy2(pair[1], dst)
            nv = ET.Element("nvram")
            nv.text = dst
            osel.insert(list(osel).index(loader) + 1, nv)
        try:
            self.conn.defineXML(ET.tostring(root, encoding="unicode"))
        except libvirt.libvirtError as e:
            raise BackendError(str(e))

    def _devices(self, root):
        return root.find("devices")

    def _insert_sorted(self, parent, elem, order):
        tag = elem.tag
        idx = order.index(tag)
        pos = len(parent)
        for i, ch in enumerate(parent):
            if ch.tag in order and order.index(ch.tag) > idx:
                pos = i
                break
        parent.insert(pos, elem)

    DEV_ORDER = ["emulator", "disk", "controller", "interface", "serial", "console",
                 "channel", "input", "tpm", "sound", "video", "memballoon"]

    def hw_read(self, name):
        root = ET.fromstring(self._config_xml(self._dom(name)))
        osel = root.find("os")
        typel = osel.find("type")
        devs = self._devices(root)
        tpmel = devs.find("tpm")
        loader = osel.find("loader")
        return {
            "vcpu": int((root.findtext("vcpu") or "1").strip() or 1),
            "ram": mem_mib(root.find("memory")),
            "kvm": (root.get("type") == "kvm"),
            "machine": typel.get("machine") if typel is not None else "pc",
            "uefi": osel.get("firmware") == "efi" or loader is not None,
            "secure": loader is not None and loader.get("secure") == "yes",
            "tpm": tpmel is not None,
            "video": (devs.find("video/model").get("type") if devs.find("video/model") is not None else "vga"),
            "autostart": bool(self._dom(name).autostart()),
        }

    def hw_apply(self, name, vals):
        d = self._dom(name)
        root = ET.fromstring(self._config_xml(d))
        osel = root.find("os")
        typel = osel.find("type")
        devs = self._devices(root)

        root.find("vcpu").text = str(int(vals["vcpu"]))
        mem = root.find("memory"); mem.set("unit", "MiB"); mem.text = str(int(vals["ram"]))
        cur = root.find("currentMemory")
        if cur is not None:
            cur.set("unit", "MiB"); cur.text = str(int(vals["ram"]))
        root.set("type", "kvm" if vals["kvm"] else "qemu")
        cpu = root.find("cpu")
        if vals["kvm"]:
            if cpu is None:
                cpu = ET.SubElement(root, "cpu")
            for ch in list(cpu):
                cpu.remove(ch)
            cpu.set("mode", "host-model")
            cpu.set("check", "partial")
            cpu.text = None
        elif cpu is not None:
            root.remove(cpu)
        cur_machine = typel.get("machine")
        typel.set("machine", vals["machine"])
        if cur_machine and cur_machine != vals["machine"]:
            for c in devs.findall("controller"):
                devs.remove(c)

        for tag in ("loader", "nvram"):
            e = osel.find(tag)
            if e is not None:
                osel.remove(e)
        feats = root.find("features")
        if vals["uefi"]:
            osel.set("firmware", "efi")
            if vals.get("tpm"):
                if feats is None:
                    feats = ET.SubElement(root, "features")
                smm = feats.find("smm")
                if smm is None:
                    smm = ET.SubElement(feats, "smm")
                smm.set("state", "on")
        else:
            osel.attrib.pop("firmware", None)
            if feats is not None:
                smm = feats.find("smm")
                if smm is not None:
                    feats.remove(smm)

        for t in devs.findall("tpm"):
            devs.remove(t)
        if vals["tpm"]:
            tpm = ET.SubElement(devs, "tpm")
            tpm.set("model", "tpm-crb" if vals["machine"] == "q35" else "tpm-tis")
            be = ET.SubElement(tpm, "backend")
            be.set("type", "emulator"); be.set("version", "2.0")
            be.set("persistent_state", "yes")

        vm_ = devs.find("video")
        if vm_ is None:
            self._insert_sorted(devs, ET.Element("video"), self.DEV_ORDER)
            vm_ = devs.find("video")
        model = vm_.find("model")
        if model is None:
            model = ET.SubElement(vm_, "model")
        model.set("type", vals["video"])
        model.set("heads", "1")
        if vals["video"] == "qxl":
            model.set("ram", "65536"); model.set("vram", "32768")
        else:
            model.set("vram", "16384")

        self._define_maybe_uefi(root, name, vals["uefi"], vals.get("tpm", False))
        deferred = False
        if d.isActive():
            try:
                d.setMemory(int(vals["ram"]) * 1024)
            except Exception:
                deferred = True
            try:
                d.setVcpus(int(vals["vcpu"]))
            except Exception:
                deferred = True
        try:
            d.setAutostart(1 if vals["autostart"] else 0)
        except Exception as e:
            raise BackendError(str(e))
        return {"deferred": deferred}

    def disks_read(self, name):
        root = ET.fromstring(self._config_xml(self._dom(name)))
        out = []
        for disk in self._devices(root).findall("disk"):
            dev = disk.get("device")
            tgt = disk.find("target")
            src = disk.find("source")
            driver = disk.find("driver")
            out.append({
                "device": dev,
                "target": tgt.get("dev") if tgt is not None else "",
                "bus": tgt.get("bus") if tgt is not None else "",
                "file": src.get("file") if src is not None else "",
                "type": driver.get("type") if driver is not None else "",
            })
        return out

    def _free_target(self, root, bus):
        used = set()
        for disk in self._devices(root).findall("disk"):
            t = disk.find("target")
            if t is not None:
                used.add(t.get("dev"))
        pre = "hd" if bus == "ide" else "sd"
        for c in "abcdefghijklmnopqrstuvwxyz":
            dev = pre + c
            if dev not in used:
                return dev
        return pre + "z"

    def _disk_xml(self, path, dev, bus, cdrom=False, ro=False):
        disk = ET.Element("disk")
        disk.set("type", "file")
        disk.set("device", "cdrom" if cdrom else "disk")
        if not cdrom:
            drv = ET.SubElement(disk, "driver")
            drv.set("name", "qemu"); drv.set("type", "qcow2")
        if path:
            src = ET.SubElement(disk, "source"); src.set("file", path)
        tgt = ET.SubElement(disk, "target"); tgt.set("dev", dev); tgt.set("bus", bus)
        if cdrom or ro:
            ET.SubElement(disk, "readonly")
        return disk

    def _change_devices(self, name, mutate):
        d = self._dom(name)
        root = ET.fromstring(self._config_xml(d))
        mutate(root)
        self._define(root)
        if not d.isActive():
            return
        try:
            live_old = ET.fromstring(self._xml(d, active=True))
            live_new = ET.fromstring(self._xml(d, active=True))
            mutate(live_new)
            self._live_sync(d, live_old, live_new)
        except Exception:
            pass

    @staticmethod
    def _dev_key(e):
        if e.tag == "disk":
            t = e.find("target")
            return t.get("dev") if t is not None else None
        if e.tag == "interface":
            m = e.find("mac")
            return m.get("address") if m is not None else None
        return None

    def _live_sync(self, d, old_root, new_root):
        for tag in ("disk", "interface"):
            old = {}
            new = {}
            for e in old_root.find("devices").findall(tag):
                old[self._dev_key(e)] = e
            for e in new_root.find("devices").findall(tag):
                new[self._dev_key(e)] = e
            for k, e in new.items():
                try:
                    if k not in old:
                        d.attachDeviceFlags(ET.tostring(e, encoding="unicode"),
                                            libvirt.VIR_DOMAIN_AFFECT_LIVE)
                    elif ET.tostring(old[k]) != ET.tostring(e):
                        d.updateDeviceFlags(ET.tostring(e, encoding="unicode"),
                                            libvirt.VIR_DOMAIN_AFFECT_LIVE)
                except Exception:
                    pass
            for k, e in old.items():
                if k not in new:
                    try:
                        d.detachDeviceFlags(ET.tostring(e, encoding="unicode"),
                                            libvirt.VIR_DOMAIN_AFFECT_LIVE)
                    except Exception:
                        pass

    def add_disk(self, name, size_gb, bus):
        paths = self._paths()
        root = ET.fromstring(self._xml(self._dom(name)))
        vm_dir = os.path.join(paths["vms"], re.sub(r"[^\w.-]", "_", name))
        os.makedirs(vm_dir, exist_ok=True)
        n = 1
        while True:
            path = os.path.join(vm_dir, "disk%d.qcow2" % n)
            if not os.path.exists(path):
                break
            n += 1
        subprocess.run(["qemu-img", "create", "-f", "qcow2", path, "%dG" % int(size_gb)],
                       check=True, capture_output=True, text=True)
        dev = self._free_target(root, bus)
        disk = self._disk_xml(path, dev, bus)

        def mutate(r):
            self._insert_sorted(r.find("devices"), disk, self.DEV_ORDER)
        self._change_devices(name, mutate)
        return path

    def remove_disk(self, name, target):
        def mutate(r):
            devs = r.find("devices")
            for disk in devs.findall("disk"):
                t = disk.find("target")
                if t is not None and t.get("dev") == target:
                    devs.remove(disk)
        self._change_devices(name, mutate)

    def set_disk_bus(self, name, target, bus):
        def mutate(r):
            for disk in r.find("devices").findall("disk"):
                t = disk.find("target")
                if t is not None and t.get("dev") == target and disk.get("device") == "disk":
                    t.set("bus", bus)
                    t.set("dev", self._free_target(r, bus))
        root = ET.fromstring(self._config_xml(self._dom(name)))
        mutate(root)
        self._define(root)

    def attach_iso(self, name, iso_path):
        def mutate(r):
            devs = r.find("devices")
            cd = None
            for disk in devs.findall("disk"):
                if disk.get("device") == "cdrom":
                    cd = disk
                    break
            if cd is None:
                typel = r.find("os/type")
                machine = (typel.get("machine") or "") if typel is not None else ""
                bus = "sata" if "q35" in machine else "ide"
                cd = self._disk_xml(iso_path, self._free_target(r, bus), bus, cdrom=True)
                self._insert_sorted(devs, cd, self.DEV_ORDER)
            else:
                src = cd.find("source")
                if iso_path:
                    if src is None:
                        src = ET.SubElement(cd, "source")
                    src.set("file", iso_path)
                elif src is not None:
                    cd.remove(src)
        self._change_devices(name, mutate)

    def nics_read(self, name):
        root = ET.fromstring(self._config_xml(self._dom(name)))
        out = []
        for itf in self._devices(root).findall("interface"):
            mac = itf.find("mac")
            model = itf.find("model")
            src = itf.find("source")
            source = ""
            if src is not None:
                source = src.get("network") or src.get("bridge") or src.get("dev") or ""
            out.append({
                "mac": mac.get("address") if mac is not None else "",
                "model": model.get("type") if model is not None else "",
                "source": source,
                "kind": itf.get("type"),
            })
        return out

    def nic_add(self, name, model, network="default", bridge=None):
        def mutate(r):
            itf = self._iface_element(model, network=network, bridge=bridge)
            self._insert_sorted(r.find("devices"), itf, self.DEV_ORDER)
        self._change_devices(name, mutate)

    def nic_remove(self, name, mac):
        def mutate(r):
            devs = r.find("devices")
            for itf in devs.findall("interface"):
                m = itf.find("mac")
                if m is not None and m.get("address") == mac:
                    devs.remove(itf)
        self._change_devices(name, mutate)

    def nic_set_model(self, name, mac, model):
        def mutate(r):
            for itf in r.find("devices").findall("interface"):
                m = itf.find("mac")
                if m is not None and m.get("address") == mac:
                    mo = itf.find("model")
                    if mo is None:
                        mo = ET.SubElement(itf, "model")
                    mo.set("type", model)
        self._change_devices(name, mutate)

    def snapshots(self, name):
        d = self._dom(name)
        out = []
        try:
            names = d.snapshotListNames()
        except Exception:
            names = []
        for n in names:
            try:
                s = d.snapshotLookupByName(n)
                root = ET.fromstring(s.getXMLDesc())
                desc = root.findtext("description") or ""
                created = root.findtext("creationTime") or ""
                out.append({"name": n, "desc": desc, "created": created})
            except Exception:
                pass
        return out

    def snap_create(self, name, snapname, desc=""):
        esc = lambda s: s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        xml = "<domainsnapshot><name>%s</name><description>%s</description></domainsnapshot>" % (
            esc(snapname), esc(desc or ""))
        self._op(name, lambda: self._dom(name).snapshotCreateXML(xml))

    def snap_revert(self, name, snapname):
        d = self._dom(name)
        s = d.snapshotLookupByName(snapname)
        try:
            d.revertToSnapshot(s, 0)
        except AttributeError:
            raise BackendError("revert not supported by libvirt")

    def snap_delete(self, name, snapname):
        d = self._dom(name)
        s = d.snapshotLookupByName(snapname)
        self._op(name, lambda: s.delete())

    def networks(self):
        if not self.conn:
            return []
        try:
            nets = self.conn.listAllNetworks(0)
        except Exception:
            nets = []
        out = []
        for n in nets:
            try:
                root = ET.fromstring(n.XMLDesc())
                fwd = root.find("forward")
                out.append({
                    "name": n.name(),
                    "active": bool(n.isActive()),
                    "autostart": bool(n.autostart()),
                    "bridge": n.bridgeName(),
                    "mode": fwd.get("mode") if fwd is not None else "isolated",
                })
            except Exception:
                pass
        out.sort(key=lambda x: x["name"])
        return out

    def net_start(self, name):
        self._op(name, lambda: self.conn.networkLookupByName(name).create())

    def net_stop(self, name):
        self._op(name, lambda: self.conn.networkLookupByName(name).destroy())

    def net_autostart(self, name, on):
        self._op(name, lambda: self.conn.networkLookupByName(name).setAutostart(1 if on else 0))

    def net_create_nat(self, name, cidr):
        import ipaddress
        net = ipaddress.ip_network(cidr, strict=False)
        gw = str(net.network_address + 1)
        lo = str(net.network_address + 10)
        hi = str(net.broadcast_address - 10)
        xml = (
            "<network><name>%s</name><forward mode='nat'/>"
            "<bridge stp='on' delay='0'/>"
            "<ip address='%s' prefix='%d'><dhcp><range start='%s' end='%s'/></dhcp></ip>"
            "</network>" % (name, gw, net.prefixlen, lo, hi))
        try:
            self.conn.networkDefineXML(xml)
        except libvirt.libvirtError as e:
            raise BackendError(str(e))

    def pools(self):
        if not self.conn:
            return []
        try:
            pools = self.conn.listAllStoragePools(0)
        except Exception:
            pools = []
        out = []
        for p in pools:
            try:
                root = ET.fromstring(p.XMLDesc())
                path = root.findtext("target/path") or ""
                ptype = root.get("type") or ""
                try:
                    info = p.info()
                    cap, alloc = info[1], info[2]
                    active = bool(info[0] == 2 or p.isActive())
                except Exception:
                    cap, alloc, active = 0, 0, bool(p.isActive())
                out.append({
                    "name": p.name(), "active": active, "type": ptype,
                    "path": path, "cap": cap, "alloc": alloc,
                    "autostart": bool(p.autostart()),
                })
            except Exception:
                pass
        out.sort(key=lambda x: x["name"])
        return out

    def pool_start(self, name):
        self._op(name, lambda: self.conn.storagePoolLookupByName(name).create())

    def pool_stop(self, name):
        self._op(name, lambda: self.conn.storagePoolLookupByName(name).destroy())

    def pool_create_dir(self, name, path):
        os.makedirs(path, exist_ok=True)
        xml = ("<pool type='dir'><name>%s</name><target><path>%s</path>"
               "<permissions><owner>-1</owner><group>-1</group>"
               "<mode>0755</mode></permissions></target></pool>" % (name, path))
        try:
            pool = self.conn.storagePoolDefineXML(xml)
        except libvirt.libvirtError as e:
            raise BackendError(str(e))
        try:
            pool.build(0)
            pool.create(0)
        except Exception:
            pass

    def host_limits(self):
        ram_mb = 0
        try:
            with open("/proc/meminfo") as f:
                for ln in f:
                    if ln.startswith("MemTotal:"):
                        ram_mb = int(ln.split()[1]) // 1024
                        break
        except OSError:
            pass
        return {"ram_mb": ram_mb or 1024, "cpus": os.cpu_count() or 1}

    def host_stats(self):
        pct = 0.0
        try:
            with open("/proc/stat") as f:
                first = f.readline().split()[1:]
            vals = list(map(float, first[:8]))
            idle = vals[3] + (vals[4] if len(vals) > 4 else 0.0)
            total = sum(vals)
            if self._host_cpu_prev:
                pt, pi, pa = self._host_cpu_prev
                dt, di = total - pt, idle - pi
                if dt > 0:
                    pct = 100.0 * (1.0 - di / dt)
            self._host_cpu_prev = (total, idle, pct)
        except Exception:
            pass
        mem_used, mem_total = 0, 0
        try:
            with open("/proc/meminfo") as f:
                mi = dict(
                    (ln.split(":")[0], int(ln.split()[1]))
                    for ln in f if ":" in ln)
            mem_total = mi.get("MemTotal", 0) // 1024
            mem_used = (mi.get("MemTotal", 0) - mi.get("MemAvailable", 0)) // 1024
        except Exception:
            pass
        load = ""
        try:
            load = ", ".join("%.2f" % x for x in os.getloadavg())
        except Exception:
            pass
        distro = ""
        try:
            with open("/etc/os-release") as f:
                for ln in f:
                    if ln.startswith("PRETTY_NAME="):
                        distro = ln.split("=", 1)[1].strip().strip('"')
                        break
        except Exception:
            pass
        versions = {}
        if self.conn:
            for k, fn in (("libvirt", "getLibVersion"), ("qemu", "getVersion")):
                try:
                    versions[k] = getattr(self.conn, fn)()
                except Exception:
                    versions[k] = 0
        return {
            "cpu": min(pct, 100.0),
            "mem_used": mem_used, "mem_total": mem_total,
            "load": load, "distro": distro,
            "kernel": os.uname().release,
            "kvm": os.path.exists("/dev/kvm"),
            "cpus": os.cpu_count() or 1,
            "versions": versions,
        }

    def _paths(self):
        from . import config
        return config.paths(self.cfg)

    def iso_files(self):
        p = self._paths().get("iso", "")
        try:
            return sorted(f for f in os.listdir(p) if f.lower().endswith(".iso"))
        except OSError:
            return []

    def create_vm(self, params):
        name = params["name"]
        osid = params["os_id"]
        prof = osdata.profile(osid)
        safe = re.sub(r"[^\w.-]", "_", name)
        remote = self._remote_target()
        if remote:
            user, host = remote
            ssh = ["ssh", ("%s@%s" % (user, host)) if user else host]
            vm_dir = "/var/lib/libvirt/images/" + safe
            disk_path = vm_dir + "/disk.qcow2"
            for cmd in (ssh + ["mkdir", "-p", vm_dir],
                        ssh + ["qemu-img", "create", "-f", "qcow2", disk_path,
                               "%dG" % int(params["disk"])]):
                try:
                    subprocess.run(cmd, check=True, capture_output=True, text=True, timeout=120)
                except subprocess.CalledProcessError as e:
                    raise BackendError((e.stderr or e.stdout or "ssh failed").strip())
        else:
            paths = self._paths()
            vm_dir = os.path.join(paths["vms"], safe)
            disk_path = os.path.join(vm_dir, "disk.qcow2")
            if os.path.exists(disk_path) or self._name_taken(name):
                raise BackendError("name already taken: " + name)
            os.makedirs(vm_dir, exist_ok=True)
            subprocess.run(
                ["qemu-img", "create", "-f", "qcow2", disk_path, "%dG" % int(params["disk"])],
                check=True, capture_output=True, text=True)

        use_kvm = os.path.exists("/dev/kvm") and params.get("kvm", True)
        machine = prof["machine"]
        bus = prof["bus"]
        firmware = params.get("firmware") or "auto"
        if firmware == "auto":
            firmware = prof["firmware"]
        uefi = firmware == "uefi"

        root = ET.Element("domain")
        root.set("type", "kvm" if use_kvm else "qemu")
        ET.SubElement(root, "name").text = name
        desc = ET.SubElement(root, "description")
        desc.text = "%s%s" % (NS_MARKER, osid)
        mem = ET.SubElement(root, "memory"); mem.set("unit", "MiB")
        mem.text = str(int(params["ram"]))
        cur = ET.SubElement(root, "currentMemory"); cur.set("unit", "MiB")
        cur.text = str(int(params["ram"]))
        vcpu = ET.SubElement(root, "vcpu"); vcpu.set("placement", "static")
        vcpu.text = str(int(params["vcpu"]))

        osel = ET.SubElement(root, "os")
        if uefi:
            osel.set("firmware", "efi")
        typel = ET.SubElement(osel, "type")
        typel.set("arch", "x86_64"); typel.set("machine", machine)
        typel.text = "hvm"
        b1 = ET.SubElement(osel, "boot"); b1.set("dev", "cdrom")
        b2 = ET.SubElement(osel, "boot"); b2.set("dev", "hd")

        feats = ET.SubElement(root, "features")
        ET.SubElement(feats, "acpi")
        ET.SubElement(feats, "apic")
        if prof["tpm"]:
            smm = ET.SubElement(feats, "smm"); smm.set("state", "on")
        if use_kvm:
            cpu = ET.SubElement(root, "cpu")
            cpu.set("mode", "host-model"); cpu.set("check", "partial")
        clock = ET.SubElement(root, "clock"); clock.set("offset", "utc")
        for tname, tp in (("rtc", "catchup"), ("pit", "delay")):
            tm = ET.SubElement(clock, "timer"); tm.set("name", tname)
            tm.set("tickpolicy", tp)
        tm = ET.SubElement(clock, "timer"); tm.set("name", "hpet"); tm.set("present", "no")
        ET.SubElement(root, "on_poweroff").text = "destroy"
        ET.SubElement(root, "on_reboot").text = "restart"
        ET.SubElement(root, "on_crash").text = "destroy"

        devs = ET.SubElement(root, "devices")
        emu = shutil.which("qemu-system-x86_64")
        if emu:
            ET.SubElement(devs, "emulator").text = emu

        disk = self._disk_xml(disk_path, "vda" if bus == "virtio" else ("hda" if bus == "ide" else "sda"), bus)
        devs.append(disk)
        iso = params.get("iso") or ""
        if iso:
            cd = self._disk_xml(iso, "hdc" if bus == "ide" else "sdb",
                                bus if bus != "virtio" else "sata", cdrom=True)
            devs.append(cd)

        itf = self._iface_element(prof["net"], mac=new_mac())
        devs.append(itf)

        console = ET.SubElement(devs, "console"); console.set("type", "pty")
        ctgt = ET.SubElement(console, "target"); ctgt.set("type", "serial"); ctgt.set("port", "0")
        channel = ET.SubElement(devs, "channel"); channel.set("type", "unix")
        ch_tgt = ET.SubElement(channel, "target"); ch_tgt.set("type", "virtio")
        ch_tgt.set("name", "org.qemu.guest_agent.0")
        inp = ET.SubElement(devs, "input"); inp.set("type", "tablet"); inp.set("bus", "usb")

        gtype = "spice"
        gfx = ET.SubElement(devs, "graphics")
        gfx.set("type", gtype); gfx.set("autoport", "yes"); gfx.set("listen", "127.0.0.1")
        listen = ET.SubElement(gfx, "listen")
        listen.set("type", "address"); listen.set("address", "127.0.0.1")
        snd = ET.SubElement(devs, "sound"); snd.set("model", "ich6")
        video = ET.SubElement(devs, "video")
        model = ET.SubElement(video, "model")
        model.set("type", prof["video"]); model.set("heads", "1")
        if prof["video"] == "qxl":
            model.set("ram", "65536"); model.set("vram", "32768")
        else:
            model.set("vram", "16384")
        if prof["tpm"]:
            tpm = ET.SubElement(devs, "tpm")
            tpm.set("model", "tpm-crb" if machine == "q35" else "tpm-tis")
            be = ET.SubElement(tpm, "backend")
            be.set("type", "emulator"); be.set("version", "2.0")
            be.set("persistent_state", "yes")
        mb = ET.SubElement(devs, "memballoon"); mb.set("model", "virtio")

        xml = ET.tostring(root, encoding="unicode")
        self._define_maybe_uefi(root, name, uefi, prof["tpm"])
        if params.get("autostart"):
            try:
                self._dom(name).setAutostart(1)
            except Exception:
                pass
        return name

    def _name_taken(self, name):
        if not self.conn:
            return False
        try:
            self.conn.lookupByName(name)
            return True
        except Exception:
            return False

    def console_cmd(self, vm):
        if vm.state not in (1, 2, 3, 7):
            raise BackendError("VM is not running")
        exe = self.cfg.get("console") or shutil.which("virt-viewer") or shutil.which("remote-viewer")
        if not exe:
            raise BackendError("virt-viewer not installed")
        uri = self.uri()
        if "remote-viewer" in os.path.basename(exe):
            try:
                root = ET.fromstring(self._xml(vm.dom, active=True))
            except Exception as e:
                raise BackendError(str(e))
            g = root.find("devices/graphics")
            if g is None:
                raise BackendError("no graphics device")
            typ, port = g.get("type"), g.get("port")
            if port in (None, "", "0", "-1"):
                raise BackendError("graphics port not allocated")
            url = "%s://127.0.0.1:%s" % (typ, port)
            return exe, [url]
        return exe, ["-c", uri, vm.name]

    SERVICES_SCRIPT = r"""set -x
systemctl enable --now libvirtd.service || true
systemctl enable --now libvirtd.socket || true
usermod -aG libvirt,kvm {user} || true
mkdir -p /etc/polkit-1/rules.d
cat > /etc/polkit-1/rules.d/50-vmm-kvm.rules <<'POL'
polkit.addRule(function(action, subject) {{
    if ((action.id == "org.libvirt.unix.manage" ||
         action.id == "org.libvirt.unix.monitor") &&
        subject.isInGroup("libvirt")) {{
        return polkit.Result.YES;
    }}
}});
POL
virsh -c qemu:///system net-autostart default || true
virsh -c qemu:///system net-start default || true
echo __VMM_DONE__
"""

    def services_command(self):
        script = self.SERVICES_SCRIPT.replace("{user}", os.environ.get("USER", ""))
        return ["pkexec", "bash", "-c", script]

    def check_deps(self):
        def have(name):
            return shutil.which(name) is not None
        return [
            ("qemu-system-x86_64", have("qemu-system-x86_64")),
            ("qemu-img", have("qemu-img")),
            ("libvirtd", have("libvirtd")),
            ("swtpm", have("swtpm")),
            ("virt-viewer", have("virt-viewer") or have("remote-viewer")),
            ("OVMF (UEFI)", find_ovmf() is not None),
            ("dnsmasq/passt", have("dnsmasq") or have("passt")),
            ("KVM /dev/kvm", os.path.exists("/dev/kvm")),
        ]
