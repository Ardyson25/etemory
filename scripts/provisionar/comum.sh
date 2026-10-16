#!/usr/bin/env bash
# Configuração comum a TODAS as VMs: nome, fuso, /etc/hosts, pacotes base,
# usuários e grupos, SSH só com chave e firewall com tudo bloqueado.
#
# Onde roda: em cada VM, uma vez, logo após instalar o Ubuntu Server:
#   git clone <URL-DO-GITHUB> ~/etermory
#   sudo ~/etermory/scripts/provisionar/comum.sh vm-app1
# Depois rode o script da função da VM (proxy.sh, app.sh ou db.sh).
set -euo pipefail
RAIZ="$(cd "$(dirname "$(readlink -f "$0")")/../.." && pwd)"
# shellcheck source=SCRIPTDIR/../lib.sh
source "${RAIZ}/scripts/lib.sh"
ARQUIVO_LOG="/var/log/etermory-provisionamento.log"

exigir_root
NOME="${1:-}"
case "$NOME" in
    vm-proxy|vm-app1|vm-app2|vm-db) ;;
    *) falhar 1 "Uso: $0 vm-proxy|vm-app1|vm-app2|vm-db" ;;
esac

log INFO "== Provisionamento comum de ${NOME} =="

# ---------- Nome, fuso e nomes da rede ----------
hostnamectl set-hostname "$NOME"
timedatectl set-timezone America/Sao_Paulo
sed -i '/# >>> etermory/,/# <<< etermory/d' /etc/hosts
sed -n '/# >>> etermory/,/# <<< etermory/p' "${RAIZ}/deploy/rede/hosts" >> /etc/hosts
log INFO "Hostname, fuso e /etc/hosts configurados"

# ---------- Pacotes base ----------
export DEBIAN_FRONTEND=noninteractive
apt-get update -q
apt-get install -y -q ufw curl git htop acl rsync logrotate openssh-server openssl
log INFO "Pacotes base instalados"

# ---------- Grupos e usuários de serviço ----------
# UID/GID fixos: o NFS identifica dono de arquivo pelo número, então
# "etermory" precisa ser 1500 em todas as VMs.
getent group etermory-dev > /dev/null || groupadd etermory-dev
getent group etermory > /dev/null || groupadd --system --gid 1500 etermory
id etermory &> /dev/null || useradd --system --uid 1500 --gid etermory \
    --home-dir /nonexistent --no-create-home --shell /usr/sbin/nologin etermory
id deploy &> /dev/null || useradd --uid 1501 --create-home --shell /bin/bash deploy
usermod -aG etermory,etermory-dev deploy
# shellcheck disable=SC2016  # aspas simples de propósito: expande no shell do deploy
runuser -u deploy -- bash -c \
    '[[ -f ~/.ssh/id_ed25519 ]] || ssh-keygen -q -t ed25519 -N "" -f ~/.ssh/id_ed25519 -C "deploy@$(hostname)"'
# Quem está rodando a instalação continua podendo entrar por SSH.
if [[ -n "${SUDO_USER:-}" && "${SUDO_USER}" != "root" ]]; then
    usermod -aG etermory-dev "$SUDO_USER"
fi
log INFO "Usuários de serviço: etermory (sem login, roda o Gunicorn) e deploy (Git e deploy)"

# ---------- Integrantes do grupo ----------
admins_com_chave=0
while IFS=';' read -r login nome admin; do
    [[ -z "$login" || "$login" == \#* ]] && continue
    if ! id "$login" &> /dev/null; then
        useradd --create-home --shell /bin/bash --comment "$nome" --groups etermory-dev "$login"
        senha=$(openssl rand -base64 12)
        echo "${login}:${senha}" | chpasswd
        chage -d 0 "$login"   # obriga a trocar no primeiro acesso
        # A senha aparece só na tela (não vai para o log): entregue a cada um.
        echo "  senha inicial de ${login}: ${senha}"
    fi
    if [[ "$admin" == "sim" ]]; then
        usermod -aG sudo "$login"
    fi
    chave="${RAIZ}/deploy/chaves/${login}.pub"
    if [[ -f "$chave" ]]; then
        install -d -m 700 -o "$login" -g "$login" "/home/${login}/.ssh"
        install -m 600 -o "$login" -g "$login" "$chave" "/home/${login}/.ssh/authorized_keys"
        [[ "$admin" == "sim" ]] && admins_com_chave=$((admins_com_chave + 1))
    fi
done < "${RAIZ}/deploy/usuarios.txt"
log INFO "Integrantes criados (grupo etermory-dev; sudo só para admin=sim)"

# ---------- SSH ----------
cat > /etc/ssh/sshd_config.d/99-etermory.conf << 'EOF'
# Etermory: endurecimento do SSH
PermitRootLogin no
PubkeyAuthentication yes
AllowGroups etermory-dev
MaxAuthTries 3
X11Forwarding no
EOF
if (( admins_com_chave > 0 )); then
    printf 'PasswordAuthentication no\nKbdInteractiveAuthentication no\n' \
        >> /etc/ssh/sshd_config.d/99-etermory.conf
    log INFO "SSH: só com chave, root bloqueado"
else
    log AVISO "Nenhum admin com chave em deploy/chaves/: senha continua liberada para não trancar a VM"
fi
sshd -t && systemctl reload ssh

# ---------- Logs ----------
install -d -m 2770 -o etermory -g etermory-dev /var/log/etermory
install -m 644 "${RAIZ}/deploy/logrotate/etermory" /etc/logrotate.d/etermory
log INFO "Pasta /var/log/etermory e logrotate configurados"

# ---------- Firewall: tudo bloqueado, só SSH da rede de administração ----------
ufw default deny incoming
ufw default allow outgoing
ufw allow from 192.168.56.0/24 to any port 22 proto tcp comment 'SSH da rede de administracao'
ufw --force enable
log INFO "ufw ativo (entrada bloqueada; SSH só de 192.168.56.0/24)"

log INFO "Chave pública do deploy desta VM (use no proxy.sh/app.sh):"
cat /home/deploy/.ssh/id_ed25519.pub
log INFO "== ${NOME}: comum concluído. Agora rode o script da função da VM. =="
