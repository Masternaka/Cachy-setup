#!/usr/bin/env bash

set -euo pipefail

# AJOUTER ICI LES QUATRE UUID ext4 (lsblk -f).
UUIDS=(
  ""
  ""
  ""
  ""
)

# Facultatif : vide = conserver le label actuel (ou Disque1… s'il est absent).
# Un label ext4 est limité à 16 octets. Ne pas mettre de « / ».
LABELS=("" "" "" "")

# Vide = le compte qui lance le script. Lancer sans sudo devant bash.
OWNER=""
# true : reprendre aussi les fichiers existants ; false : seulement la racine.
RECURSIVE=true

die() { printf 'Erreur : %s\n' "$*" >&2; exit 1; }
usage() {
  cat <<'EOF'
Usage : bash scripts/disk_setup.sh [--plan | --apply | --help]
  --plan   Affiche les UUID et les effets prévus, sans sudo (par défaut).
  --apply  Vérifie les quatre partitions puis demande la saisie CONFIGURER.

Effets : sauvegarde de fstab, des labels et des propriétaires/permissions,
montage automatique sous /mnt/<label>, affichage demandé via x-gvfs-show,
attribution au compte choisi. Ni formatage, ni changement d'UUID.
Les partitions doivent être démontées avant --apply.
Voir docs/disques.md pour la procédure et le retour arrière.
EOF
}

