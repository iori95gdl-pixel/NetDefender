import os
import sys
import json
import socket
import subprocess
import re
import platform
import paramiko
import time
import ipaddress
import urllib.request
from collections import deque
from concurrent.futures import ThreadPoolExecutor
from ipwhois import IPWhois

os.system("")

GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
CYAN = "\033[96m"
RESET = "\033[0m"
CLEAR = "\033[2K\r"

def paint(text, color):
    return f"{color}{text}{RESET}"

def now():
    return time.strftime("%Y-%m-%d %H:%M")

def log(text, color):
    print(CLEAR + paint(f"[{now()}] {text}", color))

print("Detecting operating system...")
time.sleep(1)
sys_name = platform.system()
print("Hi im your assistant, i will help you to set this monitoring tool, please follow the instructions.")
time.sleep(2)
print("you need a device running this script forever.")
time.sleep(3)
print("looks like you are in a " + sys_name + " system.")
time.sleep(2)
print("well, lets check if you are connected to a network, this is important for the tool to work.")
time.sleep(3)

def get_ssid():
    if sys_name == "Windows":
        r = subprocess.run(
            ["netsh", "wlan", "show", "interfaces"],
            capture_output=True, text=True, encoding="utf-8", errors="ignore"
        )
        out = r.stdout
        if "ubicaci" in out.lower() or "location" in out.lower() or "elevaci" in out.lower():
            print("Maybe windows is running a VM or is blocking ubication permissions, please check your settings.")
            print("For windows 11: start ms-settings:privacy-location")
            print("and enable all location permissions for apps and services.")
            return None
        m = re.search(r"^\s*SSID\s*:\s*(.+)$", out, re.MULTILINE)
        return m.group(1).strip() if m else None
    else:
        cmds = [
            "iwgetid -r",
            "nmcli -t -f active,ssid dev wifi | grep '^yes' | cut -d: -f2-",
            "nmcli -t -f NAME,TYPE connection show --active | grep wireless | cut -d: -f1",
            "iw dev | awk '/ssid/ {print $2}'",
        ]
        for c in cmds:
            out = subprocess.getoutput(c).strip()
            if out and "not found" not in out.lower() and "command" not in out.lower():
                return out.splitlines()[0].strip()
        return None

while True:
    ssid = get_ssid()
    if ssid:
        print(f"looks like you are connected to: {ssid} i like that name, lets continue.")
        time.sleep(2)
        break
    else:
        ans = input("No WiFi detected (or Ethernet/VM in use). Continue anyway (y/n)? ").strip().lower()
        if ans == "y":
            break

print("well, this tool works via SSH, so you need to connect SSH to the target")
time.sleep(2)

while True:
    ssh_host = input("Enter the SSH host (IP or hostname): ").strip()
    ssh_port = input("Enter the SSH port (default 22): ").strip() or "22"
    ssh_user = input("Enter the SSH username: ").strip()
    ssh_pass = input("Enter the SSH password: ").strip()
    time.sleep(1)

    print("are these credentials correct?")
    print(f"Host: {ssh_host}")
    print(f"Port: {ssh_port}")
    print(f"Username: {ssh_user}")

    while True:
        option = input("y/n: ").strip().lower()
        if option in ("y", "n"):
            break
        print("Invalid option. Please enter 'y' or 'n'.")

    if option == "n":
        print("Please re-enter the SSH credentials.")
        continue

    try:
        ssh_client = paramiko.SSHClient()
        ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh_client.connect(ssh_host, port=int(ssh_port), username=ssh_user, password=ssh_pass, timeout=10)
        log(f"Successfully connected to {ssh_host} via SSH.", GREEN)
        break
    except Exception as e:
        log(f"Failed to connect via SSH: {e}. Please check your credentials and try again.", RED)

time.sleep(2)
print("Ok we are now connected via SSH, ")
time.sleep(2)
print("this tool is going to monitor your network and detect possible intrusions")
time.sleep(2)
print("it maybe detect false positives but it will improve over time, and you can add trusted IPs to the list ")
time.sleep(2)
print("see your whitelist and blacklist in the log, and you can block connections to untrusted IPs")
time.sleep(2)
print("you can put in automatic mode or manual in any moment")
time.sleep(2)
print("press Ctrl+C at any moment to open the menu")
time.sleep(2)
print("autor not responsible for any bad use")
time.sleep(1)

while True:
    choice = input("Select mode: 1 = manual (asks you), 2 = automatic (blocks by itself). Default 1: ").strip() or "1"
    if choice in ("1", "2"):
        break
    print("Invalid option.")
mode = "auto" if choice == "2" else "manual"

