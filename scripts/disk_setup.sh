#!/usr/bin/env bash
# Adapté de Masternaka/CachyOS, 10 - disk_setup.sh, consulté le 17 novembre 2026.
# Blob de référence : 175644549a28c9fcb3c1f1981eed1ae248c3294e.
# Labels et propriété des quatre volumes de données ext4 de Gabriel.
# Aperçu par défaut ; voir docs/disques.md avant toute application.
set -euo pipefail
export LC_ALL=C PATH=/usr/bin:/bin

OWNER=gabriel
UUIDS=(
    58cdcfb4-b7c7-45aa-9d27-97d3567e77ba
    7c61158b-ac8c-42e6-90ed-1f659acf4335
    cab0291d-9a2a-4110-a02f-6783238dcda3
    d594fd69-fb7d-485a-aab4-272da6bee7e0
)
LABELS=('Backup Medias' 'Disque Samsung' 'Medias' 'SSD')
FSTAB=/etc/fstab
BOOT_MOUNT_OPTIONS=defaults,nofail

CYAN='' GREEN='' YELLOW='' RED='' RESET=''
if [[ -t 1 && -t 2 && -z "${NO_COLOR:-}" && "${TERM:-dumb}" != dumb ]]; then
    CYAN='\033[1;36m' GREEN='\033[1;32m' YELLOW='\033[1;33m' RED='\033[1;31m' RESET='\033[0m'
