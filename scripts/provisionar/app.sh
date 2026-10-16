#!/usr/bin/env bash
# vm-app1 / vm-app2: Python, código em /srv/etermory, venv, .env, pasta de
# fotos por NFS, serviço systemd e firewall (porta 8000 só para o proxy).
#
# Uso: sudo ~/etermory/scripts/provisionar/app.sh [URL_DO_REPOSITORIO]
#   URL padrão: deploy@vm-proxy:/srv/git/etermory.git (precisa da chave do
#   deploy desta VM autorizada na vm-proxy e de um primeiro "git push producao").
set -euo pipefail
RAIZ="$(cd "$(dirname "$(readlink -f "$0")")/../.." && pwd)"
# shellcheck source=SCRIPTDIR/../lib.sh
source "${RAIZ}/scripts/lib.sh"
ARQUIVO_LOG="/var/log/etermory-provisionamento.log"
exigir_root

NOME="$(hostname)"
[[ "$NOME" == "vm-app1" || "$NOME" == "vm-app2" ]] || falhar 1 "Rode o comum.sh vm-app1|vm-app2 antes."
INSTANCIA="${NOME#vm-}"
REPOSITORIO="${1:-deploy@vm-proxy:/srv/git/etermory.git}"
PASTA="/srv/etermory"

export DEBIAN_FRONTEND=noninteractive
apt-get install -y -q python3 python3-venv python3-pip nfs-common
log INFO "Python: $(python3 --version)"

# ---------- Pasta de fotos compartilhada (NFS da vm-db) ----------
install -d -m 770 -o etermory -g etermory /srv/etermory-uploads
if ! grep -q '/srv/etermory-uploads' /etc/fstab; then
    echo 'vm-db:/srv/etermory-uploads /srv/etermory-uploads nfs4 defaults,_netdev,noatime 0 0' >> /etc/fstab
fi
systemctl daemon-reload
if mount /srv/etermory-uploads 2> /dev/null || findmnt /srv/etermory-uploads > /dev/null; then
    log INFO "NFS montado: $(findmnt -no SOURCE /srv/etermory-uploads)"
else
    log AVISO "NFS ainda não montou (a vm-db já foi provisionada?). Depois: sudo mount -a"
fi

# ---------- Código ----------
install -d -o deploy -g etermory -m 750 "$PASTA"
if [[ ! -d "${PASTA}/.git" ]]; then
    runuser -u deploy -- env GIT_SSH_COMMAND="ssh -o StrictHostKeyChecking=accept-new" \
        git clone --quiet "$REPOSITORIO" "$PASTA"
fi
chmod 750 "${PASTA}"/scripts/*.sh
log INFO "Código em ${PASTA} ($(runuser -u deploy -- git -C "$PASTA" log -1 --format='%h %s'))"

# ---------- Dependências Python (venv) ----------
[[ -d "${PASTA}/.venv" ]] || runuser -u deploy -- python3 -m venv "${PASTA}/.venv"
runuser -u deploy -- "${PASTA}/.venv/bin/pip" install --quiet --upgrade pip
runuser -u deploy -- "${PASTA}/.venv/bin/pip" install --quiet -r "${PASTA}/requirements.txt"
log INFO "Dependências instaladas no venv"

# ---------- .env ----------
if [[ ! -f "${PASTA}/.env" ]]; then
    install -o deploy -g etermory -m 640 "${RAIZ}/deploy/app.env.exemplo" "${PASTA}/.env"
    sed -i "s/^INSTANCIA=.*/INSTANCIA=${INSTANCIA}/" "${PASTA}/.env"
    log AVISO "Edite ${PASTA}/.env (SECRET_KEY igual nas duas apps e senha do banco)"
fi

# ---------- sudo restrito para o deploy reiniciar só o serviço ----------
cat > /etc/sudoers.d/etermory-deploy << 'EOF'
deploy ALL=(root) NOPASSWD: /usr/bin/systemctl restart etermory, /usr/bin/systemctl reload etermory, /usr/bin/systemctl status etermory
EOF
chmod 440 /etc/sudoers.d/etermory-deploy
visudo -cf /etc/sudoers.d/etermory-deploy > /dev/null

# ---------- systemd ----------
install -m 644 "${RAIZ}/deploy/systemd/etermory.service" /etc/systemd/system/
if [[ "$INSTANCIA" == "app1" ]]; then
    # A limpeza da Lixeira roda numa instância só.
    install -m 644 "${RAIZ}/deploy/systemd/etermory-limpeza.service" /etc/systemd/system/
    install -m 644 "${RAIZ}/deploy/systemd/etermory-limpeza.timer" /etc/systemd/system/
fi
systemctl daemon-reload
systemctl enable etermory
[[ "$INSTANCIA" == "app1" ]] && systemctl enable etermory-limpeza.timer

if grep -q '\[GERAR\|\[SENHA' "${PASTA}/.env"; then
    log AVISO "Serviço habilitado mas NÃO iniciado: preencha o .env e rode"
    log AVISO "  (só na app1) sudo -u deploy ${PASTA}/.venv/bin/flask --app wsgi db upgrade"
    log AVISO "  sudo systemctl start etermory"
else
    systemctl restart etermory
    if esperar_saude "http://127.0.0.1:8000/saude" 30; then
        log INFO "Instância ${INSTANCIA} no ar"
    else
        log ERRO "Não respondeu: journalctl -u etermory -n 50"
    fi
fi

# ---------- Firewall ----------
ufw allow from 192.168.56.10 to any port 8000 proto tcp comment 'Gunicorn so para o vm-proxy'
log INFO "ufw: porta 8000 liberada só para 192.168.56.10"
log INFO "== ${NOME} concluída =="