print("Starting the monitoring tool...")
sudo = "" if ssh_user == "root" else "sudo -n "

ISP_NAMES = [
    "totalplay", "total play", "telmex", "uninet", "telcel", "radiomovil", "izzi", "cablevision",
    "televisión internacional", "megacable", "mega cable", "axtel", "alestra", "maxcom", "bestel",
    "iusacell", "at&t", "att", "movistar", "telefonica", "claro", "america movil", "dish", "bait",
    "altan", "virgin mobile", "unefon", "cablemas", "cablecom", "telecable", "sky mexico", "netcom",
    "marcatel", "kio networks", "triara", "transtelco", "ufinet", "metrored", "tigo", "liberty",
    "digicel", "cable & wireless", "flow", "etb", "une epm", "entel", "vtr", "gtd", "wom", "vivo",
    "tim brasil", "oi s.a.", "embratel", "algar", "copel", "personal", "telecom argentina", "arnet",
    "antel", "ancel", "cantv", "movilnet", "digitel", "ucom", "tricom", "cnt", "claro peru",
    "verizon", "comcast", "xfinity", "spectrum", "charter", "cox", "centurylink", "frontier",
    "windstream", "optimum", "altice", "suddenlink", "t-mobile", "sprint", "google fiber",
    "rogers", "bell canada", "telus", "shaw", "videotron", "cogeco", "vodafone", "orange",
    "deutsche telekom", "telekom", "bt group", "british telecom", "sky broadband", "virgin media",
    "talktalk", "plusnet", "jazztel", "masmovil", "digi", "swisscom", "sunrise", "salt",
    "telenor", "telia", "tele2", "proximus", "telecom italia", "fastweb", "wind tre", "iliad",
    "free sas", "bouygues", "sfr", "kpn", "ziggo", "odido", "a1 telekom", "magenta", "eir",
    "ntt", "kddi", "softbank", "china telecom", "china unicom", "china mobile", "korea telecom",
    "sk broadband", "lg uplus", "singtel", "starhub", "telstra", "optus", "vocus", "spark new zealand",
    "airtel", "reliance jio", "bsnl", "tata communications", "pldt", "globe telecom", "true corporation",
    "chunghwa", "hkt", "pccw", "maxis", "telkom", "etisalat", "du telecom", "stc", "zain", "mtn",
    "safaricom", "orange africa", "turkcell", "turk telekom", "rostelecom", "mts", "beeline", "megafon",
    "level 3", "lumen", "cogent", "gtt", "zayo", "arelion", "telxius", "sparkle", "hurricane electric",
    "tata", "pccw global", "he.net"
]

COMPANY_NAMES = [
    "google", "youtube", "cloudflare", "amazon", "aws", "microsoft", "azure", "akamai", "facebook",
    "meta platforms", "meta", "instagram", "whatsapp", "apple", "netflix", "fastly", "github", "gitlab",
    "bitbucket", "atlassian", "twitter", "x corp", "tiktok", "bytedance", "spotify", "valve", "steam",
    "oracle", "ibm", "zoom", "dropbox", "adobe", "salesforce", "slack", "shopify", "paypal", "stripe",
    "ebay", "alibaba", "tencent", "baidu", "samsung", "sony", "nintendo", "playstation", "electronic arts",
    "epic games", "riot games", "blizzard", "activision", "twitch", "discord", "reddit", "pinterest",
    "linkedin", "snapchat", "snap inc", "telegram", "signal", "openai", "anthropic", "cloudfront",
    "edgecast", "limelight", "stackpath", "imperva", "incapsula", "sucuri", "verizon digital media",
    "bunny", "cdn77", "keycdn", "jsdelivr", "unpkg", "wikimedia", "mozilla", "canonical", "debian",
    "ubuntu", "redhat", "red hat", "docker", "npm", "pypi", "cisco", "juniper", "palo alto", "fortinet",
    "check point", "sophos", "mcafee", "symantec", "broadcom", "vmware", "dell", "hp inc", "hewlett",
    "lenovo", "asus", "intel", "nvidia", "amd", "qualcomm", "xiaomi", "huawei", "oppo", "vivo mobile",
    "tp-link", "netgear", "ubiquiti", "mikrotik", "roku", "sonos", "ring", "nest", "tuya", "philips",
    "cloudflarenet", "teamviewer", "anydesk", "notion", "figma", "canva", "trello", "asana", "hubspot",
    "zendesk", "twilio", "sendgrid", "mailchimp", "intercom", "datadog", "newrelic", "sentry", "okta",
    "auth0", "duo security", "mercadolibre", "mercado libre", "mercadopago", "rappi", "uber", "didi",
    "cabify", "bbva", "banorte", "santander", "citibanamex", "hsbc", "scotiabank", "inbursa", "banregio",
    "visa", "mastercard", "american express", "walmart", "costco", "liverpool", "coppel", "elektra",
    "cfe", "pemex", "sat mexico", "imss", "gob.mx", "unam", "ipn", "tec de monterrey", "bing", "yahoo",
    "duckduckgo", "brave software", "opera", "avast", "kaspersky", "eset", "malwarebytes", "bitdefender",
    "1e100", "fbcdn"
]