fi
step() { printf '\n%b── %s%b\n' "$CYAN" "$1" "$RESET"; }
status() { printf '  %b[%s]%b %s\n' "$1" "$2" "$RESET" "$3"; }
fatal() { status "$RED" 'Échec' "$1" >&2; exit 1; }
validate_settings() {
    local i j label
    [[ ${#UUIDS[@]} == 4 && ${#LABELS[@]} == 4 ]] || fatal 'Quatre UUID et quatre labels sont requis.'
    for i in 0 1 2 3; do
        [[ ${UUIDS[i]} =~ ^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$ ]] || fatal 'UUID ext4 non valide.'
        label=${LABELS[i]}
        [[ -n $label && $label != */* && $label != *\\* && $label != . && $label != .. && ! $label =~ [[:cntrl:]] && ${#label} -le 16 ]] || fatal 'Label non valide (1 à 16 octets, sans slash ni caractère de contrôle).'
        for ((j=0; j<i; j++)); do
            [[ ${UUIDS[i]} != "${UUIDS[j]}" && $label != "${LABELS[j]}" ]] || fatal 'UUID ou label en double.'
        done
    done
}
usage() {
    cat <<'HELP'
Usage : bash scripts/disk_setup.sh [--plan | --dry-run | --apply | --help]

Sans option, --plan ou --dry-run : inventaire et plan sans sudo ni écriture.
--apply : vérifications interactives, proposition sudo puis saisie APPLIQUER.
Voir docs/disques.md pour les prérequis, sauvegardes et le retour arrière.

Le plan comprend le montage automatique des volumes au démarrage via /etc/fstab.
Le script demande sudo avant les vérifications administrateur. Les volumes
doivent être démontés et toute modification exige la saisie d’APPLIQUER.
HELP
}

MODE=preview
case "$#:${1:-}" in
    0:) ;;
    1:--plan|1:--dry-run) MODE=preview ;;
    1:--apply) MODE=interactive ;;
    1:--help|1:-h) usage; exit 0 ;;
    *) usage >&2; exit 2 ;;
esac

step 'CachyOS · Volumes secondaires'
if [[ "$MODE" != preview ]]; then
    [[ -t 0 && -t 1 && -z ${SSH_CONNECTION:-} && -z ${SSH_TTY:-} ]] || fatal 'Un terminal local interactif est requis pour appliquer.'
    status "$CYAN" 'Privilèges' 'Les modifications nécessitent sudo et la confirmation APPLIQUER.'
else
    status "$CYAN" 'Simulation' 'Aucun sudo ni écriture ; lecture de l’inventaire uniquement.'
fi

[[ "$(uname -s)" == Linux ]] || fatal 'Ce script nécessite Linux.'
[[ -r /etc/os-release ]] || fatal 'Distribution indéterminée.'
source /etc/os-release
[[ ${ID:-} == cachyos ]] || fatal 'Ce script cible CachyOS.'
[[ ! -d /run/archiso ]] || fatal 'Démarrer sur le système installé, hors de l’ISO.'
validate_settings
OWNER_UID=$(id -u "$OWNER") || fatal "Compte introuvable : $OWNER."
(( OWNER_UID != 0 )) || fatal 'Le compte cible doit avoir un UID différent de 0.'
for tool in lsblk findmnt; do
    command -v "$tool" >/dev/null || fatal "Outil manquant : $tool."
done

mounted_device_numbers() {
    findmnt --kernel --noheadings --raw -o MAJ:MIN
}

discover() {
    local inventory mounted wanted uuid device fs kind node found actual label_plan i
    inventory=$(lsblk -lpn -o UUID,PATH,FSTYPE,TYPE,MAJ:MIN) ||
        fatal 'Inventaire des volumes indisponible.'
    mounted=$(mounted_device_numbers) ||
        fatal 'Table des montages indisponible.'
    DEVICES=() NODES=()
    ALL_OFFLINE=true
    for i in "${!UUIDS[@]}"; do
        wanted="${UUIDS[i]}" found=0
        while read -r uuid device fs kind node; do
            [[ "$uuid" == "$wanted" ]] || continue
            (( found += 1 ))
            [[ "$fs" == ext4 && "$kind" == part && "$device" == /dev/* &&
               -b "$device" && "$node" =~ ^[0-9]+:[0-9]+$ ]] ||
                fatal "La cible $wanted doit être une partition ext4."
            DEVICES[i]="$device" NODES[i]="$node"
        done <<< "$inventory"
        (( found == 1 )) || fatal "Une seule partition est attendue pour ${LABELS[i]} ($wanted), relevé : $found."
        actual=$(lsblk --nodeps --noheadings -o LABEL -- "${DEVICES[i]}") ||
            fatal "Lecture du label impossible sur ${DEVICES[i]}."
        if [[ "$actual" == "${LABELS[i]}" ]]; then
            label_plan="label « $actual » déjà correct"
        else
            label_plan="label « ${actual:-sans label} » → « ${LABELS[i]} »"
        fi
        if [[ $'\n'"$mounted"$'\n' == *$'\n'"${NODES[i]}"$'\n'* ]]; then
            ALL_OFFLINE=false
            status "$YELLOW" 'Monté' "${DEVICES[i]} · $label_plan"
        else
            status "$CYAN" 'Démonté' "${DEVICES[i]} · $label_plan"
        fi
    done
}

step '1 · Examiner les quatre partitions'
discover
printf '  Propriétaire prévu pour la racine et son contenu : %s (UID %s).\n' "$OWNER" "$OWNER_UID"
printf '  Montage automatique au démarrage prévu sous /mnt :\n'
for label in "${LABELS[@]}"; do printf '    /mnt/%s\n' "$label"; done
if [[ "$MODE" == preview ]]; then exit 0; fi
while ! $ALL_OFFLINE; do
    status "$YELLOW" 'Montage' 'Fermer les fichiers ouverts et démonter les volumes signalés depuis le gestionnaire de fichiers.'
    printf '  Entrée pour actualiser, q pour quitter : '
    if ! IFS= read -r answer || [[ "$answer" == [qQ] ]]; then
        printf '  Opération annulée.\n'
        exit 0
    fi
    discover
done
if (( EUID != 0 )); then
    printf '  Continuer vers les vérifications avec sudo ? [o/N] '
    if ! IFS= read -r answer || [[ "$answer" != [oO] && "$answer" != oui ]]; then
        printf '  Opération annulée.\n'
        exit 0
    fi
    command -v sudo >/dev/null || fatal 'Outil manquant : sudo.'
    script_path=$(realpath -e -- "${BASH_SOURCE[0]}") || fatal 'Chemin du script introuvable.'
    exec sudo -- /usr/bin/bash -- "$script_path" --apply
fi

for tool in blkid blockdev chown cmp cp e2label find findfs flock mkdir mktemp mount mountpoint mv realpath rm rmdir sha256sum umount systemctl touch getfacl setfacl getfattr setfattr; do
    command -v "$tool" >/dev/null || fatal "Outil manquant : $tool."
done

require_offline_device() {
    local device="$1" expected_uuid="$2" node="$3" mounted actual_uuid actual_type actual_node read_only
    actual_uuid=$(blkid -p -s UUID -o value -- "$device") ||
        fatal "Impossible de lire l’UUID sur $device."
    [[ "$actual_uuid" == "$expected_uuid" ]] ||
        fatal "UUID inattendu sur $device : $actual_uuid (attendu : $expected_uuid)."
    actual_type=$(blkid -p -s TYPE -o value -- "$device") ||
        fatal "Impossible de lire le type de système de fichiers sur $device."
    [[ "$actual_type" == ext4 ]] || fatal "Type inattendu sur $device : $actual_type (attendu : ext4)."
    # La présentation tabulaire de lsblk ajoute des espaces autour de MAJ:MIN.
    actual_node=$(lsblk --nodeps --noheadings --raw -o MAJ:MIN -- "$device") ||
        fatal "Impossible de lire le numéro de périphérique de $device."
    [[ "$actual_node" == "$node" ]] ||
        fatal "Numéro de périphérique inattendu sur $device : $actual_node (attendu : $node)."
    mounted=$(mounted_device_numbers) ||
        fatal 'Table des montages indisponible.'
    [[ $'\n'"$mounted"$'\n' != *$'\n'"$node"$'\n'* ]] || fatal "$device est monté."
    # Certaines versions de blockdev traitent le séparateur -- comme une commande.
    read_only=$(blockdev --getro "$device") || fatal "Impossible de vérifier l’accès en écriture sur $device."
    [[ "$read_only" == 0 ]] || fatal "$device est en lecture seule."
}

verify_targets() {
    local i
    for i in "${!UUIDS[@]}"; do
        require_offline_device "${DEVICES[i]}" "${UUIDS[i]}" "${NODES[i]}"
    done
}

check_mount_directory() {
    local target="$1" entries
    [[ -d /mnt && ! -L /mnt && ! -L "$target" ]] || fatal "Point de montage redirigé ou parent absent : $target."
    if [[ -e "$target" ]]; then
        [[ -d "$target" ]] || fatal "Le point de montage n’est pas un dossier : $target."
        if mountpoint -q -- "$target"; then fatal "Point de montage déjà utilisé : $target."; fi
        entries=$(find "$target" -mindepth 1 -maxdepth 1 -printf x -quit) ||
            fatal "Impossible de lire $target."
        [[ -z "$entries" ]] || fatal "Point de montage non vide : $target."
    fi
}

plan_boot_mounts() {
    local source target fs options dump pass rest resolved canonical tag i path expected
    local -a present=()
    [[ -f "$FSTAB" && ! -L "$FSTAB" ]] || fatal "$FSTAB doit être un fichier ordinaire."
    FSTAB_BEFORE=$(sha256sum -- "$FSTAB") || fatal "Impossible de lire $FSTAB."
    FSTAB_LINES=()
    while read -r source target fs options dump pass rest || [[ -n "$source" ]]; do
        [[ -n "$source" && "$source" != \#* ]] || continue
        source="${source//\\040/ }"
        target="${target//\\040/ }"
        target="${target//\\011/$'\t'}"
        resolved=''
        tag=''
        case "$source" in
            UUID=*|LABEL=*|PARTUUID=*|PARTLABEL=*)
                tag="${source#*=}"
                if [[ "$tag" == \"*\" || "$tag" == \'*\' ]]; then tag="${tag:1:${#tag}-2}"; fi
                source="${source%%=*}=$tag"
                resolved=$(findfs "$source" 2>/dev/null) || resolved=''
                ;;
            /dev/*) resolved="$source" ;;
        esac
        if [[ -n "$resolved" ]]; then resolved=$(realpath -m -- "$resolved") || fatal "Chemin de périphérique invalide : $resolved."; fi
        canonical="$target"
        if [[ "$target" == /* ]]; then canonical=$(realpath -m -- "$target") || fatal "Chemin fstab invalide : $target."; fi
        for i in "${!UUIDS[@]}"; do
            path="/mnt/${LABELS[i]}"
            expected="UUID=${UUIDS[i]}"
            if [[ "$source" == "$expected" && "$target" == "$path" && "$fs" == ext4 &&
                  "$options" == "$BOOT_MOUNT_OPTIONS" && "$dump" == 0 && "$pass" == 2 &&
                  -z "${present[i]:-}" ]]; then
                present[i]=true
            elif [[ "$source" == "$expected" || "$source" == "LABEL=${LABELS[i]}" ||
                    "$resolved" == "${DEVICES[i]}" || "$canonical" == "$path" ||
                    "$canonical" == "$path/"* || "$path" == "$canonical/"* ]]; then
                fatal "Entrée existante en conflit dans $FSTAB : $source → $target."
            fi
        done
    done < "$FSTAB"
    for i in "${!UUIDS[@]}"; do
        path="/mnt/${LABELS[i]}"
        check_mount_directory "$path"
        if [[ "${present[i]:-}" != true ]]; then
            FSTAB_LINES+=("UUID=${UUIDS[i]} ${path// /\\040} ext4 $BOOT_MOUNT_OPTIONS 0 2")
        fi
    done
    [[ "$(sha256sum -- "$FSTAB")" == "$FSTAB_BEFORE" ]] || fatal "$FSTAB a changé pendant la lecture."
}

step '2 · Confirmer les changements'
verify_targets
plan_boot_mounts
status "$GREEN" 'Prêt' 'Les quatre partitions ext4 sont identifiées par UUID, démontées et accessibles en écriture.'
printf '  Entrées de montage à ajouter dans %s : %s. Un disque absent ne bloque pas le démarrage.\n' "$FSTAB" "${#FSTAB_LINES[@]}"
status "$YELLOW" 'Attention' 'Le changement de propriétaire touche tous les fichiers, y compris les fichiers cachés. Il peut modifier les droits d’accès et effacer certains bits spéciaux ou capacités.'
printf '  Les groupes sont conservés. Un relevé des propriétaires, ACL et capacités précède chaque changement.\n'
printf '  Taper APPLIQUER pour continuer : '
IFS= read -r answer || fatal 'Confirmation interrompue.'
if [[ "$answer" != APPLIQUER ]]; then printf '  Opération annulée.\n'; exit 0; fi

umask 077
exec 9>/run/cachyos-disk-setup.lock || fatal 'Impossible d’ouvrir le verrou.'
flock -n 9 || fatal 'Une autre exécution est déjà en cours.'
# Revalider toutes les cibles avant d’ouvrir la première en écriture.
verify_targets
[[ "$(sha256sum -- "$FSTAB")" == "$FSTAB_BEFORE" ]] || fatal "$FSTAB a changé depuis le plan."

SNAPSHOT=$(mktemp -d /var/tmp/cachy-setup-disques.XXXXXXXX) || fatal 'Création du relevé impossible.'
MOUNT_DIR="$SNAPSHOT/volume"
FSTAB_STAGE=''
FSTAB_INSTALLED=false
CREATED_MOUNT_PATHS=()
cleanup() {
    local result=$? path
    if mountpoint -q -- "$MOUNT_DIR"; then
        if ! umount -- "$MOUNT_DIR"; then
            status "$RED" 'Échec' "Montage encore actif : $MOUNT_DIR." >&2
            result=1
        fi
    fi
    if [[ -d "$MOUNT_DIR" ]] && ! mountpoint -q -- "$MOUNT_DIR"; then rmdir -- "$MOUNT_DIR" || result=1; fi
    if [[ -n "$FSTAB_STAGE" ]]; then rm -f -- "$FSTAB_STAGE" || result=1; fi
    if (( result != 0 )) && ! $FSTAB_INSTALLED; then
        for path in ${CREATED_MOUNT_PATHS[@]+"${CREATED_MOUNT_PATHS[@]}"}; do rmdir -- "$path" || result=1; done
    fi
    printf '  Relevé et journal : %s\n' "$SNAPSHOT"
    exit "$result"
}
trap cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' TERM
mkdir -- "$MOUNT_DIR"
printf 'État\tUUID\tPériphérique\tLabel prévu\n' > "$SNAPSHOT/journal.tsv"

for label in "${LABELS[@]}"; do
    path="/mnt/$label"
    check_mount_directory "$path"
    if [[ ! -d "$path" ]]; then
        mkdir -m 0755 -- "$path" || fatal "Impossible de créer $path."
        CREATED_MOUNT_PATHS+=("$path")
    fi
done
if (( ${#FSTAB_LINES[@]} > 0 )); then
    cp --preserve=all -- "$FSTAB" "$SNAPSHOT/fstab.avant" || fatal "Sauvegarde de $FSTAB impossible."
    [[ "$(sha256sum -- "$FSTAB")" == "$FSTAB_BEFORE" ]] &&
        cmp -s -- "$FSTAB" "$SNAPSHOT/fstab.avant" || fatal "$FSTAB a changé depuis le plan."
    FSTAB_STAGE=$(mktemp /etc/.cachyos-fstab.XXXXXXXX) || fatal 'Préparation du fichier fstab impossible.'
    cp --preserve=all -- "$SNAPSHOT/fstab.avant" "$FSTAB_STAGE" || fatal 'Copie du fichier fstab impossible.'
    printf '\n# CachyOS : volumes secondaires\n%s\n' "${FSTAB_LINES[@]}" >> "$FSTAB_STAGE" ||
        fatal 'Écriture du fichier fstab préparé impossible.'
    findmnt --verify --tab-file "$FSTAB_STAGE" > "$SNAPSHOT/fstab.verification" 2>&1 ||
        fatal "Le fichier fstab préparé a échoué à la vérification. Voir $SNAPSHOT/fstab.verification."
fi

for i in "${!UUIDS[@]}"; do
    uuid="${UUIDS[i]}" device="${DEVICES[i]}" label="${LABELS[i]}" node="${NODES[i]}"
    step "3 · Traiter $label ($device)"
    require_offline_device "$device" "$uuid" "$node"
    old_label=$(e2label "$device") || fatal "Lecture du label de $device impossible."
    printf '%s\n' "$old_label" > "$SNAPSHOT/$uuid.label"
    mount -t ext4 -o nosuid,nodev,noexec -- "$device" "$MOUNT_DIR" ||
        fatal "Montage temporaire impossible : $device."
    mount_identity=$(findmnt --kernel --noheadings --raw --mountpoint "$MOUNT_DIR" -o MAJ:MIN,FSTYPE,FSROOT) ||
        fatal 'Identité du montage temporaire indisponible.'
    [[ "$mount_identity" == "$node ext4 /" ]] || fatal 'Le montage temporaire ne correspond pas au volume attendu.'

    # Relevé des entrées qui changent : UID, GID, mode, inode et chemin relatif,
    # avec séparateurs NUL pour conserver aussi les caractères spéciaux.
    status "$CYAN" 'Relevé' 'Lecture des propriétaires sur ce volume.'
    find -P "$MOUNT_DIR" -xdev ! -uid "$OWNER_UID" -printf '%U\0%G\0%m\0%i\0%P\0' > "$SNAPSHOT/$uuid.proprietaires" ||
        fatal "Relevé des propriétaires incomplet pour $label."
    # Sauvegarder les ACL, propriétaires, modes et capacités : chown peut
    # retirer des bits spéciaux et security.capability. Ne suivre aucun lien.
    getfacl -R -P -p -n -- "$MOUNT_DIR" > "$SNAPSHOT/$uuid.acl" ||
        fatal "Sauvegarde ACL incomplète pour $label."
    getfattr -R -h -d -m '^security.capability$' --absolute-names -- "$MOUNT_DIR" > "$SNAPSHOT/$uuid.capabilities" ||
        fatal "Sauvegarde des capacités incomplète pour $label."
    printf '%s\n' "$MOUNT_DIR" > "$SNAPSHOT/$uuid.mount-path"
    touch "$SNAPSHOT/$uuid.metadata-complete"
    if [[ -s "$SNAPSHOT/$uuid.proprietaires" ]]; then
        printf 'Propriété en cours\t%s\t%s\t%s\n' "$uuid" "$device" "$label" >> "$SNAPSHOT/journal.tsv"
        status "$CYAN" 'Propriété' "Attribution des entrées concernées à $OWNER."
        find -P "$MOUNT_DIR" -xdev ! -uid "$OWNER_UID" -execdir chown -h -- "+$OWNER_UID" '{}' + ||
            fatal "Changement de propriétaire incomplet pour $label. Voir le relevé."
    else
        status "$GREEN" 'Propriété' "Toutes les entrées appartiennent déjà à $OWNER."
    fi
    remaining=$(find -P "$MOUNT_DIR" -xdev ! -uid "$OWNER_UID" -print -quit) ||
        fatal "Vérification de la propriété impossible pour $label."
    [[ -z "$remaining" ]] || fatal "Une entrée appartient encore à un autre compte : $remaining."
    umount -- "$MOUNT_DIR" || fatal "Démontage temporaire impossible : $device."

    require_offline_device "$device" "$uuid" "$node"
    if [[ "$old_label" != "$label" ]]; then
        e2label "$device" "$label" || fatal "Impossible d’appliquer le label « $label »."
    fi
    [[ "$(e2label "$device")" == "$label" ]] || fatal "Le label final de $device est inattendu."
    printf 'Vérifié\t%s\t%s\t%s\n' "$uuid" "$device" "$label" >> "$SNAPSHOT/journal.tsv"
    status "$GREEN" 'Vérifié' "Label « $label » et propriétaire $OWNER."
done

step '4 · Activer le montage au démarrage et afficher le bilan'
if [[ -n "$FSTAB_STAGE" ]]; then
    [[ -f "$FSTAB" && ! -L "$FSTAB" && "$(sha256sum -- "$FSTAB")" == "$FSTAB_BEFORE" ]] ||
        fatal "$FSTAB a changé. Le fichier existant est conservé."
    for label in "${LABELS[@]}"; do check_mount_directory "/mnt/$label"; done
    FSTAB_INSTALLED=true
    if ! mv -T -- "$FSTAB_STAGE" "$FSTAB"; then
        FSTAB_INSTALLED=false
        fatal "Impossible de mettre à jour $FSTAB."
    fi
    FSTAB_STAGE=''
fi
# Recharger les unités générées par fstab, sans monter les quatre volumes.
if $FSTAB_INSTALLED; then systemctl daemon-reload || fatal 'Rechargement systemd échoué ; consulter le relevé.'; fi
status "$GREEN" 'Terminé' "${#UUIDS[@]} volumes vérifiés. Le montage automatique prendra effet au prochain démarrage."
