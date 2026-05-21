#!/bin/bash
set -euo pipefail

APP_DIR="/opt/wfmintel"
APP_USER="wfm"
RUNNER_DIR="${APP_DIR}/actions-runner"
REPO_SSH="git@github.com:bensa89/wfmMarketIntelligence.git"
REPO_HTTPS="https://github.com/bensa89/wfmMarketIntelligence"

msg() { echo -e "\n\033[1;34m>>> $*\033[0m"; }
ok()  { echo -e "\033[1;32m    ✓ $*\033[0m"; }

msg "Configuring DNS"
printf 'nameserver 8.8.8.8\nnameserver 1.1.1.1\n' > /etc/resolv.conf
ok "DNS set to 8.8.8.8 / 1.1.1.1"

msg "Updating system packages"
apt-get update -qq && apt-get upgrade -y -qq

msg "Installing prerequisites"
apt-get install -y -qq curl ca-certificates git openssh-client

msg "Installing Docker Engine"
install -m 0755 -d /etc/apt/keyrings
# shellcheck source=/dev/null
. /etc/os-release
curl -fsSL "https://download.docker.com/linux/${ID}/gpg" -o /etc/apt/keyrings/docker.asc
chmod a+r /etc/apt/keyrings/docker.asc
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] \
  https://download.docker.com/linux/${ID} ${VERSION_CODENAME} stable" \
  | tee /etc/apt/sources.list.d/docker.list > /dev/null
apt-get update -qq
apt-get install -y -qq docker-ce docker-ce-cli containerd.io docker-compose-plugin
DOCKER_VERSION=$(docker --version | awk '{print $3}' | tr -d ',')
ok "Docker ${DOCKER_VERSION}"

msg "Creating app user '${APP_USER}'"
useradd -m -s /bin/bash "$APP_USER" || true
usermod -aG docker "$APP_USER"
ok "User ${APP_USER} created and added to docker group"

msg "Generating SSH deploy key"
SSH_DIR="/home/${APP_USER}/.ssh"
mkdir -p "$SSH_DIR"
chown "${APP_USER}:${APP_USER}" "$SSH_DIR"
su -s /bin/bash -c "ssh-keygen -t ed25519 -f '${SSH_DIR}/deploy_key' -N '' -C 'wfmintel-deploy' -q" "$APP_USER"
cat > "${SSH_DIR}/config" << 'EOF'
Host github.com
    IdentityFile ~/.ssh/deploy_key
    StrictHostKeyChecking accept-new
EOF
chown -R "${APP_USER}:${APP_USER}" "$SSH_DIR"
chmod 700 "$SSH_DIR"
chmod 600 "${SSH_DIR}/deploy_key" "${SSH_DIR}/config"

echo ""
echo "========================================================"
echo "  Add this deploy key to GitHub before continuing:"
echo "  ${REPO_HTTPS}/settings/keys/new"
echo "  Title: wfmintel-proxmox | Allow write access: NO"
echo "========================================================"
cat "${SSH_DIR}/deploy_key.pub"
echo "========================================================"
read -rp "Press ENTER once the deploy key has been added..."

msg "Cloning repository"
mkdir -p "$APP_DIR"
chown "${APP_USER}:${APP_USER}" "$APP_DIR"
su -s /bin/bash -c "git clone '$REPO_SSH' '$APP_DIR'" "$APP_USER"
chown -R "${APP_USER}:${APP_USER}" "$APP_DIR"
ok "Repository cloned to ${APP_DIR}"

msg "Creating placeholder .env"
cat > "${APP_DIR}/.env" << 'EOF'
# Written by GitHub Actions on each deploy. Do not edit manually.
EOF
chown "${APP_USER}:${APP_USER}" "${APP_DIR}/.env"

msg "Downloading GitHub Actions runner"
mkdir -p "$RUNNER_DIR"
RUNNER_VERSION=$(curl -s https://api.github.com/repos/actions/runner/releases/latest \
  | grep '"tag_name"' | sed 's/.*"v\([^"]*\)".*/\1/')
curl -fsSL \
  "https://github.com/actions/runner/releases/download/v${RUNNER_VERSION}/actions-runner-linux-x64-${RUNNER_VERSION}.tar.gz" \
  | tar -xz -C "$RUNNER_DIR"
chown -R "${APP_USER}:${APP_USER}" "$RUNNER_DIR"
ok "Runner v${RUNNER_VERSION} downloaded"

echo ""
echo "========================================================"
echo "  Get your runner token from GitHub:"
echo "  ${REPO_HTTPS}/settings/actions/runners/new?runnerOs=linux"
echo "========================================================"
read -rp "Runner registration token: " RUNNER_TOKEN

msg "Configuring GitHub Actions runner"
su -s /bin/bash -c \
  "cd '${RUNNER_DIR}' && ./config.sh \
    --url '${REPO_HTTPS}' \
    --token '${RUNNER_TOKEN}' \
    --name 'proxmox-lxc' \
    --labels 'self-hosted,linux' \
    --unattended" "$APP_USER"

msg "Installing runner as systemd service"
cd "$RUNNER_DIR"
./svc.sh install "$APP_USER"
./svc.sh start

msg "Checking for seed database"
SEED_FILE="${APP_DIR}/install/seed.dump"
if [[ -f "$SEED_FILE" ]]; then
    msg "Seed file found — restoring initial data"

    # Minimal .env to start the db container only
    cat > "${APP_DIR}/.env" << 'EOF'
POSTGRES_USER=wfm
POSTGRES_PASSWORD=wfm
POSTGRES_DB=wfmintel
DATABASE_URL=postgresql://wfm:wfm@db:5432/wfmintel
EOF
    chown "${APP_USER}:${APP_USER}" "${APP_DIR}/.env"

    cd "$APP_DIR"
    su -s /bin/bash -c "cd '${APP_DIR}' && docker compose up -d db" "$APP_USER"

    echo "    Waiting for database to be ready..."
    for _ in $(seq 1 30); do
        if su -s /bin/bash -c "cd '${APP_DIR}' && docker compose exec -T db pg_isready -U wfm -q" "$APP_USER" 2>/dev/null; then
            break
        fi
        sleep 2
    done

    su -s /bin/bash -c "cd '${APP_DIR}' && docker compose cp '${SEED_FILE}' db:/tmp/seed.dump" "$APP_USER"
    su -s /bin/bash -c "cd '${APP_DIR}' && docker compose exec -T db \
        pg_restore -U wfm -d wfmintel --no-owner --clean --if-exists /tmp/seed.dump" "$APP_USER"

    su -s /bin/bash -c "cd '${APP_DIR}' && docker compose down" "$APP_USER"
    ok "Seed data restored — .env will be overwritten on first GitHub Actions deploy"
else
    ok "No seed file found — stack will start with an empty database"
fi

LXC_IP=$(hostname -I | awk '{print $1}')
echo ""
echo "========================================================"
echo "  Installation complete!"
echo "  Frontend : http://${LXC_IP}:80"
echo "  API      : http://${LXC_IP}:8000"
echo ""
echo "  Trigger first deploy from GitHub Actions to start the"
echo "  full stack and set real credentials via .env."
echo "========================================================"