HOSTING_NAMES = [
    "digitalocean", "digital ocean", "linode", "akamai connected cloud", "vultr", "choopa", "ovh",
    "hetzner", "scaleway", "online sas", "leaseweb", "contabo", "hostinger", "godaddy", "namecheap",
    "bluehost", "hostgator", "siteground", "dreamhost", "wpengine", "kinsta", "rackspace", "softlayer",
    "equinix", "packet host", "cherry servers", "upcloud", "ionos", "1&1", "strato", "hostwinds",
    "liquid web", "inmotion", "a2 hosting", "heroku", "netlify", "vercel", "render services",
    "fly.io", "railway", "google cloud", "alibaba cloud", "tencent cloud", "oracle cloud", "ibm cloud",
    "cloudflare workers", "backblaze", "wasabi", "cloudsigma", "kamatera", "ramnode", "interserver",
    "hostpapa", "ipage", "web.com", "network solutions", "register.com", "tucows", "enom", "hover",
    "gandi", "ovhcloud", "infomaniak", "aruba", "register.it", "seeweb", "serverplan", "netcup",
    "hosteurope", "host europe", "webhostingpad", "greengeeks", "fatcow", "ipower", "hostmonster",
    "arvixe", "justhost", "lunarpages", "midphase", "site5", "webfaction", "pair networks",
    "jaguar network", "datapacket", "cdnetworks", "nforce", "worldstream", "tzulo", "limestone",
    "nocix", "reliablesite", "servermania", "singlehop", "steadfast", "webair", "hivelocity",
    "colo4", "cyrusone", "digital realty", "coresite", "switch inc", "flexential", "iron mountain",
    "mexico hosting", "hostgator mexico", "hostmx", "dattaweb", "cpanel", "plesk", "hostdime",
    "bluehost mexico", "wix", "squarespace", "weebly", "godaddy mexico", "dreamhost mexico"
]

TRUSTED_ASNS = {
    "15169": ("company", "google"),
    "13335": ("company", "cloudflare"),
    "16509": ("hosting", "amazon aws"),
    "14618": ("hosting", "amazon aws"),
    "8075": ("company", "microsoft"),
    "32934": ("company", "meta"),
    "20940": ("company", "akamai"),
    "714": ("company", "apple"),
    "2906": ("company", "netflix"),
    "54113": ("company", "fastly"),
    "36459": ("company", "github"),
    "8151": ("isp", "telmex"),
    "17072": ("isp", "totalplay"),
    "28403": ("isp", "telcel"),
}

BAD_ASNS = set()
WATCH_COUNTRIES = set()
PROTECTED_IPS = set()

ALLOW_HOSTING = True
USE_INTERNETDB = True
APPLY_BLACKLIST_ON_START = True
AUTO_SUSPICIOUS_ACTION = "queue"
ABUSEIPDB_KEY = os.environ.get("ABUSEIPDB_KEY", "")

SUSPICIOUS_AT = 25
DANGER_AT = 60
AUTO_BLOCK_LIMIT = 10
AUTO_BLOCK_WINDOW = 3600
INTERVAL = 0.5
INTEL_REFRESH = 10800
ANALYSIS_TIMEOUT = 10

FEEDS = {
    "spamhaus-drop": (["https://www.spamhaus.org/drop/drop_v4.json", "https://www.spamhaus.org/drop/drop.txt"], 80),
    "feodo": (["https://feodotracker.abuse.ch/downloads/ipblocklist.txt"], 90),
    "et-compromised": (["https://rules.emergingthreats.net/blockrules/compromised-ips.txt"], 50),
    "blocklist-de": (["https://lists.blocklist.de/lists/all.txt"], 40),
}

TAG_WEIGHTS = {
    "malware": 60,
    "compromised": 60,
    "doublepulsar": 70,
    "scanner": 30,
    "tor": 40,
    "proxy": 10,
    "vpn": 10,
}

CATEGORY_NAMES = {
    "isp": [n.lower() for n in ISP_NAMES],
    "company": [n.lower() for n in COMPANY_NAMES],
    "hosting": [n.lower() for n in HOSTING_NAMES],
}