validate_settings() {
  local i j label
  [[ ${#UUIDS[@]} == 4 && ${#LABELS[@]} == 4 ]] || die 'Prévoir exactement quatre UUID et quatre labels.'
  [[ $RECURSIVE == true || $RECURSIVE == false ]] || die 'RECURSIVE doit être true ou false.'
  for i in 0 1 2 3; do
    [[ ${UUIDS[i]} =~ ^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$ ]] \
      || die "Remplir l'UUID numéro $((i + 1)) avec un UUID ext4 valide."
    UUIDS[i]=$(printf %s "${UUIDS[i]}" | tr '[:upper:]' '[:lower:]')
    for ((j=0; j<i; j++)); do
      [[ ${UUIDS[i]} != "${UUIDS[j]}" ]] || die 'UUID en double.'
    done
    label=${LABELS[i]}
    [[ $label != */* && ! $label =~ [[:cntrl:]] && $label != *\\* && $label != . && $label != .. ]] \
      || die 'Label non valide : éviter slash, antislash et caractères de contrôle.'
    [[ $(LC_ALL=C printf %s "$label" | wc -c) -le 16 ]] || die 'Label trop long (16 octets maximum).'
  done
}

main() {
  [[ $# -le 1 ]] || die 'Un seul argument est accepté.'
  case ${1:---plan} in
    --help|-h) usage; return ;;
    --plan|--apply) ;;
    *) usage >&2; exit 1 ;;
  esac
  usage
  validate_settings
  printf '\nUUID configurés :\n'; printf '  %s\n' "${UUIDS[@]}"
  [[ ${1:---plan} == --apply ]] || return 0
  [[ $(uname -s) == Linux && -f /etc/arch-release ]] || die 'Ce script cible Omarchy/Arch Linux.'
  [[ $EUID -ne 0 ]] || die 'Lancer avec votre compte habituel, sans sudo devant bash.'
  [[ -t 0 && -t 1 && -z ${SSH_CONNECTION:-} ]] || die 'Utiliser un terminal local interactif.'
  local cmd owner uid gid i j device label target confirmation backup candidate
  local -a devices labels targets oldlabels
  for cmd in sudo blkid findmnt lsblk e2label getfacl setfacl getfattr setfattr python3 systemctl find mount umount chown; do
    command -v "$cmd" >/dev/null || die "Commande requise absente : $cmd. Aucun paquet ne sera installé automatiquement."
  done
  owner=${OWNER:-$(id -un)}
  uid=$(id -u "$owner") || die 'Compte inconnu.'
  gid=$(id -g "$owner")
  [[ $uid != 0 ]] || die 'Le propriétaire doit être un compte non root.'
  [[ ! -L /etc/fstab && -f /etc/fstab ]] || die 'fstab absent ou symbolique : examiner manuellement.'
  sudo -v
  for i in 0 1 2 3; do
    # Pas de cache : exiger une correspondance unique, même avec des clones.
    device=$(sudo blkid -c /dev/null -t "UUID=${UUIDS[i]}" -o device) || die "UUID absent : ${UUIDS[i]}"
    [[ $device != *$'\n'* && -b $device ]] || die 'UUID ambigu ou périphérique non bloc.'
    [[ $(sudo blkid -p -s TYPE -o value "$device") == ext4 ]] || die "$device n'est pas ext4."
    [[ $(lsblk -dn -o RO "$device") == 0 ]] || die "$device est en lecture seule."
    # Refuser tout montage existant visible dans cet espace de montage.
    if findmnt --source "$device" --noheadings >/dev/null; then
      die "$device est monté. Le démonter manuellement avant de poursuivre (jamais une partition système)."
    fi
    oldlabels[i]=$(sudo e2label "$device")
    label=${LABELS[i]:-${oldlabels[i]}}
    label=${label:-Disque$((i + 1))}
    LABELS[i]=$label
    validate_settings
    target=/mnt/$label
    for ((j=0; j<i; j++)); do
      [[ $target != "${targets[j]}" ]] || die 'Deux partitions ont le même label : choisir des labels distincts.'
    done
    [[ ! -L /mnt && ! -L $target ]] || die 'Le point de montage est un lien symbolique.'
    if [[ -e $target ]]; then
      [[ -d $target ]] || die "$target n'est pas un dossier."
      [[ -z $(sudo find "$target" -mindepth 1 -maxdepth 1 -print -quit) ]] || die "$target n'est pas vide."
    fi
    if findmnt --mountpoint "$target" --noheadings >/dev/null; then die "$target est déjà monté."; fi
    devices[i]=$device; labels[i]=$label; targets[i]=$target
    printf '\n%s → %s → %s\n' "${UUIDS[i]}" "$device" "$target"
    printf '  Label : %s → %s ; propriétaire : %s (%s:%s) ; récursif : %s\n' "${oldlabels[i]}" "$label" "$owner" "$uid" "$gid" "$RECURSIVE"
  done
  printf '\nLes entrées fstab de ces partitions seront remplacées ; les autres seront conservées.\n'
  printf 'Une sauvegarde ACL/propriétaires précède toute prise de possession.\n'
  read -r -p 'Pour autoriser ces changements, saisir CONFIGURER : ' confirmation
  [[ $confirmation == CONFIGURER ]] || die 'Annulé.'
  sudo mkdir -p /var/backups
  backup=$(sudo mktemp -d /var/backups/omarchy-disks.XXXXXXXX)
  sudo chmod 700 "$backup"
  sudo cp -a /etc/fstab "$backup/fstab"
  candidate=$backup/fstab.new
  # Générer fstab sans interpréter les chaînes comme du code shell.
  sudo python3 - "$backup/fstab" "$candidate" "${UUIDS[@]}" "${devices[@]}" "${labels[@]}" <<'PY'
import os, re, sys
source, dest = sys.argv[1:3]
uuids, devices, labels = sys.argv[3:7], sys.argv[7:11], sys.argv[11:15]
targets = ['/mnt/' + label for label in labels]
def unescape(value):
    return re.sub(r'\\([0-7]{3})', lambda m: chr(int(m[1], 8)), value)
def escape(value):
    return value.replace('\\', r'\134').replace(' ', r'\040').replace('\t', r'\011')
result = []
for line in open(source):
    fields = line.split()
    if not fields or fields[0].startswith('#'):
        result.append(line); continue
    if len(fields) < 4:
        raise SystemExit('fstab malformé : corriger manuellement avant de poursuivre.')
    spec, target = map(unescape, fields[:2])
    selected = spec.lower() in ['uuid=' + u for u in uuids]
    if spec.startswith('/'):
        selected |= os.path.realpath(spec) in [os.path.realpath(d) for d in devices]
    for tag, folder in [('LABEL=', 'by-label'), ('PARTLABEL=', 'by-partlabel'), ('PARTUUID=', 'by-partuuid')]:
        if spec.startswith(tag):
            selected |= os.path.realpath('/dev/disk/' + folder + '/' + spec[len(tag):]) in [os.path.realpath(d) for d in devices]
    if selected:
        if not target.startswith(('/mnt/', '/media/', '/run/media/')):
            raise SystemExit('Entrée système ou personnalisée refusée : ' + line)
        result.append('# Ancienne entrée sauvegardée : ' + line)
    elif any(target == t or target.startswith(t + '/') or spec == t or spec.startswith(t + '/') for t in targets):
        raise SystemExit('Point de montage déjà déclaré pour une autre source : ' + target)
    else:
        result.append(line)
result.append('\n# Disques secondaires personnels — Omarchy-setup\n')
for uuid, target in zip(uuids, targets):
    result.append(f'UUID={uuid} {escape(target)} ext4 defaults,nofail,x-systemd.device-timeout=10s,x-gvfs-show 0 2\n')
with open(dest, 'x') as output:
    output.write(''.join(result))
PY
  sudo findmnt --verify --tab-file "$candidate"
  printf '\nSauvegarde et journal de restauration : %s\n' "$backup"
  # Les étapes restent journalisées même en cas d'interruption. Pas de faux
  # retour arrière automatique après un chown partiellement effectué.
  trap 'printf "Interruption/échec. Sauvegarde : %s ; voir docs/disques.md pour restaurer.\n" "$backup" >&2' ERR
  for i in 0 1 2 3; do
    printf '%s\n' "${oldlabels[i]}" | sudo tee "$backup/label-$i.txt" >/dev/null
    printf '%s\n' "${UUIDS[i]}" | sudo tee "$backup/uuid-$i.txt" >/dev/null
    printf '%s\n' "${targets[i]}" | sudo tee "$backup/target-$i.txt" >/dev/null
    sudo mkdir -p -- "${targets[i]}"
    sudo mount -t ext4 -o rw -- "${devices[i]}" "${targets[i]}"
    [[ $(findmnt --mountpoint "${targets[i]}" -n -o UUID) == "${UUIDS[i]}" ]] || die 'UUID monté différent : arrêt.'
    # -P : ne pas suivre les liens symboliques ; -p : chemins absolus.
    if [[ $RECURSIVE == true ]]; then
      sudo getfacl -R -P -p -n -- "${targets[i]}" | sudo tee "$backup/permissions-$i.acl" >/dev/null
    else
      sudo getfacl -p -n -- "${targets[i]}" | sudo tee "$backup/permissions-$i.acl" >/dev/null
    fi
    # chown peut effacer les capacités exécutables : les sauvegarder aussi.
    if [[ $RECURSIVE == true ]]; then
      sudo getfattr -R -h -d -m '^security.capability$' --absolute-names -- "${targets[i]}" | sudo tee "$backup/capabilities-$i.attrs" >/dev/null
    else
      sudo getfattr -h -d -m '^security.capability$' --absolute-names -- "${targets[i]}" | sudo tee "$backup/capabilities-$i.attrs" >/dev/null
    fi
    sudo touch "$backup/permissions-$i.complete"
    sudo e2label "${devices[i]}" "${labels[i]}"
    if [[ $RECURSIVE == true ]]; then
      sudo find "${targets[i]}" -xdev ! -type l -exec chown --no-dereference "$uid:$gid" -- {} +
    else
      sudo chown --no-dereference "$uid:$gid" -- "${targets[i]}"
    fi
  done
  # Ne pas écraser un changement parallèle de fstab.
  sudo cmp -s /etc/fstab "$backup/fstab" || die 'fstab a changé pendant le travail : montage persistant non appliqué.'
  sudo cp -- "$candidate" /etc/fstab
  sudo systemctl daemon-reload
  trap - ERR
  printf '\nLes quatre disques sont montés et appartiennent à %s.\nSauvegarde : %s\n' "$owner" "$backup"
  printf 'Rouvrir le gestionnaire de fichiers pour vérifier leur affichage.\n'
}

if [[ ${BASH_SOURCE[0]} == "$0" ]]; then main "$@"; fi
