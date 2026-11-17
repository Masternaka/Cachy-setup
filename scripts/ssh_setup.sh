#!/usr/bin/env bash
# Adapté de Masternaka/CachyOS, 01 - systemd_services.sh (17 novembre 2026).
# Blob de référence : deae51cb015a520da264f7f7f591982c6aa0742e.
# Ici, seul sshd.service est concerné ; aucune réécriture de sshd_config.
set -Eeuo pipefail

SSH_BACKUP_ROOT=/var/lib/cachy-setup
BACKUP=
ENABLED_STATE=
ACTIVE_STATE=

die() { printf 'Erreur : %s\n' "$*" >&2; exit 1; }
usage() {
  cat <<'HELP'
Usage : bash scripts/ssh_setup.sh [--plan | --dry-run | --apply | --help]
Sans option, --plan ou --dry-run : inspecter OpenSSH et sshd.service sans sudo.
--apply : depuis un terminal local, confirmer ACTIVER, valider la configuration
existante puis activer/démarrer sshd.service si nécessaire, sans redémarrage.

Le paquet openssh doit être installé séparément. Aucun paquet n'est installé.
La configuration SSH, les clés, comptes, ports et règles de pare-feu sont conservés.
Les accès autorisés dépendent de la configuration existante, pas d'une restriction
ajoutée par ce script. Aucun service Bluetooth ni timer n'est traité ici.
Les états initiaux et les commandes de retour arrière sont sauvegardés.
Voir docs/ssh.md avant application.
HELP
}

check_target() {
  [[ $(uname -s) == Linux && -r /etc/os-release ]] || die 'CachyOS installé requis.'
  local ID=
  source /etc/os-release
  [[ $ID == cachyos && ! -d /run/archiso ]] || die 'Démarrer sur CachyOS installé, hors de l’ISO.'
  local cmd
  for cmd in pacman systemctl sudo; do
    command -v "$cmd" >/dev/null || die "Commande requise absente : $cmd"
  done
  systemctl show --property=Version --value >/dev/null || die 'Gestionnaire systemd système indisponible.'
  pacman -Q openssh >/dev/null 2>&1 || die 'Paquet openssh absent : installation distincte nécessaire.'
  [[ -x /usr/bin/sshd ]] || die 'Exécutable /usr/bin/sshd absent malgré le paquet openssh.'
}

read_state() {
  local output key value load= fragment= dropins=
  ENABLED_STATE= ACTIVE_STATE=
  output=$(systemctl show sshd.service --property=LoadState,UnitFileState,ActiveState,FragmentPath,DropInPaths) || die 'Lecture de sshd.service impossible.'
  while IFS='=' read -r key value; do
    case $key in
      LoadState) load=$value ;;
      UnitFileState) ENABLED_STATE=$value ;;
      ActiveState) ACTIVE_STATE=$value ;;
      FragmentPath) fragment=$value ;;
      DropInPaths) dropins=$value ;;
    esac
  done <<< "$output"
  [[ $load == loaded ]] || die "sshd.service indisponible : ${load:-inconnu}"
  case $ENABLED_STATE in enabled|enabled-runtime|disabled) ;; *) die "Activation inhabituelle : $ENABLED_STATE ; aucun démasquage automatique." ;; esac
  case $ACTIVE_STATE in active|inactive|failed) ;; *) die "État SSH instable ou inconnu : $ACTIVE_STATE" ;; esac
  [[ $fragment == /usr/lib/systemd/system/sshd.service && -z $dropins ]] || die 'Unité SSH personnalisée ou surchargée : examen manuel requis.'
  output=$(systemctl show sshd.socket --property=LoadState,UnitFileState,ActiveState) || die 'Diagnostic sshd.socket impossible.'
  while IFS='=' read -r key value; do
    case $key:$value in
      UnitFileState:enabled|UnitFileState:enabled-runtime|UnitFileState:linked|UnitFileState:linked-runtime|ActiveState:active|ActiveState:activating)
        die 'sshd.socket actif ou activé : examiner cette autre méthode de démarrage.' ;;
    esac
  done <<< "$output"
}

show_plan() {
  printf '\nCachyOS · OpenSSH\n  sshd.service : activation=%s ; état=%s\n' "$ENABLED_STATE" "$ACTIVE_STATE"
  if [[ $ENABLED_STATE == enabled && $ACTIVE_STATE == active ]]; then
    printf '  Déjà activé durablement et actif : aucune action prévue.\n'
  else
    printf '  Prévu : sauvegarder les états, valider sshd_config, activer durablement et démarrer si nécessaire.\n'
  fi
  printf '  sshd_config et ses fragments sont conservés. Aucun redémarrage du service actif.\n'
  printf '  Ports, interfaces et accès : ceux de la configuration existante. Pare-feu et routeur inchangés.\n'
}

