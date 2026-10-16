#!/usr/bin/env bash
# vm-db (192.168.56.20): PostgreSQL, pasta de fotos exportada por NFS,
# backups diários e firewall (5432 e NFS só para as apps).
#
# Uso: sudo ETERMORY_DB_SENHA='senha-forte' ~/etermory/scripts/provisionar/db.sh
#   (sem a variável, o script pergunta a senha)
set -euo pipefail
RAIZ="$(cd "$(dirname "$(readlink -f "$0")")/../.." && pwd)"
# shellcheck source=SCRIPTDIR/../lib.sh
source "${RAIZ}/scripts/lib.sh"
ARQUIVO_LOG="/var/log/etermory-provisionamento.log"
exigir_root
[[ "$(hostname)" == "vm-db" ]] || falhar 1 "Rode o comum.sh vm-db antes."

APPS=("192.168.56.11" "192.168.56.12")

export DEBIAN_FRONTEND=noninteractive
apt-get install -y -q postgresql nfs-kernel-server
VERSAO_PG=$(find /etc/postgresql -mindepth 1 -maxdepth 1 -printf '%f\n' | sort -V | tail -1)
CONF="/etc/postgresql/${VERSAO_PG}/main"
log INFO "PostgreSQL ${VERSAO_PG} instalado"

# ---------- Usuário e banco ----------
SENHA="${ETERMORY_DB_SENHA:-}"
if [[ -z "$SENHA" ]]; then
    read -r -s -p "Senha do usuário etermory no PostgreSQL: " SENHA
    echo
fi
[[ ${#SENHA} -ge 12 ]] || falhar 1 "Use uma senha com pelo menos 12 caracteres."

runuser -u postgres -- psql --quiet -v ON_ERROR_STOP=1 -v senha="$SENHA" << 'SQL'
SELECT 'CREATE ROLE etermory LOGIN'
WHERE NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'etermory') \gexec
ALTER ROLE etermory PASSWORD :'senha';
SQL
if ! runuser -u postgres -- psql -tAc "SELECT 1 FROM pg_database WHERE datname='etermory'" | grep -q 1; then
    runuser -u postgres -- createdb --owner=etermory etermory
fi
log INFO "Banco etermory e usuário etermory prontos"

# ---------- Acesso pela rede: só as apps, com senha (scram-sha-256) ----------
cat > "${CONF}/conf.d/etermory.conf" << 'EOF'
listen_addresses = 'localhost,192.168.56.20'
password_encryption = scram-sha-256
log_connections = on
log_disconnections = on
EOF
if ! grep -q '# etermory' "${CONF}/pg_hba.conf"; then
    {
        echo "# etermory: só as VMs de aplicação"
        for ip in "${APPS[@]}"; do
            echo "host    etermory    etermory    ${ip}/32    scram-sha-256"
        done
    } >> "${CONF}/pg_hba.conf"
fi
systemctl restart postgresql
log INFO "PostgreSQL escutando em 192.168.56.20:5432 só para ${APPS[*]}"

# ---------- NFS: pasta de fotos compartilhada ----------
install -d -m 770 -o etermory -g etermory /srv/etermory-uploads
{
    printf '/srv/etermory-uploads'
    for ip in "${APPS[@]}"; do
        printf ' %s(rw,sync,no_subtree_check,root_squash)' "$ip"
    done
    printf '\n'
} > /etc/exports.d/etermory.exports
exportfs -ra
systemctl enable --now nfs-server
log INFO "NFS exportando /srv/etermory-uploads para as apps"

# ---------- Backups ----------
install -d -m 700 /srv/backups /srv/backups/etermory
install -d -m 750 /opt/etermory
cp -r "${RAIZ}/scripts" /opt/etermory/
chmod 750 /opt/etermory/scripts/*.sh
ln -sf /opt/etermory/scripts/backup.sh /usr/local/sbin/etermory-backup
ln -sf /opt/etermory/scripts/restore.sh /usr/local/sbin/etermory-restore
[[ -f /root/.ssh/id_backup ]] || ssh-keygen -q -t ed25519 -N "" -f /root/.ssh/id_backup -C "backup@vm-db"
install -m 644 "${RAIZ}/deploy/systemd/etermory-backup.service" /etc/systemd/system/
install -m 644 "${RAIZ}/deploy/systemd/etermory-backup.timer" /etc/systemd/system/
systemctl daemon-reload
systemctl enable --now etermory-backup.timer
log INFO "Backup diário às 02:00 (systemctl list-timers etermory-backup.timer)"

# ---------- Firewall ----------
for ip in "${APPS[@]}"; do
    ufw allow from "$ip" to any port 5432 proto tcp comment 'PostgreSQL so das apps'
    ufw allow from "$ip" to any port 2049 proto tcp comment 'NFS so das apps'
done
log INFO "ufw: 5432 e 2049 liberadas só para as apps"

echo
echo "Chave pública de backup (autorize no deploy da vm-proxy):"
cat /root/.ssh/id_backup.pub
log INFO "== vm-db concluída =="
