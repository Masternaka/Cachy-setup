#!/usr/bin/env bash

set -euo pipefail

die() { printf 'Erreur : %s\n' "$*" >&2; exit 1; }

usage() {
  cat <<'EOF'
Usage : bash scripts/ssh_setup.sh [--plan | --apply | --help]

À lancer dans un terminal local sur l'ordinateur Omarchy cible.
--plan   Affiche les effets prévus sans modifier la machine (par défaut).
--apply  Demande le compte, l'adresse IPv4 locale et le réseau autorisé,
         puis exige la confirmation « ACTIVER » avant toute modification.

Le script remplace /etc/ssh/sshd_config après sauvegarde, installe openssh
si absent, génère les clés d'hôte manquantes et active sshd.service.
Le pare-feu et le routeur ne sont pas modifiés. Voir docs/ssh.md.
EOF
}

# Résultat dans IP_NUMBER. Aucun eval, DNS ou interprétation octale.
ipv4_number() {
  local value=$1 part
  local -a parts
  [[ $value =~ ^[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+$ ]] || return 1
  IFS=. read -r -a parts <<< "$value"
  IP_NUMBER=0
  for part in "${parts[@]}"; do
    [[ ${#part} -le 3 && ( $part == 0 || $part != 0* ) ]] || return 1
    (( 10#$part <= 255 )) || return 1
    IP_NUMBER=$(( (IP_NUMBER << 8) + 10#$part ))
  done
}

validate_network() {
  local address=$1 cidr=$2 base prefix number mask low high private_low private_high
  ipv4_number "$address" || return 1
  number=$IP_NUMBER
  [[ $cidr == */* ]] || return 1
  base=${cidr%/*}; prefix=${cidr##*/}
  [[ $prefix =~ ^([89]|[12][0-9]|30)$ ]] || return 1
  ipv4_number "$base" || return 1
  low=$IP_NUMBER
  mask=$(( (0xFFFFFFFF << (32 - prefix)) & 0xFFFFFFFF ))
  (( (low & mask) == low )) || return 1
  high=$(( low | (0xFFFFFFFF ^ mask) ))
  # Le CIDR entier doit rester dans une plage privée RFC 1918.
  if (( number >= 0x0A000000 && number <= 0x0AFFFFFF )); then
    private_low=$((0x0A000000)); private_high=$((0x0AFFFFFF))
  elif (( number >= 0xAC100000 && number <= 0xAC1FFFFF )); then
    private_low=$((0xAC100000)); private_high=$((0xAC1FFFFF))
  elif (( number >= 0xC0A80000 && number <= 0xC0A8FFFF )); then
    private_low=$((0xC0A80000)); private_high=$((0xC0A8FFFF))
  else
    return 1
  fi
  (( low >= private_low && high <= private_high && number > low && number < high ))
}

write_config() {
  cat <<EOF
# Géré par Omarchy-setup/scripts/ssh_setup.sh ; configuration autonome.
# Les anciennes directives et les fichiers sshd_config.d ne sont pas inclus.
Port 22
AddressFamily inet
ListenAddress $address
AllowUsers $account@$network
PermitRootLogin no
PubkeyAuthentication yes
PasswordAuthentication yes
KbdInteractiveAuthentication no
PermitEmptyPasswords no
UsePAM yes
X11Forwarding no
AllowTcpForwarding no
AllowAgentForwarding no
PermitTunnel no
MaxAuthTries 3
Subsystem sftp internal-sftp
EOF
}

main() {
  [[ $# -le 1 ]] || die 'Un seul argument est accepté.'
  case ${1:---plan} in
    --help|-h) usage; return ;;
    --plan) usage; return ;;
    --apply) ;;
    *) usage >&2; exit 1 ;;
  esac
  [[ $(uname -s) == Linux && -f /etc/arch-release ]] || die 'Omarchy/Arch Linux requis.'
  [[ -z ${SSH_CONNECTION:-} && -z ${SSH_TTY:-} ]] || die 'Utiliser un terminal local, pas une session SSH.'
  [[ -t 0 && -t 1 ]] || die 'Un terminal interactif est requis.'
  [[ $EUID -ne 0 ]] || die 'Lancer avec votre compte habituel, sans sudo devant bash.'
  local cmd account address network confirmation
  for cmd in sudo pacman systemctl ip getent mktemp; do
    command -v "$cmd" >/dev/null || die "Commande absente : $cmd"
  done
  printf '\nAdresses IPv4 disponibles :\n'
  ip -4 -o address show scope global
  read -r -p "Compte autorisé [$(id -un)] : " account
  account=${account:-$(id -un)}
  [[ $account =~ ^[a-z_][a-z0-9_-]*[$]?$ && $account != root ]] || die 'Compte non valide.'
  getent passwd "$account" >/dev/null || die 'Ce compte doit déjà exister.'
  [[ $(id -u "$account") -ne 0 ]] || die 'Compte root interdit.'
  read -r -p 'Adresse IPv4 de cet ordinateur (ex. 192.168.1.50) : ' address
  read -r -p 'Sous-réseau de la maison (ex. 192.168.1.0/24) : ' network
  validate_network "$address" "$network" || die 'Adresse/CIDR privé invalide ou adresse hors du réseau (préfixes /8 à /30).'
  ip -4 -o address show scope global | awk '{split($4,a,"/"); print a[1]}' | \
    { local found=0 value; while read -r value; do [[ $value != "$address" ]] || found=1; done; [[ $found == 1 ]]; } \
    || die "Cette adresse n'est pas configurée sur cet ordinateur."
  local enabled active
  enabled=$(systemctl is-enabled sshd.service 2>/dev/null || true)
  active=$(systemctl is-active sshd.service 2>/dev/null || true)
  case $enabled in enabled|disabled|not-found|'') ;; *) die "État inhabituel de sshd.service : $enabled. Examiner manuellement." ;; esac
  case $active in active|inactive|unknown|'') ;; *) die "État inhabituel du service : $active. Examiner manuellement." ;; esac
  if systemctl is-active --quiet sshd.socket || systemctl is-enabled --quiet sshd.socket 2>/dev/null; then
    die 'sshd.socket est actif ou activé : examiner cette configuration avant de continuer.'
  fi
  cat <<EOF

Intervention proposée :
  - installer openssh avec pacman si absent (sans mise à jour automatique) ;
  - sauvegarder /etc/ssh/sshd_config sous /var/backups/omarchy-ssh.* ;
  - remplacer cette configuration, sans inclure les anciens fragments ;
  - autoriser uniquement $account depuis $network sur $address:22 (IPv4) ;
  - autoriser la clé SSH ou le mot de passe actuel du compte ;
  - interdire root et les redirections SSH ;
  - générer les clés d'hôte manquantes, activer et redémarrer sshd.service.
Les autres accès SSH existants peuvent être interrompus.
Le pare-feu, le mot de passe du compte et le routeur restent inchangés.
EOF
  read -r -p 'Pour autoriser précisément cette intervention, saisir ACTIVER : ' confirmation
  [[ $confirmation == ACTIVER ]] || die 'Annulé, aucune modification effectuée.'
  sudo -v
  if ! pacman -Q openssh >/dev/null 2>&1; then
    sudo pacman -S --needed openssh
  fi
  sudo test -f /etc/ssh/sshd_config || die 'Configuration SSH introuvable.'
  sudo test ! -L /etc/ssh/sshd_config || die 'Configuration symbolique : intervention manuelle requise.'
  [[ -z $(systemctl show sshd.service -p DropInPaths --value) ]] || die 'sshd.service possède des surcharges : examiner manuellement.'
  [[ $(systemctl show sshd.service -p FragmentPath --value) == /usr/lib/systemd/system/sshd.service ]] || die 'Unité SSH personnalisée : examiner manuellement.'
  local backup candidate changed=0
  sudo mkdir -p /var/backups
  backup=$(sudo mktemp -d /var/backups/omarchy-ssh.XXXXXXXX)
  sudo chmod 700 "$backup"
  sudo cp -a /etc/ssh/sshd_config "$backup/sshd_config"
  printf 'enabled=%s\nactive=%s\n' "$enabled" "$active" | sudo tee "$backup/service-state.txt" >/dev/null
  printf 'Sauvegarde : %s\n' "$backup"
  candidate=$(sudo mktemp /etc/ssh/.omarchy-home.XXXXXXXX)
  # En cas d'échec, restaurer la configuration et les états de service initiaux.
  trap 'rc=$?; trap - EXIT; sudo rm -f -- "$candidate"; if (( rc != 0 && changed )); then
    printf "Échec : restauration de %s\n" "$backup" >&2
    sudo cp -a -- "$backup/sshd_config" /etc/ssh/sshd_config
    if [[ $enabled != enabled ]]; then sudo systemctl disable sshd.service; fi
    if [[ $active == active ]]; then sudo systemctl restart sshd.service; else sudo systemctl stop sshd.service; fi
    printf "Vérifier la restauration avec sudo systemctl status sshd.service.\n" >&2
  fi; exit "$rc"' EXIT
  write_config | sudo tee "$candidate" >/dev/null
  sudo chown root:root "$candidate"
  sudo chmod 600 "$candidate"
  sudo ssh-keygen -A
  sudo /usr/bin/sshd -t -f "$candidate"
  changed=1
  sudo mv -f -- "$candidate" /etc/ssh/sshd_config
  sudo systemctl enable sshd.service
  sudo systemctl restart sshd.service
  sudo systemctl is-active --quiet sshd.service
  # Les variables locales utilisées par le piège existent encore ici.
  trap - EXIT
  printf '\nSSH actif. Depuis un autre ordinateur : ssh %s@%s\n' "$account" "$address"
  printf 'Sauvegarde : %s\n' "$backup"
  printf 'Empreintes du serveur à comparer lors de la première connexion :\n'
  local key
  for key in /etc/ssh/ssh_host_*_key.pub; do
    [[ ! -f $key ]] || ssh-keygen -lf "$key"
  done
  printf '\nConnexion réseau non testée. Si elle bloque, voir docs/ssh.md (pare-feu).\n'
}

if [[ ${BASH_SOURCE[0]} == "$0" ]]; then
  main "$@"
fi
