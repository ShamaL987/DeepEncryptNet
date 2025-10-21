# capture_https.py
import os, sys, subprocess, shutil, signal

# ====== CONFIG ======
# Capture both HTTPS (TCP/443) and QUIC (UDP/443)
BPF_FILTER = 'tcp port 443 or udp port 443'

# Output header (only what we need)
HEADER = "timestamp,src_ip,src_port,dst_ip,dst_port,protocol"

# Fields captured from TShark
FIELDS = [
    "frame.time_epoch",   # timestamp
    "ip.src",             # source IP
    "tcp.srcport",        # TCP source port (if TCP)
    "udp.srcport",        # UDP source port (if UDP)
    "ip.dst",             # destination IP
    "tcp.dstport",        # TCP destination port (if TCP)
    "udp.dstport",        # UDP destination port (if UDP)
    "_ws.col.Protocol"    # human-readable protocol name (TCP/UDP/QUIC)
]

# ====== PATH HELPERS ======
def exe_dir():
    """Return current executable or script directory."""
    return os.path.dirname(sys.executable) if getattr(sys, "frozen", False) else os.path.dirname(os.path.abspath(__file__))

def ensure_dirs(base):
    """Ensure captures directory exists and return paths."""
    capdir = os.path.join(base, "captures")
    os.makedirs(capdir, exist_ok=True)
    return capdir, os.path.join(capdir, "live_https.csv")

def write_header_once(csv_path):
    """Write CSV header only if file is new."""
    if not os.path.exists(csv_path) or os.path.getsize(csv_path) < 5:
        with open(csv_path, "w", encoding="utf-8", newline="") as f:
            f.write(HEADER + "\n")

# ====== TSHARK HELPERS ======
def find_tshark():
    """Locate tshark executable."""
    for p in (
        r"C:\Program Files\Wireshark\tshark.exe",
        r"C:\Program Files (x86)\Wireshark\tshark.exe",
        shutil.which("tshark") or ""
    ):
        if p and os.path.exists(p):
            return p
    return None

def list_ifaces(tshark):
    """List all available network interfaces."""
    out = subprocess.check_output([tshark, "-D"], text=True, stderr=subprocess.DEVNULL)
    lines = [ln.strip() for ln in out.splitlines() if ln.strip()]
    parsed = []
    for ln in lines:
        try:
            idx = int(ln.split(".", 1)[0].strip())
            parsed.append((idx, ln))
        except Exception:
            pass
    return parsed

def build_args(tshark, iface):
    """Build arguments for tshark subprocess."""
    args = [
        tshark, "-i", str(iface),
        "-f", BPF_FILTER,
        "-l",
        "-T", "fields",
        "-E", "header=n",
        "-E", "separator=,",
    ]
    for f in FIELDS:
        args.extend(["-e", f])
    return args

def probe_iface(tshark, iface_idx, bpf):
    """Quickly test if an interface works."""
    cmd = [tshark, "-i", str(iface_idx), "-f", bpf, "-a", "duration:2", "-c", "1"]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True)
        if proc.returncode == 0:
            return True, ""
        err = (proc.stderr or "") + (("\n" + proc.stdout) if proc.stdout else "")
        return False, err.strip()
    except Exception as e:
        return False, str(e)

def pick_iface_validated(tshark, parsed_list, bpf):
    """Ask user for interface, validate it's working."""
    while True:
        print("\nAvailable interfaces:")
        for idx, ln in parsed_list:
            print(ln)

        default = next((idx for idx, ln in parsed_list
                        if any(k in ln.lower() for k in ("wi-fi","wifi","wireless","ethernet"))), None)
        prompt = f"\nEnter interface index to capture (number before the dot){f' [{default}]' if default else ''}: "
        ans = input(prompt).strip()
        iface_idx = default if (ans == "" and default is not None) else (int(ans) if ans.isdigit() else None)

        if iface_idx is None or not any(idx == iface_idx for idx, _ in parsed_list):
            print("Invalid index, try again.")
            continue

        ok, err = probe_iface(tshark, iface_idx, bpf)
        if ok:
            print(f"[OK] Interface {iface_idx} passed the probe.")
            return iface_idx
        print("\n[ERROR] TShark couldn't start on that interface. Details:\n" + (err or "(no message)"))
        print("Tip: choose your real Wi-Fi/Ethernet adapter (not Hyper-V/WSL/Default Switch) and run as Administrator.\n")

def need_admin_hint():
    try:
        import ctypes
        return not ctypes.windll.shell32.IsUserAnAdmin()
    except Exception:
        return False

# ====== MAIN ======
def main():
    base = exe_dir()
    capdir, csv_path = ensure_dirs(base)

    tshark = find_tshark()
    if not tshark:
        print("[ERROR] tshark.exe not found. Install Wireshark (with Npcap): https://www.wireshark.org/download.html")
        input("Press Enter to exit...")
        return

    if need_admin_hint():
        print("[WARNING] Run as Administrator for capture to work (right-click the .py/.exe → Run as administrator).\n")

    try:
        parsed = list_ifaces(tshark)
    except subprocess.CalledProcessError as e:
        print("[ERROR] Unable to list interfaces via 'tshark -D'.")
        print(e)
        input("Press Enter to exit...")
        return

    if not parsed:
        print("[ERROR] No interfaces returned by 'tshark -D'.")
        input("Press Enter to exit...")
        return

    iface_idx = pick_iface_validated(tshark, parsed, BPF_FILTER)
    write_header_once(csv_path)

    args = build_args(tshark, iface_idx)
    print("\nWriting live CSV to:", csv_path)
    print("Filter:", BPF_FILTER)
    print("Interface:", iface_idx)
    print("(Press CTRL+C in this window to stop)\n")

    # Stream stdout → CSV (flush each line)
    with open(csv_path, "a", encoding="utf-8", newline="") as out:
        proc = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1)

        def stop(_sig=None, _frm=None):
            try:
                proc.terminate()
            except Exception:
                pass
            sys.exit(0)

        signal.signal(signal.SIGINT, stop)

        try:
            for line in proc.stdout:
                if not line or not line.strip():
                    continue
                parts = line.strip().split(",")
                if len(parts) < 8:
                    continue

                # Extract only valid fields
                timestamp, src_ip, tcp_sport, udp_sport, dst_ip, tcp_dport, udp_dport, proto = parts[:8]

                # Pick correct ports depending on protocol
                protocol = proto.lower()
                if "tcp" in protocol:
                    src_port, dst_port = tcp_sport, tcp_dport
                elif "udp" in protocol:
                    src_port, dst_port = udp_sport, udp_dport
                else:
                    continue  # skip non-TCP/UDP (e.g., QUIC metadata)

                out.write(f"{timestamp},{src_ip},{src_port},{dst_ip},{dst_port},{protocol}\n")
                out.flush()

            rc = proc.wait()
            print(f"[INFO] tshark exited with code {rc}.")

        except KeyboardInterrupt:
            stop()
        finally:
            try:
                proc.terminate()
            except Exception:
                pass

if __name__ == "__main__":
    main()