CATEGORY_LABELS = {
    "isp": "ISP",
    "company": "COMPANY",
    "hosting": "HOSTING",
}

VERDICT_TAGS = {"ok": "[OK]", "suspicious": "[?]", "danger": "[ALERT]"}
VERDICT_COLORS = {"ok": GREEN, "suspicious": YELLOW, "danger": RED}

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
WHITELIST_FILE = os.path.join(BASE_DIR, "whitelist.txt")
BLACKLIST_FILE = os.path.join(BASE_DIR, "blacklist.txt")
PROVIDERS_FILE = os.path.join(BASE_DIR, "providers.txt")

def net_text(net):
    return str(net.network_address) if net.num_addresses == 1 else str(net)

class IPList:
    def __init__(self, path):
        self.path = path
        self.entries = {}
        self.load()

    def load(self):
        self.entries = {}
        try:
            with open(self.path, "r", encoding="utf-8") as f:
                for line in f:
                    raw = line.strip()
                    if not raw or raw.startswith("#"):
                        continue
                    value, _, note = raw.partition("#")
                    try:
                        net = ipaddress.ip_network(value.strip(), strict=False)
                    except ValueError:
                        continue
                    self.entries[net] = note.strip()
        except OSError:
            pass

    def save(self):
        with open(self.path, "w", encoding="utf-8") as f:
            for net, note in self.entries.items():
                f.write(f"{net_text(net)}  # {note}\n" if note else f"{net_text(net)}\n")

    def contains(self, ip):
        addr = ipaddress.ip_address(ip)
        return any(addr in net for net in self.entries)

    def note_for(self, ip):
        addr = ipaddress.ip_address(ip)
        for net, note in self.entries.items():
            if addr in net:
                return note
        return ""

    def add(self, value, note=""):
        self.entries[ipaddress.ip_network(value, strict=False)] = note
        self.save()

    def remove(self, value):
        net = ipaddress.ip_network(value, strict=False)
        if net in self.entries:
            del self.entries[net]
            self.save()
            return True
        return False

whitelist = IPList(WHITELIST_FILE)
blacklist = IPList(BLACKLIST_FILE)

