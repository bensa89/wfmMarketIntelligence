#!/usr/bin/env bash
# Usage: bash -c "$(curl -fsSL https://raw.githubusercontent.com/bensa89/wfmMarketIntelligence/main/install/wfmintel-lxc.sh)"
set -euo pipefail

INSTALL_SCRIPT_URL="https://raw.githubusercontent.com/bensa89/wfmMarketIntelligence/main/install/wfmintel-install.sh"

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; BLUE='\033[0;34m'; NC='\033[0m'
info()   { echo -e "${GREEN}[INFO]${NC} $*"; }
warn()   { echo -e "${YELLOW}[WARN]${NC} $*"; }
error()  { echo -e "${RED}[ERROR]${NC} $*"; exit 1; }
prompt() { echo -e "${BLUE}[?]${NC} $*"; }

command -v pct &>/dev/null || error "pct nicht gefunden. Dieses Script muss auf dem Proxmox-Host ausgeführt werden."
[[ $EUID -ne 0 ]] && error "Dieses Script muss als root ausgeführt werden."

echo ""
echo -e "${GREEN}╔══════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║   WFM Market Intelligence — LXC Setup        ║${NC}"
echo -e "${GREEN}╚══════════════════════════════════════════════╝${NC}"
echo ""

NEXT_ID=$(pvesh get /cluster/nextid 2>/dev/null || echo "200")
prompt "Container ID [${NEXT_ID}]:"
read -r CT_ID
CT_ID=${CT_ID:-$NEXT_ID}

prompt "Hostname [wfmintel]:"
read -r CT_HOSTNAME
CT_HOSTNAME=${CT_HOSTNAME:-"wfmintel"}

DEFAULT_STORAGE=$(pvesm status --content rootdir 2>/dev/null | tail -n +2 | awk 'NR==1{print $1}' || echo "local-lvm")
prompt "Storage [${DEFAULT_STORAGE}]:"
read -r CT_STORAGE
CT_STORAGE=${CT_STORAGE:-$DEFAULT_STORAGE}

CT_DISK=20
CT_MEMORY=2048

prompt "Netzwerk-Bridge [vmbr0]:"
read -r CT_BRIDGE
CT_BRIDGE=${CT_BRIDGE:-"vmbr0"}

echo ""
info "IP-Konfiguration: Statische IP oder DHCP?"
info "  (DHCP funktioniert nur wenn die Bridge einen DHCP-Server hat)"
prompt "Statische IP (z.B. 192.168.1.100/24) oder 'dhcp' [dhcp]:"
read -r CT_IP_INPUT
CT_IP_INPUT=${CT_IP_INPUT:-"dhcp"}

if [[ "$CT_IP_INPUT" == "dhcp" ]]; then
    NET_CONFIG="name=eth0,bridge=${CT_BRIDGE},ip=dhcp"
    NAMESERVER_ARG="--nameserver 8.8.8.8"
else
    prompt "Gateway (z.B. 192.168.1.1):"
    read -r CT_GW
    NET_CONFIG="name=eth0,bridge=${CT_BRIDGE},ip=${CT_IP_INPUT},gw=${CT_GW}"
    NAMESERVER_ARG="--nameserver 8.8.8.8"
fi

echo ""
info "Konfiguration:"
info "  Container ID : $CT_ID"
info "  Hostname     : $CT_HOSTNAME"
info "  Storage      : $CT_STORAGE  |  Disk: ${CT_DISK}GB  |  RAM: ${CT_MEMORY}MB"
info "  Bridge       : $CT_BRIDGE"
info "  Netzwerk     : $CT_IP_INPUT"
echo ""

# ── Debian 12 Template ────────────────────────────────────────────────────────
info "Suche Ubuntu 22.04 Template..."
TEMPLATE_FILE=$(pveam list local 2>/dev/null | awk '{print $1}' | grep "ubuntu-22.04-standard" | head -1 || true)

if [[ -z "$TEMPLATE_FILE" ]]; then
    info "Template nicht gefunden — lade herunter..."
    pveam update >/dev/null
    TEMPLATE_NAME=$(pveam available --section system 2>/dev/null | grep "ubuntu-22.04-standard" | tail -1 | awk '{print $2}')
    [[ -z "$TEMPLATE_NAME" ]] && error "Ubuntu 22.04 Template nicht im PVE-Repository gefunden."
    pveam download local "$TEMPLATE_NAME"
    TEMPLATE="local:vztmpl/$TEMPLATE_NAME"
else
    TEMPLATE="$TEMPLATE_FILE"
fi
info "Verwende Template: $TEMPLATE"

# ── LXC erstellen ─────────────────────────────────────────────────────────────
info "Erstelle LXC Container $CT_ID..."
pct create "$CT_ID" "$TEMPLATE" \
    --hostname "$CT_HOSTNAME" \
    --storage "$CT_STORAGE" \
    --rootfs "${CT_STORAGE}:${CT_DISK}" \
    --memory "$CT_MEMORY" \
    --cores 2 \
    --net0 "$NET_CONFIG" \
    --unprivileged 1 \
    --features "nesting=1,keyctl=1" \
    --ostype ubuntu \
    --onboot 1 \
    $NAMESERVER_ARG

info "Starte Container..."
pct start "$CT_ID"

# ── Warten bis Container + Netzwerk bereit ────────────────────────────────────
info "Warte auf Container-Start..."
RETRIES=20
until pct exec "$CT_ID" -- test -f /etc/os-release 2>/dev/null; do
    ((RETRIES--)) || error "Container hat nicht rechtzeitig gestartet."
    sleep 3
done

info "Warte auf Netzwerk (eth0 mit IP)..."
RETRIES=30
until pct exec "$CT_ID" -- ip addr show eth0 2>/dev/null | grep -q "inet "; do
    ((RETRIES--)) || error "Kein Netzwerk nach 90s. Bridge/IP-Konfiguration prüfen."
    sleep 3
done
info "Netzwerk bereit."

# ── Install-Script im Container ausführen ─────────────────────────────────────
info "Führe WFM Install-Script im Container aus..."
echo ""
pct exec "$CT_ID" -- bash -c \
    "apt-get update -qq && apt-get install -y -qq curl && bash <(curl -fsSL ${INSTALL_SCRIPT_URL})"

# ── Abschluss ─────────────────────────────────────────────────────────────────
echo ""
CT_IP=$(pct exec "$CT_ID" -- hostname -I 2>/dev/null | awk '{print $1}' || echo "unbekannt")
echo -e "${GREEN}════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}  LXC erfolgreich erstellt und provisioniert!${NC}"
echo -e "${GREEN}════════════════════════════════════════════════════════${NC}"
echo ""
echo "  Container ID : $CT_ID"
echo "  IP-Adresse   : $CT_IP"
echo ""
echo "Nächste Schritte:"
echo "  1. GitHub Actions Deploy auslösen:"
echo "     GitHub → Actions → Deploy → Run workflow"
echo ""
echo "  2. Nginx Proxy Manager konfigurieren:"
echo "     Frontend : http://${CT_IP}:80"
echo "     API      : http://${CT_IP}:8000"
echo -e "${GREEN}════════════════════════════════════════════════════════${NC}"
