#!/usr/bin/env bash
# vm-proxy (192.168.56.10): Nginx com failover, HTTPS autoassinado,
# repositório Git de produção (bare + hook), destino da cópia dos backups e
# healthcheck a cada minuto.
#
# Uso: sudo ~/etermory/scripts/provisionar/proxy.sh   (depois do comum.sh)
set -euo pipefail
RAIZ="$(cd "$(dirname "$(readlink -f "$0")")/../.." && pwd)"
# shellcheck source=SCRIPTDIR/../lib.sh
source "${RAIZ}/scripts/lib.sh"
ARQUIVO_LOG="/var/log/etermory-provisionamento.log"
exigir_root
[[ "$(hostname)" == "vm-proxy" ]] || falhar 1 "Rode o comum.sh vm-proxy antes."

export DEBIAN_FRONTEND=noninteractive
apt-get install -y -q nginx
log INFO "Nginx instalado: $(nginx -v 2>&1)"

# ---------- Scripts da Etermory nesta VM ----------
install -d -o deploy -g etermory-dev -m 750 /opt/etermory
cp -r "${RAIZ}/scripts" "${RAIZ}/deploy" /opt/etermory/
chown -R deploy:etermory-dev /opt/etermory
chmod 750 /opt/etermory/scripts/*.sh
ln -sf /opt/etermory/scripts/deploy.sh /usr/local/bin/etermory-deploy
ln -sf /opt/etermory/scripts/healthcheck.sh /usr/local/bin/etermory-healthcheck

# ---------- HTTPS (certificado autoassinado, válido por 1 ano) ----------
install -d -m 700 /etc/ssl/etermory
if [[ ! -f /etc/ssl/etermory/etermory.crt ]]; then
    openssl req -x509 -nodes -newkey rsa:2048 -days 365 \
        -subj "/CN=vm-proxy" \
        -addext "subjectAltName=IP:192.168.56.10,DNS:vm-proxy" \
        -keyout /etc/ssl/etermory/etermory.key -out /etc/ssl/etermory/etermory.crt
    chmod 600 /etc/ssl/etermory/etermory.key
    log INFO "Certificado autoassinado criado"
fi

# ---------- Nginx ----------
install -m 644 "${RAIZ}/deploy/nginx/etermory-proxy.conf" /etc/nginx/snippets/etermory-proxy.conf
install -m 644 "${RAIZ}/deploy/nginx/etermory.conf" /etc/nginx/sites-available/etermory
ln -sf ../sites-available/etermory /etc/nginx/sites-enabled/etermory
rm -f /etc/nginx/sites-enabled/default
nginx -t
systemctl enable --now nginx
systemctl reload nginx
log INFO "Nginx configurado com upstream app1/app2"

# ---------- Repositório Git de produção ----------
install -d -o deploy -g deploy -m 755 /srv/git
if [[ ! -d /srv/git/etermory.git ]]; then
    runuser -u deploy -- git init --quiet --bare --initial-branch=main /srv/git/etermory.git
fi
install -o deploy -g deploy -m 750 "${RAIZ}/deploy/git/post-receive" \
    /srv/git/etermory.git/hooks/post-receive
log INFO "Repositório bare em /srv/git/etermory.git com hook post-receive"

# ---------- Destino da cópia dos backups ----------
install -d -o deploy -g deploy -m 700 /srv/backups-remotos /srv/backups-remotos/etermory

# ---------- Healthcheck a cada minuto ----------
install -m 644 "${RAIZ}/deploy/systemd/etermory-healthcheck.service" /etc/systemd/system/
install -m 644 "${RAIZ}/deploy/systemd/etermory-healthcheck.timer" /etc/systemd/system/
systemctl daemon-reload
systemctl enable --now etermory-healthcheck.timer

# ---------- Firewall ----------
ufw allow 80/tcp comment 'HTTP (redireciona para HTTPS)'
ufw allow 443/tcp comment 'HTTPS'
log INFO "ufw: 80 e 443 liberadas"

cat << 'EOF'

Próximos passos na vm-proxy:
  1. Autorizar a chave do deploy de cada app (para o git fetch):
       sudo -u deploy tee -a /home/deploy/.ssh/authorized_keys < chave_deploy_app1.pub
  2. Autorizar a chave de backup da vm-db (root@vm-db) no mesmo arquivo.
  3. Copiar a chave do deploy DESTA VM para o deploy das apps:
       sudo -u deploy ssh-copy-id deploy@vm-app1   (e vm-app2)
  4. No seu computador: git remote add producao deploy@192.168.56.10:/srv/git/etermory.git
                        git push producao main
EOF
log INFO "== vm-proxy concluída =="