def load_extra_names():
    try:
        with open(PROVIDERS_FILE, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip().lower()
                if not line:
                    continue
                category = "company"
                for prefix in ("isp:", "company:", "hosting:"):
                    if line.startswith(prefix):
                        category = prefix[:-1]
                        line = line[len(prefix):].strip()
                        break
                if line:
                    CATEGORY_NAMES[category].append(line)
    except OSError:
        pass

load_extra_names()

checked = {}
pending = {}
profile = None
active_command = None
tor_exits = set()
feed_ips = {}
feed_nets = {}
intel_last = 0
mikrotik_ready = False
spin_index = 0
auto_block_times = deque()
protected_ips = set(PROTECTED_IPS)
executor = ThreadPoolExecutor(max_workers=16)
analysis_pool = ThreadPoolExecutor(max_workers=4)

def status_line(connections):
    global spin_index
    spin_index = (spin_index + 1) % 4
    spin = "|/-\\"[spin_index]
    text = f"{spin} {mode.upper()} | conn {connections} | seen {len(checked)} | pending {len(pending)} | Ctrl+C: menu"
    sys.stdout.write(CLEAR + paint(text, CYAN))
    sys.stdout.flush()

def fetch_text(url, timeout=20, headers=None):
    req = urllib.request.Request(url, headers=headers or {"User-Agent": "wifi-monitor/1.0"})
    return urllib.request.urlopen(req, timeout=timeout).read().decode("utf-8", errors="ignore")

def fetch_tor_exits():
    global tor_exits
    try:
        raw = fetch_text("https://check.torproject.org/torbulkexitlist", timeout=15)
        tor_exits = set(x.strip() for x in raw.splitlines() if x.strip())
        log(f"Tor exit list loaded: {len(tor_exits)} nodes.", GREEN)
    except Exception as e:
        log(f"Could not load Tor exit list: {e}", YELLOW)

def load_feeds():
    pattern = re.compile(r"\b\d{1,3}(?:\.\d{1,3}){3}(?:/\d{1,2})?\b")
    for name, (urls, weight) in FEEDS.items():
        text = None
        for url in urls:
            try:
                text = fetch_text(url)
                break
            except Exception:
                continue
        if text is None:
            log(f"Could not load feed {name}", YELLOW)
            continue
        ips = set()
        nets = []
        for token in pattern.findall(text):
            if "/" in token:
                try:
                    nets.append(ipaddress.ip_network(token, strict=False))
                except ValueError:
                    pass
            else:
                ips.add(token)
        feed_ips[name] = ips
        feed_nets[name] = nets
        log(f"Feed {name} loaded: {len(ips)} IPs, {len(nets)} networks.", GREEN)

def refresh_intel():
    global intel_last
    fetch_tor_exits()
    load_feeds()
    intel_last = time.time()

def feed_hits(ip):
    addr = ipaddress.ip_address(ip)
    hits = []
    for name in FEEDS:
        if ip in feed_ips.get(name, ()) or any(addr in n for n in feed_nets.get(name, ())):
            hits.append(name)
    return hits

def run_remote(cmd):
    stdin, stdout, stderr = ssh_client.exec_command(cmd, timeout=20)
    return stdout.read().decode(errors="ignore"), stderr.read().decode(errors="ignore")

def detect_profile():
    out, _ = run_remote("/system identity print")
    if "name:" in out.lower():
        return "mikrotik"
    return "linux"

def is_public(value):
    try:
        ip = ipaddress.ip_address(value)
    except ValueError:
        return False
    return not (ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_multicast or ip.is_unspecified or ip.is_reserved)

def extract_ips(output):
    found = set()
    for line in output.splitlines():
        if "src=" in line and "dst=" in line:
            src = re.search(r"src=([\d.]+)", line)
            dst = re.search(r"dst=([\d.]+)", line)
            candidates = [m.group(1) for m in (src, dst) if m]
        else:
            candidates = re.findall(r"\b(\d{1,3}(?:\.\d{1,3}){3})\b", line)
        for c in candidates:
            if is_public(c):
                found.add(c)
    return found

def get_list_commands():
    if profile == "mikrotik":
        return ["/ip firewall connection print terse"]
    return [
        sudo + "cat /proc/net/nf_conntrack",
        sudo + "cat /proc/net/ip_conntrack",
        sudo + "conntrack -L",
        "ss -tnH state established",
    ]

def get_remote_ips():
    global active_command
    if active_command:
        out, _ = run_remote(active_command)
        return extract_ips(out)
    for cmd in get_list_commands():
        out, _ = run_remote(cmd)
        if out.strip():
            active_command = cmd
            log(f"Using command: {active_command}", GREEN)
            return extract_ips(out)
    return None

def rdap(ip):
    try:
        data = IPWhois(ip, timeout=6).lookup_rdap(depth=0, retry_count=1, inc_nir=False, rate_limit_timeout=5)
    except Exception:
        return {}
    asn = str(data.get("asn") or "")
    if asn.upper() == "NA":
        asn = ""
    return {
        "asn": asn,
        "asn_desc": data.get("asn_description") or "",
        "cc": data.get("asn_country_code") or "",
        "net_name": (data.get("network") or {}).get("name") or "",
    }

def reverse_dns(ip):
    try:
        host = socket.gethostbyaddr(ip)[0]
        if ip in socket.gethostbyname_ex(host)[2]:
            return host.lower()
    except Exception:
        pass
    return ""

def internetdb(ip):
    if not USE_INTERNETDB:
        return {}
    try:
        return json.loads(fetch_text(f"https://internetdb.shodan.io/{ip}", timeout=8))
    except Exception:
        return {}

def abuseipdb(ip):
    if not ABUSEIPDB_KEY:
        return {}
    try:
        text = fetch_text(
            f"https://api.abuseipdb.com/api/v2/check?ipAddress={ip}&maxAgeInDays=90",
            timeout=10,
            headers={"Key": ABUSEIPDB_KEY, "Accept": "application/json", "User-Agent": "wifi-monitor/1.0"},
        )
        return json.loads(text).get("data", {})
    except Exception:
        return {}

def match_any(text, names):
    for name in names:
        if len(name) >= 6:
            if name in text:
                return True
        elif re.search(r"(?<!\w)" + re.escape(name) + r"(?!\w)", text):
            return True
    return False

def classify(text):
    for category in ("hosting", "isp", "company"):
        if match_any(text, CATEGORY_NAMES[category]):
            return category
    return None

def analyze(ip):
    futures = {
        "rdap": executor.submit(rdap, ip),
        "dns": executor.submit(reverse_dns, ip),
        "idb": executor.submit(internetdb, ip),
        "abuse": executor.submit(abuseipdb, ip),
    }
    deadline = time.time() + ANALYSIS_TIMEOUT
    results = {}
    for key, fut in futures.items():
        try:
            results[key] = fut.result(timeout=max(0.1, deadline - time.time()))
        except Exception:
            results[key] = "" if key == "dns" else {}

    rd = results["rdap"]
    host = results["dns"]
    idb = results["idb"]
    ab = results["abuse"]

    asn = rd.get("asn", "")
    cc = rd.get("cc", "")
    desc = " | ".join(p for p in (rd.get("asn_desc", ""), rd.get("net_name", "")) if p)

    if asn in TRUSTED_ASNS:
        category = TRUSTED_ASNS[asn][0]
    else:
        category = classify(" ".join([desc, host]).lower())

    score = 0
    reasons = []

    if category in ("isp", "company"):
        pass
    elif category == "hosting":
        if not ALLOW_HOSTING:
            score += 25
            reasons.append("hosting provider")
    else:
        score += 25
        reasons.append("owner not in any list")
        if not host:
            score += 5
            reasons.append("no confirmed reverse dns")

    if not desc and not asn:
        score += 10
        reasons.append("no whois data")

    if asn and asn in BAD_ASNS:
        score += 60
        reasons.append("ASN in bad list")

    if cc and cc in WATCH_COUNTRIES:
        score += 15
        reasons.append(f"watched country {cc}")

    if ip in tor_exits:
        score += 60
        reasons.append("tor exit node")

    hits = feed_hits(ip)
    if hits:
        weight = max(FEEDS[h][1] for h in hits) + 10 * (len(hits) - 1)
        score += weight
        reasons.append("listed in " + ", ".join(hits))

    tag_score = 0
    used_tags = []
    for tag in idb.get("tags") or []:
        weight = TAG_WEIGHTS.get(tag, 0)
        if tag == "tor" and ip in tor_exits:
            continue
        if weight:
            tag_score = max(tag_score, weight)
            used_tags.append(tag)
    if tag_score:
        score += tag_score
        reasons.append("tags: " + ", ".join(used_tags))

    vulns = idb.get("vulns") or []
    if len(vulns) >= 5:
        score += 5
        reasons.append(f"{len(vulns)} known vulns exposed")

    conf = ab.get("abuseConfidenceScore")
    if isinstance(conf, int) and conf >= 10:
        score += int(conf * 0.8)
        reasons.append(f"abuseipdb {conf}%")

    return {
        "score": min(100, score),
        "reasons": reasons,
        "label": CATEGORY_LABELS.get(category, "UNKNOWN"),
        "desc": desc,
        "asn": asn,
        "cc": cc,
        "host": host,
    }

def verdict_of(score):
    if score >= DANGER_AT:
        return "danger"
    if score >= SUSPICIOUS_AT:
        return "suspicious"
    return "ok"

def describe(ip, res):
    parts = [f"{ip} -> {res['desc'] or 'no whois data'}"]
    if res["asn"]:
        parts.append(f"AS{res['asn']} {res['cc']}".strip())
    if res["host"]:
        parts.append(res["host"])
    parts.append(f"score {res['score']}")
    if res["reasons"]:
        parts.append("; ".join(res["reasons"]))
    return " | ".join(parts)

def ensure_mikrotik_rules():
    global mikrotik_ready
    if mikrotik_ready:
        return
    out, _ = run_remote('/ip firewall filter print count-only where comment="monitor-blacklist"')
    if out.strip() in ("", "0"):
        run_remote('/ip firewall filter add chain=forward action=drop src-address-list=monitor-blacklist comment="monitor-blacklist" place-before=0')
        run_remote('/ip firewall filter add chain=forward action=drop dst-address-list=monitor-blacklist comment="monitor-blacklist" place-before=0')
    mikrotik_ready = True

def block_target(target):
    if profile == "mikrotik":
        ensure_mikrotik_rules()
        cmds = [f'/ip firewall address-list add list=monitor-blacklist address={target} comment="monitor"']
    else:
        cmds = []
        for chain, flag in (("FORWARD", "-s"), ("FORWARD", "-d"), ("INPUT", "-s"), ("OUTPUT", "-d")):
            cmds.append(f"{sudo}iptables -C {chain} {flag} {target} -j DROP 2>/dev/null || {sudo}iptables -I {chain} {flag} {target} -j DROP")
        cmds.append(f"{sudo}conntrack -D -s {target}")
        cmds.append(f"{sudo}conntrack -D -d {target}")
    for c in cmds:
        try:
            out, err = run_remote(c)
        except Exception as e:
            log(f"  {c} -> {e}", YELLOW)
            continue
        if err.strip() and "flow entries" not in err and "already have" not in err:
            log(f"  {c} -> {err.strip()}", YELLOW)

def unblock_target(target):
    if profile == "mikrotik":
        cmds = [f"/ip firewall address-list remove [find list=monitor-blacklist address={target}]"]
    else:
        cmds = [f"{sudo}iptables -D {chain} {flag} {target} -j DROP 2>/dev/null" for chain, flag in (("FORWARD", "-s"), ("FORWARD", "-d"), ("INPUT", "-s"), ("OUTPUT", "-d"))]
    for c in cmds:
        try:
            run_remote(c)
        except Exception as e:
            log(f"  {c} -> {e}", YELLOW)

def forget(value):
    net = ipaddress.ip_network(value, strict=False)
    for ip in list(checked):
        if ipaddress.ip_address(ip) in net:
            del checked[ip]
    for ip in list(pending):
        if ipaddress.ip_address(ip) in net:
            del pending[ip]

def overlaps_protected(value):
    net = ipaddress.ip_network(value, strict=False)
    return any(ipaddress.ip_address(p) in net for p in protected_ips)

def add_whitelist(value, note):
    blacklist.remove(value)
    whitelist.add(value, note)
    forget(value)

def add_blacklist(value, note):
    whitelist.remove(value)
    blacklist.add(value, note)
    block_target(value)
    forget(value)

def apply_blacklist():
    count = 0
    for net in list(blacklist.entries):
        block_target(net_text(net))
        count += 1
    log(f"Blacklist applied to the device: {count} entries.", RED if count else GREEN)

def auto_allowed():
    cutoff = time.time() - AUTO_BLOCK_WINDOW
    while auto_block_times and auto_block_times[0] < cutoff:
        auto_block_times.popleft()
    return len(auto_block_times) < AUTO_BLOCK_LIMIT

def decide_manual(ip, res, color):
    while True:
        ans = input(CLEAR + paint(f"[{now()}] Block {ip}? y = block + blacklist | n = allow + whitelist | s = decide later: ", color)).strip().lower()
        if ans in ("y", "n", "s"):
            break
        print("Invalid option. Please enter 'y', 'n' or 's'.")
    if ans == "y":
        add_blacklist(ip, f"manual {now()} score {res['score']}")
        log(f"[BLOCKED] {ip} blocked and added to the blacklist.", RED)
        checked[ip] = "blocked"
    elif ans == "n":
        add_whitelist(ip, f"manual {now()} score {res['score']}")
        log(f"[WHITELIST] {ip} added to the whitelist.", GREEN)
        checked[ip] = "whitelist"
    else:
        pending[ip] = res
        checked[ip] = "pending"
        log(f"[REVIEW] {ip} queued for later.", YELLOW)

def handle_ip(ip, future=None):
    global mode
    if ip in protected_ips:
        checked[ip] = "protected"
        return

    if whitelist.contains(ip):
        log(f"[WHITELIST] {ip} {whitelist.note_for(ip)}", GREEN)
        checked[ip] = "whitelist"
        return

    if blacklist.contains(ip):
        log(f"[BLACKLIST] {ip} {blacklist.note_for(ip)} -> blocking", RED)
        block_target(ip)
        checked[ip] = "blocked"
        return

    res = future.result() if future else analyze(ip)
    verdict = verdict_of(res["score"])
    log(f"{VERDICT_TAGS[verdict]} [{res['label']}] {describe(ip, res)}", VERDICT_COLORS[verdict])

    if verdict == "ok":
        checked[ip] = "ok"
        return

    if mode == "auto":
        if verdict == "danger" or AUTO_SUSPICIOUS_ACTION == "block":
            if auto_allowed():
                auto_block_times.append(time.time())
                add_blacklist(ip, f"auto {now()} score {res['score']}")
                log(f"[BLOCKED] {ip} blocked automatically and added to the blacklist.", RED)
                checked[ip] = "blocked"
                return
            mode = "manual"
            log("Automatic block limit reached, switching to manual mode.", RED)
        elif AUTO_SUSPICIOUS_ACTION == "allow":
            checked[ip] = "allowed"
            log(f"[AUTO-ALLOW] {ip} allowed for this session (not added to the whitelist).", YELLOW)
            return
        else:
            pending[ip] = res
            checked[ip] = "pending"
            log(f"[REVIEW] {ip} queued, monitoring continues. Press Ctrl+C and choose option 8 to review it.", YELLOW)
            return

    decide_manual(ip, res, VERDICT_COLORS[verdict])

def show_list(name, store):
    print(paint(f"--- {name} ({len(store.entries)}) ---", CYAN))
    for net, note in store.entries.items():
        print(f"  {net_text(net)}  {note}")

def read_target(prompt):
    value = input(prompt).strip()
    if not value:
        return None
    try:
        ipaddress.ip_network(value, strict=False)
    except ValueError:
        print(paint("Invalid IP or network.", RED))
        return None
    return value

def review_pending():
    if not pending:
        print("No pending IPs.")
        return
    for ip in list(pending):
        res = pending.get(ip)
        if res is None:
            continue
        verdict = verdict_of(res["score"])
        print(paint(f"{VERDICT_TAGS[verdict]} [{res['label']}] {describe(ip, res)}", VERDICT_COLORS[verdict]))
        while True:
            ans = input("b = block + blacklist | w = allow + whitelist | s = skip | q = stop: ").strip().lower()
            if ans in ("b", "w", "s", "q"):
                break
        if ans == "q":
            return
        if ans == "b":
            add_blacklist(ip, f"review {now()} score {res['score']}")
            checked[ip] = "blocked"
            log(f"[BLOCKED] {ip} blocked and added to the blacklist.", RED)
        elif ans == "w":
            add_whitelist(ip, f"review {now()} score {res['score']}")
            checked[ip] = "whitelist"
            log(f"[WHITELIST] {ip} added to the whitelist.", GREEN)

def menu():
    global mode
    print(CLEAR, end="")
    while True:
        print(paint(f"\n=== MENU (mode: {mode}) ===", CYAN))
        print("1) Switch mode manual/automatic")
        print("2) Show whitelist")
        print("3) Show blacklist")
        print("4) Add IP or network to whitelist")
        print("5) Add IP or network to blacklist (and block)")
        print("6) Remove from whitelist")
        print("7) Remove from blacklist (and unblock)")
        print(f"8) Review pending IPs ({len(pending)})")
        print("9) Refresh threat feeds now")
        print("0) Resume monitoring")
        print("q) Quit")
        try:
            choice = input("> ").strip().lower()
        except KeyboardInterrupt:
            return True
        try:
            if choice == "1":
                mode = "auto" if mode == "manual" else "manual"
                log(f"Mode changed to {mode}.", CYAN)
            elif choice == "2":
                show_list("WHITELIST", whitelist)
            elif choice == "3":
                show_list("BLACKLIST", blacklist)
            elif choice == "4":
                value = read_target("IP or network to whitelist: ")
                if value:
                    note = input("Note (optional): ").strip()
                    add_whitelist(value, note)
                    print(paint("Added to whitelist.", GREEN))
            elif choice == "5":
                value = read_target("IP or network to blacklist: ")
                if value:
                    note = input("Note (optional): ").strip()
                    add_blacklist(value, note)
                    print(paint("Added to blacklist and blocked.", RED))
            elif choice == "6":
                value = read_target("IP or network to remove from whitelist: ")
                if value:
                    if whitelist.remove(value):
                        print(paint("Removed from whitelist.", GREEN))
                    else:
                        print(paint("Not found in whitelist.", YELLOW))
            elif choice == "7":
                value = read_target("IP or network to remove from blacklist: ")
                if value:
                    if blacklist.remove(value):
                        unblock_target(value)
                        print(paint("Removed from blacklist and unblocked.", GREEN))
                    else:
                        print(paint("Not found in blacklist.", YELLOW))
            elif choice == "8":
                review_pending()
            elif choice == "9":
                refresh_intel()
                print(paint("Threat feeds refreshed.", GREEN))
            elif choice == "0":
                return
            elif choice == "q":
                sys.exit(0)
            else:
                print(paint("Invalid option.", RED))
        except Exception as e:
            print(paint(f"Error: {e}", RED))

def main():
    global profile
    print("Detecting remote profile...")
    profile = detect_profile()
    log(f"Remote profile detected: {profile}", GREEN)
    
    if APPLY_BLACKLIST_ON_START:
        apply_blacklist()
        
    refresh_intel()
    
    log("Starting monitoring tool loop...", GREEN)
    try:
        while True:
            if time.time() - intel_last > INTEL_REFRESH:
                refresh_intel()
            ips = get_remote_ips()
            if ips is None:
                log("Could not retrieve connections. Retrying...", YELLOW)
                time.sleep(2)
                continue
            active_ips = [ip for ip in ips if ip not in checked]
            if active_ips:
                futures = {ip: analysis_pool.submit(analyze, ip) for ip in active_ips}
                for ip in active_ips:
                    status_line(len(ips))
                    try:
                        handle_ip(ip, futures[ip])
                    except Exception as e:
                        log(f"Error handling {ip}: {e}", RED)
            else:
                status_line(len(ips))
            time.sleep(INTERVAL)
    except KeyboardInterrupt:
        menu()
        main()

if __name__ == "__main__":
    main()