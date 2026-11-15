# NetDefender

A Python monitor that watches the connections on **your own network** through SSH to your router/gateway, analyzes every public IP that shows up (WHOIS/RDAP, ASN, reverse DNS, threat feeds) and lets you block it manually or automatically.

> ⚠️ **Legitimate use only.** Use it only on networks and devices that you own or have explicit authorization to monitor. The author is not responsible for misuse.

---

## Features

- Operating system and WiFi SSID detection on startup (Windows and Linux).
- SSH connection to the router/gateway using [paramiko](https://www.paramiko.org/).
- Automatic remote profile detection: **MikroTik RouterOS** or **Linux** (conntrack / iptables).
- Continuous reading of active connections and extraction of public IPs.
- Parallel analysis of every new IP:
  - RDAP/WHOIS (ASN, description, country, network name) via `ipwhois`
  - Forward-confirmed reverse DNS
  - [Shodan InternetDB](https://internetdb.shodan.io/) (tags and exposed vulnerabilities)
  - [AbuseIPDB](https://www.abuseipdb.com/) (optional, requires an API key)
  - Tor exit node list
  - Threat feeds: Spamhaus DROP, Feodo Tracker, Emerging Threats, Blocklist.de
- Owner classification: **ISP**, **COMPANY**, **HOSTING** or **UNKNOWN**.
- Risk score from 0 to 100 with verdicts `[OK]`, `[?]` (suspicious) and `[ALERT]` (dangerous).
- Persistent whitelist and blacklist stored in plain text files, with CIDR network support.
- **Manual** mode (asks you) and **automatic** mode (blocks by itself), switchable at any time.
- Hourly limit on automatic blocks: if exceeded, it falls back to manual mode.
- Interactive menu available at any moment with `Ctrl+C`.

---

## Requirements

### On the machine running NetDefender

| Requirement | Details |
|---|---|
| Python | 3.8 or newer |
| Dependencies | `paramiko`, `ipwhois` |
| Network | Internet access (RDAP, feeds, InternetDB) and SSH access to the router |
| Runtime | The device should stay powered on and running continuously |

All other modules (`os`, `sys`, `json`, `socket`, `subprocess`, `re`, `platform`, `time`, `ipaddress`, `urllib`, `collections`, `concurrent.futures`) are part of the Python standard library.

### On the remote device (router / gateway)

**Option A: Linux** (OpenWrt, gateway server, Raspberry Pi, etc.)
- A running SSH server.
- `root` user, **or** a user with passwordless `sudo` (the script uses `sudo -n`).
- At least one of the following to list connections: `/proc/net/nf_conntrack`, `/proc/net/ip_conntrack`, or the `conntrack` tool. (As a last resort it falls back to `ss -tnH state established`, which only shows the device's own connections, not the whole network.)
- `iptables` to block, and `conntrack` to cut connections that are already established.

**Option B: MikroTik RouterOS**
- SSH enabled (`/ip service`).
- A user allowed to read `/ip firewall connection` and modify `/ip firewall filter` and address lists.
- The script automatically creates two `drop` rules (forward chain) tied to the `monitor-blacklist` address list.

---

## Installation

### 1. Clone the repository

```bash
git clone https://github.com/iori95gdl-pixel/NetDefender.git
cd NetDefender
```

### 2. Install dependencies

#### Linux (Debian / Ubuntu / Kali)

```bash
sudo apt update
sudo apt install -y python3 python3-pip python3-venv
python3 -m venv venv
source venv/bin/activate
pip install paramiko ipwhois
```

#### Windows (PowerShell)

```powershell
py -m venv venv
venv\Scripts\Activate.ps1
pip install paramiko ipwhois
```

> If PowerShell blocks activation: `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`

#### macOS

```bash
brew install python
python3 -m venv venv
source venv/bin/activate
pip install paramiko ipwhois
```

#### Termux (Android)

```bash
pkg update && pkg upgrade -y
pkg install -y python openssl libffi rust binutils
pip install paramiko ipwhois
```

#### Using `requirements.txt` (optional)

Create a `requirements.txt` file:

```
paramiko
ipwhois
```

and install with:

```bash
pip install -r requirements.txt
```

### 3. (Optional) AbuseIPDB API key

Improves detection. A free tier with a daily limit is available.

```bash
# Linux / macOS / Termux
export ABUSEIPDB_KEY="your_api_key"

# Windows PowerShell
$env:ABUSEIPDB_KEY = "your_api_key"

# Windows CMD
set ABUSEIPDB_KEY=your_api_key
```

If you don't set it, that lookup is simply skipped.

---

## Usage

```bash
python3 NetDefender.py      # Linux / macOS / Termux
py NetDefender.py           # Windows
```

### Startup flow

1. **System detection** and WiFi SSID check (on Windows, location permissions must be enabled; if no WiFi is detected you can still continue by answering `y`).
2. **SSH credentials:** host, port (default 22), username and password. You are asked to confirm them before connecting.
3. **Mode selection:**
   - `1` → **Manual** (default): asks you what to do with each suspicious IP.
   - `2` → **Automatic**: blocks dangerous IPs by itself.
4. NetDefender detects the remote profile (`mikrotik` or `linux`), applies the blacklist to the router, downloads the threat feeds and enters the monitoring loop.

### What you will see

```
[2026-11-15 20:14] [OK] [ISP] 189.x.x.x -> TELMEX | AS8151 MX | score 0
[2026-11-15 20:14] [?] [UNKNOWN] 203.x.x.x -> ... | score 30 | owner not in any list
[2026-11-15 20:15] [ALERT] [HOSTING] 45.x.x.x -> ... | score 90 | listed in feodo
| MANUAL | conn 42 | seen 17 | pending 1 | Ctrl+C: menu
```

| Tag | Meaning |
|---|---|
| `[OK]` (green) | Score below 25. Marked as checked and not analyzed again. |
| `[?]` (yellow) | Score 25–59. Suspicious. |
| `[ALERT]` (red) | Score 60 or higher. Dangerous. |

---

## How it works

### Monitoring loop

1. Every `INTERVAL` seconds (0.5 by default) it runs the connection listing command over SSH.
2. It extracts **public** IPs only (private, loopback, link-local, multicast and reserved addresses are ignored).
3. For each new IP it checks: whitelist → blacklist → full analysis.
4. Analysis runs in a thread pool so monitoring is never blocked.
5. Threat feeds and the Tor list are refreshed every `INTEL_REFRESH` seconds (3 hours by default).

### Scoring system

| Factor | Points |
|---|---|
| Owner not recognized (not in ISP/COMPANY/HOSTING lists) | +25 |
| No confirmed reverse DNS (when the owner is also unknown) | +5 |
| No WHOIS data | +10 |
| Hosting provider (only if `ALLOW_HOSTING = False`) | +25 |
| ASN in `BAD_ASNS` | +60 |
| Country in `WATCH_COUNTRIES` | +15 |
| Tor exit node | +60 |
| Listed in threat feeds | feed weight (40–90) + 10 per additional feed |
| InternetDB tags (`malware`, `compromised`, `doublepulsar`, `scanner`, `tor`, `proxy`, `vpn`) | highest tag weight (10–70) |
| 5 or more known exposed vulnerabilities | +5 |
| AbuseIPDB confidence ≥ 10% | +80% of the confidence value |

The result is capped at 100. IPs whose ASN is in `TRUSTED_ASNS` (Google, Cloudflare, AWS, Microsoft, Meta, Akamai, Apple, Netflix, Fastly, GitHub, Telmex, Totalplay, Telcel) are treated as trusted.

### Decision by mode

| Verdict | Manual mode | Automatic mode |
|---|---|---|
| OK | Ignored | Ignored |
| Suspicious | Asks: `y` block, `n` allow, `s` decide later | Depends on `AUTO_SUSPICIOUS_ACTION`: `queue` (review queue), `allow` or `block` |
| Dangerous | Asks | Blocks and adds to the blacklist |

If in automatic mode more than `AUTO_BLOCK_LIMIT` blocks (10) happen within `AUTO_BLOCK_WINDOW` (1 hour), NetDefender **switches to manual mode by itself** as a safety measure.

### How it blocks

**Linux:** inserts `iptables -j DROP` rules in `FORWARD` (source and destination), `INPUT` and `OUTPUT`, and removes active connections with `conntrack -D`.

**MikroTik:** adds the IP to the `monitor-blacklist` address list (the drop rules are created automatically).

---

## Menu (Ctrl+C)

| Option | Action |
|---|---|
| `1` | Switch between manual and automatic mode |
| `2` | Show whitelist |
| `3` | Show blacklist |
| `4` | Add an IP or network to the whitelist |
| `5` | Add an IP or network to the blacklist (and block it) |
| `6` | Remove from whitelist |
| `7` | Remove from blacklist (and unblock) |
| `8` | Review pending IPs |
| `9` | Refresh threat feeds now |
| `0` | Resume monitoring |
| `q` | Quit |

Accepts single IPs (`8.8.8.8`) or CIDR networks (`8.8.8.0/24`).

---

## Generated files

Created next to the script:

| File | Description |
|---|---|
| `whitelist.txt` | Trusted IPs/networks, one per line. Format: `IP  # note` |
| `blacklist.txt` | Blocked IPs/networks, same format |
| `providers.txt` | (Optional, you create it) extra provider names |

`providers.txt` format, one name per line with an optional category prefix:

```
isp: my local provider
company: my company
hosting: my hosting
some name without prefix   # treated as company
```

---

## Configuration

Edit the constants at the top of `NetDefender.py`:

| Variable | Default | Description |
|---|---|---|
| `ALLOW_HOSTING` | `True` | If `False`, hosting providers add to the score |
| `USE_INTERNETDB` | `True` | Query Shodan InternetDB |
| `APPLY_BLACKLIST_ON_START` | `True` | Apply the blacklist to the router on startup |
| `AUTO_SUSPICIOUS_ACTION` | `"queue"` | `queue`, `allow` or `block` for suspicious IPs in auto mode |
| `SUSPICIOUS_AT` | `25` | Minimum score for suspicious |
| `DANGER_AT` | `60` | Minimum score for dangerous |
| `AUTO_BLOCK_LIMIT` | `10` | Maximum automatic blocks per window |
| `AUTO_BLOCK_WINDOW` | `3600` | Window in seconds |
| `INTERVAL` | `0.5` | Seconds between connection reads |
| `INTEL_REFRESH` | `10800` | Seconds between feed updates |
| `ANALYSIS_TIMEOUT` | `10` | Maximum time per IP analysis |
| `BAD_ASNS` | `set()` | ASNs you want to penalize |
| `WATCH_COUNTRIES` | `set()` | Country codes to watch (e.g. `{"RU", "CN"}`) |
| `PROTECTED_IPS` | `set()` | IPs that are **never** analyzed or blocked |
| `TRUSTED_ASNS` | see code | Trusted ASNs and their category |

> **Important:** add your own public IP, your gateway/ISP IP and any management IP (including the SSH host if it is public) to `PROTECTED_IPS`. This prevents you from blocking yourself.

---

## Troubleshooting

| Problem | Possible cause / fix |
|---|---|
| `Failed to connect via SSH` | Check host, port, username and password; make sure the SSH service is running and reachable. |
| `Could not retrieve connections` | The user cannot read conntrack. Use `root` or configure passwordless `sudo` (`NOPASSWD`). |
| Only your own connections appear | It fell back to `ss`. The router needs `nf_conntrack` or the `conntrack` tool. |
| Windows does not detect the SSID | Enable location permissions: `start ms-settings:privacy-location`. On a VM or Ethernet, continue with `y`. |
| `paramiko` fails to install on Termux | Install `rust`, `binutils`, `openssl` and `libffi` first. |
| Too many false positives | Add IPs to the whitelist, names to `providers.txt`, or ASNs to `TRUSTED_ASNS`. |
| `Could not load feed ...` | No Internet or the feed is down; the monitor keeps working with the others. |
| Strange colors in the terminal | Use a terminal with ANSI support (Windows Terminal, modern PowerShell). |

---

## Security notes

- SSH credentials are requested on the console and **never saved** to disk.
- The script uses `AutoAddPolicy` for unknown host keys, which accepts any key the first time. For stronger security, use `RejectPolicy` with a known `known_hosts` file or authenticate with a public key.
- Create a dedicated router user with minimal permissions instead of using `root`.
- Review the whitelist and blacklist regularly.
- In automatic mode, a false positive can cut off a legitimate service; start in **manual mode** until your lists are tuned.

---

## Free and open source

NetDefender is free and open source. Use it, study it, modify it and share it. Contributions, issues and pull requests are welcome.

---

## Disclaimer

This tool is intended for **defending and monitoring your own networks**. The author is not responsible for misuse or for any damage resulting from its use.
