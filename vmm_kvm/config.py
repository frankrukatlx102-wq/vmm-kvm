import json
import os

CFG_DIR = os.path.join(os.path.expanduser("~"), ".config", "vmm-kvm")
CFG_FILE = os.path.join(CFG_DIR, "config.json")

DEFAULTS = {
    "lang": "",
    "base_dir": "~/VirtualMachines",
    "connection": "session",
    "console": "",
    "ssh_hosts": [],
    "win": {"w": 1280, "h": 800},
}


def load():
    cfg = json.loads(json.dumps(DEFAULTS))
    try:
        with open(CFG_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        for k, v in data.items():
            if k in cfg:
                cfg[k] = v
    except Exception:
        pass
    return cfg


def save(cfg):
    try:
        os.makedirs(CFG_DIR, exist_ok=True)
        tmp = CFG_FILE + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(cfg, f, ensure_ascii=False, indent=2)
        os.replace(tmp, CFG_FILE)
    except OSError:
        pass


def paths(cfg):
    base = os.path.expanduser(cfg.get("base_dir") or "~/VirtualMachines")
    p = {
        "base": base,
        "vms": os.path.join(base, "vms"),
        "iso": os.path.join(base, "iso"),
        "snapshots": os.path.join(base, "snapshots"),
        "logs": os.path.join(base, "logs"),
    }
    try:
        for v in p.values():
            os.makedirs(v, exist_ok=True)
    except OSError:
        pass
    return p
