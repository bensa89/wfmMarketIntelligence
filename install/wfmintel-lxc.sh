#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

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

read -rp "LXC IP with CIDR (e.g. 192.168.1.50/24): " CT_IP
read -rp "Default gateway (e.g. 192.168.1.1):        " CT_GW
read -rp "Storage pool [${CT_STORAGE}]:               " CT_STORAGE_IN
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
    --onboot 1

msg "Starting LXC"
pct start "$CT_ID"

msg "Waiting for LXC to boot (10s)"
sleep 10

msg "Copying install script into LXC"
pct push "$CT_ID" "${SCRIPT_DIR}/wfmintel-install.sh" /root/wfmintel-install.sh
pct exec "$CT_ID" -- chmod +x /root/wfmintel-install.sh

msg "Running install script inside LXC"
pct exec "$CT_ID" -- bash /root/wfmintel-install.sh

echo ""
echo "========================================================"
echo "  LXC ${CT_ID} (${CT_HOSTNAME}) setup complete."
echo "  IP: ${CT_IP%/*}"
echo "  Run 'pct enter ${CT_ID}' to open a shell."
echo "========================================================"
