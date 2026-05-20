#!/bin/bash
# Usage: GITHUB_TOKEN=ghp_xxxx bash -c "$(curl -fsSL -H "Authorization: Bearer $GITHUB_TOKEN" \
#   https://raw.githubusercontent.com/bensa89/wfmMarketIntelligence/main/install/wfmintel-lxc.sh)"
set -euo pipefail

RAW_BASE="https://raw.githubusercontent.com/bensa89/wfmMarketIntelligence/main"
CURL_ARGS=(-fsSL)
if [[ -n "${GITHUB_TOKEN:-}" ]]; then
    CURL_ARGS+=(-H "Authorization: Bearer ${GITHUB_TOKEN}")
fi

msg() { echo -e "\n\033[1;34m>>> $*\033[0m"; }

# --- Configuration ---
CT_ID=${1:-200}
CT_HOSTNAME="wfmintel"
CT_CORES=2
CT_RAM=2048
CT_DISK=20
CT_STORAGE="local-lvm"
CT_BRIDGE="vmbr0"
TEMPLATE="debian-12-standard_12.12-1_amd64.tar.zst"
TEMPLATE_STORAGE="local"

echo "========================================================"
echo "  WFM Market Intelligence — Proxmox LXC Setup"
echo "  LXC ID: ${CT_ID}  |  Hostname: ${CT_HOSTNAME}"
echo "========================================================"

read -rp "LXC ID [${CT_ID}]: " CT_ID_IN
CT_ID="${CT_ID_IN:-$CT_ID}"
read -rp "IP-Adresse mit CIDR (z.B. 192.168.1.50/24): " CT_IP
read -rp "Gateway (z.B. 192.168.1.1): " CT_GW
read -rp "Storage pool [${CT_STORAGE}]: " CT_STORAGE_IN
CT_STORAGE="${CT_STORAGE_IN:-$CT_STORAGE}"

msg "Checking for Debian 12 template"
if ! pveam list "$TEMPLATE_STORAGE" 2>/dev/null | grep -q "$TEMPLATE"; then
    msg "Downloading Debian 12 template (this may take a moment)..."
    pveam download "$TEMPLATE_STORAGE" "$TEMPLATE"
fi
echo "    ✓ Template ready"

msg "Creating LXC ${CT_ID}"
pct create "$CT_ID" "${TEMPLATE_STORAGE}:vztmpl/${TEMPLATE}" \
    --hostname "$CT_HOSTNAME" \
    --cores "$CT_CORES" \
    --memory "$CT_RAM" \
    --rootfs "${CT_STORAGE}:${CT_DISK}" \
    --net0 "name=eth0,bridge=${CT_BRIDGE},ip=${CT_IP},gw=${CT_GW}" \
    --unprivileged 1 \
    --features "nesting=1" \
    --onboot 1 \
    --nameserver 8.8.8.8

msg "Starting LXC"
pct start "$CT_ID"

msg "Waiting for LXC to boot (10s)"
sleep 10

msg "Downloading install script from GitHub"
INSTALL_TMP=$(mktemp)
curl "${CURL_ARGS[@]}" "${RAW_BASE}/install/wfmintel-install.sh" -o "$INSTALL_TMP"
pct push "$CT_ID" "$INSTALL_TMP" /root/wfmintel-install.sh
rm "$INSTALL_TMP"
pct exec "$CT_ID" -- chmod +x /root/wfmintel-install.sh

msg "Running install script inside LXC"
pct exec "$CT_ID" -- bash /root/wfmintel-install.sh

echo ""
echo "========================================================"
LXC_IP="${CT_IP%/*}"
echo "  LXC ${CT_ID} (${CT_HOSTNAME}) setup complete."
echo "  IP: ${LXC_IP}"
echo "  Run 'pct enter ${CT_ID}' to open a shell."
echo "========================================================"