apply_ssh() {
  local initial_enabled=$ENABLED_STATE initial_active=$ACTIVE_STATE
  if [[ $initial_enabled == enabled && $initial_active == active ]]; then
    printf 'SSH déjà prêt : aucune modification.\n'
    return
  fi
  # Vérifier la configuration réelle, ses Includes et les clés existantes.
  # Aucune clé d'hôte n'est générée pour faire passer ce contrôle.
  sudo /usr/bin/sshd -t || die 'Configuration ou clés SSH invalides ; service inchangé.'
  sudo install -d -m 0700 "$SSH_BACKUP_ROOT"
  BACKUP=$(sudo mktemp -d "$SSH_BACKUP_ROOT/ssh-XXXXXXXX")
  printf 'activation=%s\netat=%s\n' "$initial_enabled" "$initial_active" | sudo tee "$BACKUP/service-state.txt" >/dev/null
  {
    printf '%s\n' '#!/usr/bin/env bash' 'set -euo pipefail' \
      '# Examiner avant exécution manuelle avec sudo bash.' \
      '# Restaure activation et état démarré/arrêté ; pas un ancien état failed.'
    if [[ $initial_enabled != enabled ]]; then
      printf 'systemctl disable sshd.service\n'
      if [[ $initial_enabled == enabled-runtime ]]; then printf 'systemctl enable --runtime sshd.service\n'; fi
    fi
    if [[ $initial_active == active ]]; then printf 'systemctl start sshd.service\n'; else printf 'systemctl stop sshd.service\n'; fi
  } | sudo tee "$BACKUP/retour-arriere.sh" >/dev/null
  sudo chmod 0600 "$BACKUP/retour-arriere.sh"
  printf 'États et retour arrière : %s\n' "$BACKUP"
  # Comme dans 01, journaliser avant chaque action et ne pas exécuter le retour
  # arrière automatiquement : un démarrage peut avoir des effets extérieurs.
  trap 'rc=$?; if ((rc != 0)); then printf "Échec/interruption : état SSH potentiellement partiel. Examiner %s/retour-arriere.sh et docs/ssh.md.\n" "$BACKUP" >&2; fi' EXIT
  trap 'exit 130' INT
  trap 'exit 143' TERM
  if [[ $initial_enabled != enabled ]]; then sudo systemctl enable sshd.service; fi
  if [[ $initial_active != active ]]; then sudo systemctl start sshd.service; fi
  read_state
  [[ $ENABLED_STATE == enabled && $ACTIVE_STATE == active ]] || die "Objectif SSH non atteint ; retour arrière : $BACKUP"
  trap - EXIT INT TERM
  printf 'SSH activé durablement et actif ; configuration existante conservée.\n'
  printf 'Connexion depuis un autre ordinateur non testée. Voir docs/ssh.md.\n'
}

main() {
  [[ $# -le 1 ]] || die 'Un seul argument est accepté.'
  local mode=${1---plan} answer initial_enabled initial_active
  case $mode in
    --help|-h) usage; return ;;
    --plan|--dry-run|--apply) ;;
    *) usage >&2; die "Option inconnue : $mode" ;;
  esac
  check_target
  read_state
  show_plan
  [[ $mode == --apply ]] || return 0
  [[ $EUID -ne 0 && -t 0 && -t 1 && -z ${SSH_CONNECTION:-} && -z ${SSH_TTY:-} ]] || die 'Lancer sans sudo depuis un terminal local interactif.'
  [[ $ENABLED_STATE != enabled || $ACTIVE_STATE != active ]] || return 0
  initial_enabled=$ENABLED_STATE initial_active=$ACTIVE_STATE
  read -r -p 'Pour autoriser cette activation SSH, saisir ACTIVER : ' answer
  [[ $answer == ACTIVER ]] || die 'Annulé, aucune modification effectuée.'
  sudo -v
  check_target
  read_state
  [[ $ENABLED_STATE == "$initial_enabled" && $ACTIVE_STATE == "$initial_active" ]] || die 'État SSH modifié depuis le plan : relancer pour examiner.'
  apply_ssh
}

if [[ ${BASH_SOURCE[0]} == "$0" ]]; then main "$@"; fi
