#!/usr/bin/env bash
# Préparation pour CachyOS ; consulter docs/noctalia.md avant --apply.
set -Eeuo pipefail

MODE=plan
REPLACE=0
# Français (Canada) : disposition ca, sans variante supplémentaire.
KEYBOARD=ca
VARIANT=
BACKUP=
STAGE=
REPO_ROOT=$(cd -- "$(dirname -- "${BASH_SOURCE[0]:-$0}")/.." && pwd)
CONFIG_ITEMS=(umbriel noctalia kitty xdg-desktop-portal mimeapps.list)
USER_UNITS=(pipewire.socket pipewire-pulse.socket wireplumber.service gnome-keyring-daemon.socket)
# Paquets demandés explicitement, regroupés par fonction. Les dépendances
# supplémentaires restent résolues par pacman pendant la transaction.
PACKAGES_DESKTOP=(umbriel noctalia)
PACKAGES_LOGIN=(greetd noctalia-greeter)
PACKAGES_APPLICATIONS=(kitty firefox firefox-i18n-fr thunar micro zed papers loupe mpv)
PACKAGES_AUDIO=(pipewire pipewire-audio pipewire-pulse pipewire-alsa wireplumber pavucontrol)
PACKAGES_NETWORK=(networkmanager)
PACKAGES_SECRETS=(gnome-keyring seahorse)
PACKAGES_INTEGRATION=(dbus polkit xorg-xwayland xdg-utils wl-clipboard)
PACKAGES_FILES=(gvfs gvfs-smb gvfs-mtp tumbler ffmpegthumbnailer thunar-archive-plugin thunar-volman xarchiver zip unzip)
PACKAGES_PORTALS=(xdg-desktop-portal xdg-desktop-portal-umbriel xdg-desktop-portal-gtk)
PACKAGES_HARDWARE=(brightnessctl upower)
PACKAGES_APPEARANCE=(ttf-dejavu ttf-liberation ttf-jetbrains-mono-nerd noto-fonts-emoji adwaita-icon-theme)
PACKAGES_SETUP=(python)

# Une seule transaction conserve la mise à jour complète et la résolution
# cohérente des dépendances, quelle que soit la catégorie d'affichage.
REPO_PACKAGES=(
  "${PACKAGES_DESKTOP[@]}" "${PACKAGES_LOGIN[@]}"
  "${PACKAGES_APPLICATIONS[@]}" "${PACKAGES_AUDIO[@]}"
  "${PACKAGES_NETWORK[@]}" "${PACKAGES_SECRETS[@]}"
  "${PACKAGES_INTEGRATION[@]}" "${PACKAGES_FILES[@]}"
  "${PACKAGES_PORTALS[@]}" "${PACKAGES_HARDWARE[@]}"
  "${PACKAGES_APPEARANCE[@]}" "${PACKAGES_SETUP[@]}"
)
REPO_TARGETS=()
PACKAGE_SOURCES=()
BLOCKERS=()

die() {
  printf 'Erreur : %s\n' "$*" >&2
  [[ -z $BACKUP ]] || printf 'Sauvegarde et retour arrière : %s ; voir docs/noctalia.md.\n' "$BACKUP" >&2
  exit 1
}
help_text() {
  cat <<'EOF'
Usage : bash scripts/umbriel_setup.sh [options]
Cible : CachyOS installé avec l'option No Desktop, puis démarré sur le disque.
  --plan                 Aperçu sans modification (défaut, sans sudo ni réseau).
  --apply                Installer/configurer après confirmation interactive.
  --replace-config       Autoriser le remplacement des configurations existantes
                         des profils gérés et des réglages GUI Noctalia sauvegardés.
  --keyboard CODE        Disposition XKB de la session et de Greeter (défaut : ca).
  --variant CODE         Variante XKB (défaut : vide, Français Canada ; multix pour CSA).
  --print-config         Afficher les fichiers locaux, puis sortir (Python 3).
                         Kitty est récupéré depuis CachyOS/main seulement en --apply.
  -h, --help             Afficher cette aide.
Ne pas lancer avec sudo. Aucun redémarrage ni lancement du greeter automatique.
Guide, limites et restauration : docs/noctalia.md
EOF
}
while (($#)); do
  case "$1" in
    --plan|--apply|--print-config) MODE=${1#--}; shift ;;
    --replace-config) REPLACE=1; shift ;;
    --keyboard|--variant)
      (($# >= 2)) || die "Valeur manquante pour $1"
      case "$1" in
        --keyboard) KEYBOARD=$2 ;;
        --variant) VARIANT=$2 ;;
      esac
      shift 2 ;;
    -h|--help) help_text; exit 0 ;;
    *) die "Option inconnue : $1" ;;
  esac
done
[[ $KEYBOARD =~ ^[a-zA-Z0-9_-]+$ ]] || die 'Disposition XKB invalide'
[[ $VARIANT =~ ^[a-zA-Z0-9_-]*$ ]] || die 'Variante XKB invalide'
if [[ $MODE == print-config ]]; then
  python3 -B "$REPO_ROOT/scripts/noctalia_dotfiles.py" --print --keyboard "$KEYBOARD" --variant "$VARIANT"
  exit 0
fi

CONFIG_HOME=${XDG_CONFIG_HOME:-$HOME/.config}
STATE_HOME=${XDG_STATE_HOME:-$HOME/.local/state}
validate_personal_paths() {
  local path
  for path in "$HOME" "$CONFIG_HOME" "$STATE_HOME"; do
    [[ $path == /* && $path != / && $path != */ ]] || die 'Chemins personnels absolus requis, sans barre finale'
    # Refuser les formes ambiguës avant le contrôle de confinement. Les liens
    # symboliques sont ensuite contrôlés par realpath dans preflight.
    case "$path/" in
      *'/../'*|*'/./'*|*'//'*) die 'Chemins personnels non normalisés : composants . ou .. et doubles barres interdits' ;;
    esac
  done
  [[ $CONFIG_HOME == "$HOME/"* && $STATE_HOME == "$HOME/"* ]] || die 'Les dossiers XDG doivent se trouver sous le dossier personnel pour cette procédure.'
  [[ $CONFIG_HOME != "$STATE_HOME" && $CONFIG_HOME != "$STATE_HOME/"* && $STATE_HOME != "$CONFIG_HOME/"* ]] || die 'Les dossiers XDG de configuration et d’état doivent être distincts et sans imbrication'
}
validate_personal_paths
USER_CONFIG=$CONFIG_HOME/umbriel/config.toml
GUI_SETTINGS=$STATE_HOME/noctalia/settings.toml

# Le remplacement déplace les profils complets afin qu'aucun ancien module
# ne se mélange à la nouvelle configuration. Le dossier de sauvegarde est privé.
install_user_dotfiles() {
  local prepared=$1 item destination
  mkdir -p -- "$CONFIG_HOME"
  sudo install -d -m 0700 "$BACKUP/replaced-user"
  for item in "${CONFIG_ITEMS[@]}"; do
    destination=$CONFIG_HOME/$item
    if [[ -e $destination || -L $destination ]]; then
      sudo mv -- "$destination" "$BACKUP/replaced-user/$item"
    fi
    cp -R -- "$prepared/user/$item" "$destination"
  done
  # Les modifications GUI ont priorité sur les modules : les conserver hors
  # du chemin actif, après sauvegarde, pour appliquer réellement le nouveau profil.
  if [[ -e $GUI_SETTINGS ]]; then
    sudo mv -- "$GUI_SETTINGS" "$BACKUP/noctalia-settings-replaced.toml"
  fi
}

validate_profiles() {
  local config_root=$1 log_directory=$2 backup_name=$3 status=0
  python3 -B "$REPO_ROOT/scripts/noctalia_dotfiles.py" --check-native "$config_root" --logs "$log_directory" || status=$?
  # Conserver aussi les diagnostics d'échec avant le nettoyage du temporaire.
  if [[ -d $log_directory ]]; then
    sudo cp -a -- "$log_directory" "$BACKUP/$backup_name"
  fi
  ((status == 0)) || die "Validation interrompue ; consulter $BACKUP/$backup_name avant de poursuivre."
}

# Résolution par pacman uniquement, dans l'ordre des dépôts configurés.
# Les cibles dépôt/paquet conservent cette provenance pendant la transaction.
resolve_packages() {
  REPO_TARGETS=()
  PACKAGE_SOURCES=()
  local pkg metadata repository version field value
  for pkg in "${REPO_PACKAGES[@]}"; do
    if ! metadata=$(LC_ALL=C pacman -Si "$pkg" 2>/dev/null); then
      BLOCKERS+=("Paquet absent des bases locales : $pkg ; vérifier les dépôts CachyOS/Arch et leurs métadonnées. Aucun recours à l'AUR.")
      continue
    fi
    repository=
    version=
    while IFS=: read -r field value; do
      case "${field// /}" in
        Repository)
          [[ -z $repository ]] || break
          read -r repository <<< "$value" ;;
        Version) read -r version <<< "$value" ;;
      esac
    done <<< "$metadata"
    if [[ ! $repository =~ ^[a-zA-Z0-9_.-]+$ || -z $version ]]; then
      BLOCKERS+=("Provenance ou version illisible pour $pkg ; installation refusée.")
      continue
    fi
    REPO_TARGETS+=("$repository/$pkg")
    PACKAGE_SOURCES+=("$pkg | $repository | $version")
  done
}

check_network_backend() {
  local unit state rest active_instances
  # Ne pas activer NetworkManager à côté d'un gestionnaire déjà en service.
  # Aucune connexion, aucun service actif n'est modifié par ce diagnostic.
  for unit in systemd-networkd.service connman.service dhcpcd.service; do
    if systemctl is-active --quiet "$unit"; then
      BLOCKERS+=("Gestionnaire réseau actif : $unit ; migration vers NetworkManager à préparer séparément.")
    fi
  done
  # Une instance lancée manuellement peut être active sans être activée pour
  # le prochain démarrage ; list-unit-files ne suffit pas à la détecter.
  if active_instances=$(systemctl list-units --all --plain --no-legend --no-pager --state=active,activating 'dhcpcd@*.service' 2>/dev/null); then
    while read -r unit rest; do
      [[ -n $unit ]] || continue
      BLOCKERS+=("Gestionnaire réseau actif : $unit ; migration vers NetworkManager à préparer séparément.")
    done <<< "$active_instances"
  else
    BLOCKERS+=("Impossible de vérifier les instances dhcpcd actives ; diagnostic réseau incomplet.")
  fi
  while read -r unit state rest; do
    case "$state" in
      enabled|enabled-runtime|linked|linked-runtime)
        BLOCKERS+=("Autre gestionnaire réseau activé : $unit ; migration à préparer séparément.") ;;
    esac
  done < <(systemctl list-unit-files --no-legend --no-pager 'systemd-networkd.service' 'connman.service' 'dhcpcd*.service' 2>/dev/null || true)
  if ! systemctl is-active --quiet NetworkManager.service && systemctl is-active --quiet iwd.service; then
    BLOCKERS+=("iwd actif sans NetworkManager ; vérifier la gestion Wi-Fi existante avant toute migration.")
  fi
}

# Aucun appel privilégié ni rafraîchissement de base dans ce diagnostic.
preflight() {
  BLOCKERS=()
  REPO_TARGETS=()
  PACKAGE_SOURCES=()
  if [[ $(uname -s) != Linux ]] || [[ ! -r /etc/os-release ]]; then
    BLOCKERS+=("Cible requise : CachyOS installé avec No Desktop, démarré hors de l'ISO.")
    return
  fi
  # os-release est un fichier système de confiance, jamais un fichier téléchargé.
  local ID= ID_LIKE=
  source /etc/os-release
  [[ $ID == cachyos ]] || BLOCKERS+=("Distribution détectée : $ID ; CachyOS requis.")
  [[ ! -d /run/archiso ]] || BLOCKERS+=("L'environnement live ISO n'est pas pris en charge.")
  ((EUID != 0)) || BLOCKERS+=("Exécuter en utilisateur ordinaire, sans sudo.")
  [[ -z ${DISPLAY:-} && -z ${WAYLAND_DISPLAY:-} ]] || BLOCKERS+=("Quitter la session graphique et utiliser une TTY locale.")
  local tool pkg session manager
  for tool in pacman systemctl sudo realpath getent; do
    command -v "$tool" >/dev/null || BLOCKERS+=("Outil requis absent : $tool")
  done
  [[ -d /run/systemd/system ]] || BLOCKERS+=("systemd doit être démarré.")
  [[ -d $REPO_ROOT/dotfiles/user/umbriel && -r $REPO_ROOT/scripts/noctalia_dotfiles.py && -r $REPO_ROOT/scripts/kitty_source.py && -r $REPO_ROOT/scripts/profiles.py ]] ||
    BLOCKERS+=("Modules dotfiles ou outil de préparation absents du dépôt.")
  [[ -z ${NOCTALIA_CONFIG_HOME:-} || $NOCTALIA_CONFIG_HOME == "$CONFIG_HOME" ]] ||
    BLOCKERS+=("NOCTALIA_CONFIG_HOME redirige la configuration hors du profil prévu.")
  [[ -z ${NOCTALIA_STATE_HOME:-} || $NOCTALIA_STATE_HOME == "$STATE_HOME" ]] ||
    BLOCKERS+=("NOCTALIA_STATE_HOME redirige les réglages hors du profil prévu.")
  local cards=(/dev/dri/card*)
  [[ -e ${cards[0]} ]] || BLOCKERS+=("Aucun périphérique graphique /dev/dri/card* ; vérifier les pilotes.")
  if command -v systemctl >/dev/null; then
    check_network_backend
    systemctl --user show-environment >/dev/null 2>&1 || BLOCKERS+=("Gestionnaire systemd utilisateur indisponible pour l'audio.")
    manager=$(systemctl show display-manager.service -p Id --value 2>/dev/null || true)
    [[ -z $manager || $manager == display-manager.service || $manager == greetd.service ]] ||
      BLOCKERS+=("Gestionnaire de connexion existant : $manager ; migration hors périmètre.")
    for manager in display-manager greetd gdm sddm lightdm lxdm ly; do
      if systemctl is-active --quiet "$manager.service"; then
        BLOCKERS+=("Service graphique actif : $manager.service")
      elif [[ $manager != greetd && $manager != display-manager ]] && systemctl is-enabled --quiet "$manager.service" 2>/dev/null; then
        BLOCKERS+=("Autre gestionnaire activé : $manager.service")
      fi
    done
  fi
  for session in /usr/share/wayland-sessions/*.desktop /usr/share/xsessions/*.desktop; do
    [[ -e $session ]] || continue
    [[ ${session##*/} == umbriel.desktop ]] || BLOCKERS+=("Session déjà installée : $session")
  done
  for pkg in "$CONFIG_HOME/mimeapps.list" "$GUI_SETTINGS" /etc/greetd/config.toml; do
    if [[ -e $pkg && ! -f $pkg ]]; then
      BLOCKERS+=("Un fichier ordinaire est attendu : $pkg")
    fi
    if [[ -e $pkg || -L $pkg ]] && ((REPLACE == 0)); then
      BLOCKERS+=("Configuration existante : $pkg ; examiner puis utiliser --replace-config si voulu.")
    fi
  done
  for pkg in "${CONFIG_ITEMS[@]}"; do
    pkg=$CONFIG_HOME/$pkg
    if [[ -e $pkg || -L $pkg ]] && ((REPLACE == 0)); then
      BLOCKERS+=("Profil existant : $pkg ; examiner puis utiliser --replace-config si voulu.")
    fi
  done
  for pkg in "$CONFIG_HOME" "$STATE_HOME" "$STATE_HOME/noctalia" "$CONFIG_HOME/umbriel" "$CONFIG_HOME/noctalia" "$CONFIG_HOME/kitty" "$CONFIG_HOME/xdg-desktop-portal" /etc/greetd /var/lib/noctalia-greeter; do
    [[ ! -e $pkg || -d $pkg ]] || BLOCKERS+=("Un répertoire est attendu : $pkg")
  done
  # Refuser les redirections de chemins, y compris via un parent symbolique.
  if command -v realpath >/dev/null; then
    for pkg in "$HOME" "$CONFIG_HOME" "$STATE_HOME" "$GUI_SETTINGS" "$CONFIG_HOME/umbriel" "$CONFIG_HOME/noctalia" "$CONFIG_HOME/kitty" "$CONFIG_HOME/xdg-desktop-portal" "$CONFIG_HOME/mimeapps.list" /etc/greetd /etc/greetd/config.toml /var/lib/noctalia-greeter; do
      [[ $(realpath -m -s -- "$pkg") == "$(realpath -m -- "$pkg")" ]] || BLOCKERS+=("Lien symbolique dans le chemin : $pkg")
    done
  fi
  if command -v pacman >/dev/null; then
    resolve_packages
  fi
}
show_package_category() {
  local title=$1 purpose=$2
  shift 2
  printf '\n%s — %s\n' "$title" "$purpose"
  printf '  %s\n' "$*"
}
show_package_categories() {
  printf '\nPaquets prévus par catégorie (toutes les catégories sont installées) :\n'
  show_package_category 'Bureau Wayland' 'Compositeur et interface du bureau.' "${PACKAGES_DESKTOP[@]}"
  show_package_category 'Écran de connexion' 'Service de connexion et interface Greeter.' "${PACKAGES_LOGIN[@]}"
  show_package_category 'Applications' 'Terminal, Firefox avec langue française, fichiers, Micro, Zed, PDF avec Papers, images avec Loupe et médias avec mpv.' "${PACKAGES_APPLICATIONS[@]}"
  show_package_category 'Audio' 'Serveur audio, compatibilité PulseAudio/ALSA, périphériques et réglages détaillés avec Pavucontrol.' "${PACKAGES_AUDIO[@]}"
  show_package_category 'Réseau' 'Contrôles réseau de Noctalia via NetworkManager ; connexions conservées.' "${PACKAGES_NETWORK[@]}"
  show_package_category 'Trousseau de secrets' 'Stockage chiffré et interface de gestion des clés.' "${PACKAGES_SECRETS[@]}"
  show_package_category 'Intégration du bureau' 'Communication, autorisations, applications X11, ouverture des fichiers et presse-papiers.' "${PACKAGES_INTEGRATION[@]}"
  show_package_category 'Services de fichiers' 'Corbeille, volumes, partages SMB, appareils MTP, miniatures vidéo et archives (dont ZIP).' "${PACKAGES_FILES[@]}"
  show_package_category 'Portails XDG' 'Partage d’écran, captures et dialogues pour les applications.' "${PACKAGES_PORTALS[@]}"
  show_package_category 'Matériel' 'Contrôle de luminosité et informations de batterie/alimentation.' "${PACKAGES_HARDWARE[@]}"
  show_package_category 'Polices et icônes' 'Texte, Liberation, JetBrainsMono Nerd Font pour Kitty, emojis et icônes.' "${PACKAGES_APPEARANCE[@]}"
  show_package_category 'Préparation des configurations' 'Génération et validation TOML des modules.' "${PACKAGES_SETUP[@]}"
  printf '\n'
}
show_plan() {
  printf 'Installation prévue après le choix No Desktop dans CachyOS ; paquets des dépôts uniquement.\n'
  printf 'Cible : %s ; session détectée : %s\n' "$(uname -s)" "${XDG_CURRENT_DESKTOP:-aucune déclarée}"
  printf 'Compte : %s ; configuration : %s\n' "$(id -un)" "$USER_CONFIG"
  printf 'Clavier Umbriel et Greeter : %s / %s\n' "$KEYBOARD" "${VARIANT:-défaut}"
  printf 'Profils personnels gérés (Kitty depuis le dépôt CachyOS, les autres depuis dotfiles/user) : %s\n' "${CONFIG_ITEMS[*]}"
  printf 'Source Kitty : https://github.com/Masternaka/CachyOS ; branche main ; dossier Dotfiles/kitty/.config/kitty.\n'
  printf 'Après confirmation : récupération de main, commit enregistré, contrôle des inclusions et adaptation des chemins dans les copies.\n'
  printf 'Aucun téléchargement Kitty pendant --plan ou --print-config ; échec de récupération = arrêt avant remplacement des profils.\n'
  show_package_categories
  if ((${#PACKAGE_SOURCES[@]})); then
    printf 'Provenance selon les bases locales : paquet | dépôt | version\n'
    printf ' %s\n' "${PACKAGE_SOURCES[@]}"
    printf 'Mise à jour complète et installation : sudo pacman -Syu --needed'
    printf ' %q' "${REPO_TARGETS[@]}"; printf '\n'
  else
    printf 'La provenance des paquets sera résolue sur CachyOS.\n'
  fi
  cat <<EOF
Sauvegarde privée : /var/lib/cachy-setup/noctalia-<date>-<identifiant>/
Remplacement des profils gérés sous $CONFIG_HOME et de /etc/greetd/config.toml.
Sauvegarde et retrait des réglages GUI prioritaires : $GUI_SETTINGS (si présents).
Assemblage des modules de Greeter dans /var/lib/noctalia-greeter/greeter.toml.
Greeter 1.7.0 minimum requis pour l'horloge : heure sur 24 heures et date au-dessus du panneau.
Activation audio et socket du trousseau pour le compte courant : ${USER_UNITS[*]} (sans --now).
Activation de NetworkManager au prochain démarrage, sans arrêt du réseau actuel.
Activation de greetd au prochain démarrage, sans --now ; cible graphical.target.
Ni pilotes GPU, ni modification des connexions réseau, ni Bluetooth, ni PAM personnalisé.
Trousseau : sa création et son déverrouillage restent interactifs ; aucun mot de passe stocké par le script.
Le portail Umbriel est inclus depuis les dépôts ; son fonctionnement reste à tester.
Les transactions de paquets et leurs hooks peuvent créer des comptes/fichiers système.
EOF
  if ((${#BLOCKERS[@]})); then printf 'Points bloquants :\n'; printf ' - %s\n' "${BLOCKERS[@]}"; fi
}
preflight
show_plan
[[ $MODE == apply ]] || exit 0
((${#BLOCKERS[@]} == 0)) || die 'Corriger les points bloquants avant application.'
[[ -t 0 && -t 1 && -z ${SSH_CONNECTION:-} ]] || die 'Une console TTY locale interactive est requise.'
[[ $(tty) == /dev/tty[0-9]* ]] || die 'Lancer depuis une console virtuelle locale (ex. Ctrl+Alt+F3).'
printf 'Pour autoriser ces changements et la mise à jour complète, saisir INSTALLER : '
read -r answer
[[ $answer == INSTALLER ]] || die 'Installation annulée.'
# Revalider juste avant la première écriture.
preflight
((${#BLOCKERS[@]} == 0)) || { show_plan; die 'La situation a changé.'; }
sudo -v
sudo install -d -m 0700 /var/lib/cachy-setup
BACKUP=$(sudo mktemp -d /var/lib/cachy-setup/noctalia-"$(date +%Y%m%d-%H%M%S)"-XXXXXX)
trap 'printf "Interruption/échec. État potentiellement partiel ; sauvegarde : %s. Voir docs/noctalia.md.\n" "$BACKUP" >&2' ERR
printf 'Sauvegarde : %s\n' "$BACKUP"
pacman -Q | sudo tee "$BACKUP/packages-before.txt" >/dev/null
printf '%s\n' "${PACKAGE_SOURCES[@]}" | sudo tee "$BACKUP/package-sources.txt" >/dev/null
systemctl is-enabled greetd.service 2>/dev/null | sudo tee "$BACKUP/greetd-enabled-before.txt" >/dev/null || true
systemctl get-default | sudo tee "$BACKUP/default-target-before.txt" >/dev/null
systemctl is-enabled NetworkManager.service 2>/dev/null | sudo tee "$BACKUP/NetworkManager.service.before" >/dev/null || true
for unit in "${USER_UNITS[@]}"; do
  systemctl --user is-enabled "$unit" 2>/dev/null | sudo tee "$BACKUP/$unit.before" >/dev/null || true
done
sudo install -d -m 0700 "$BACKUP/user"
printf 'CONFIG_HOME=%s\nSTATE_HOME=%s\n' "$CONFIG_HOME" "$STATE_HOME" | sudo tee "$BACKUP/paths.txt" >/dev/null
for item in "${CONFIG_ITEMS[@]}"; do
  if [[ -e $CONFIG_HOME/$item ]]; then
    sudo cp -a -- "$CONFIG_HOME/$item" "$BACKUP/user/$item"
  else
    printf 'absent\n' | sudo tee "$BACKUP/user/$item.absent" >/dev/null
  fi
done
for entry in greetd greeter-state noctalia-settings; do
  case "$entry" in
    greetd) path=/etc/greetd ;;
    greeter-state) path=/var/lib/noctalia-greeter ;;
    noctalia-settings) path=$GUI_SETTINGS ;;
  esac
  if sudo test -e "$path"; then
    sudo cp -a -- "$path" "$BACKUP/$entry"
  else
    printf '%s\n' absent | sudo tee "$BACKUP/$entry.absent" >/dev/null
  fi
done
sudo pacman -Syu --needed "${REPO_TARGETS[@]}"
# Lecture de la base installée uniquement ; refuser une ancienne version avant
# toute copie d'un profil contenant les réglages d'horloge apparus en 1.7.0.
pacman -T 'noctalia-greeter>=1.7.0' >/dev/null || die 'Greeter 1.7.0 minimum requis pour la section clock ; configurations non remplacées.'
for tool in umbriel start-umbriel noctalia noctalia-greeter-session noctalia-greeter-apply-appearance kitty kitten firefox thunar micro zeditor papers loupe mpv xarchiver zip unzip pavucontrol ffmpegthumbnailer python3 wl-copy brightnessctl nmcli gnome-keyring-daemon seahorse; do
  [[ -x /usr/bin/$tool ]] || die "Exécutable du paquet absent : /usr/bin/$tool ; greetd non activé."
done
# Recharger uniquement les définitions d'unités, sans démarrer de service.
systemctl --user daemon-reload
for unit in umbriel.service umbriel-session.target umbriel-shutdown.target "${USER_UNITS[@]}"; do
  systemctl --user cat "$unit" >/dev/null || die "Unité utilisateur du paquet absente : $unit"
done
[[ $(systemctl --user show umbriel.service -p Type --value) == notify ]] || die 'umbriel.service doit assurer la synchronisation Type=notify des portails.'
python3 -B "$REPO_ROOT/scripts/noctalia_dotfiles.py" --check-pam-root /etc/pam.d
getent passwd greeter >/dev/null || die 'Compte système greeter absent ; vérifier les paquets.'
[[ -f /usr/share/wayland-sessions/umbriel.desktop ]] || die 'Session Umbriel du paquet absente.'
for desktop in firefox.desktop thunar.desktop dev.zed.Zed.desktop org.gnome.Papers.desktop org.gnome.Loupe.desktop mpv.desktop; do
  [[ -f /usr/share/applications/$desktop ]] || die "Identifiant d'application absent : $desktop ; associations non appliquées."
done
# Préparer et vérifier les modules avant de remplacer les configurations actives.
STAGE=$(mktemp -d "${TMPDIR:-/tmp}/cachy-noctalia.XXXXXX")
trap '[[ -z $STAGE ]] || rm -rf -- "$STAGE"' EXIT
python3 -B "$REPO_ROOT/scripts/noctalia_dotfiles.py" --keyboard "$KEYBOARD" --variant "$VARIANT" --fetch-kitty --check --output "$STAGE/rendered"
sudo cp -a -- "$STAGE/rendered/system/kitty-source.json" "$BACKUP/kitty-source.json"
validate_profiles "$STAGE/rendered/user" "$STAGE/validation-before-copy" validation-before-copy
sudo cp -a -- "$STAGE/rendered" "$BACKUP/proposed"
if ((REPLACE)); then
  python3 -B "$REPO_ROOT/scripts/profiles.py" compare "$STAGE/rendered/user"
  printf 'Les paquets ont déjà été traités. Pour remplacer les profils affichés et Greeter après sauvegarde, saisir REMPLACER : '
  read -r answer
  [[ $answer == REMPLACER ]] || die 'Remplacement annulé ; les profils sont conservés, la transaction de paquets reste effectuée.'
fi
install_user_dotfiles "$STAGE/rendered"
validate_profiles "$CONFIG_HOME" "$STAGE/validation-installed" validation-installed
sudo install -d -m 0755 /etc/greetd
sudo install -m 0644 "$STAGE/rendered/system/greetd.toml" /etc/greetd/config.toml
sudo env GREETER_USER=greeter /usr/bin/noctalia-greeter-apply-appearance --setup-system
sudo install -o greeter -g "$(id -gn greeter)" -m 0600 "$STAGE/rendered/system/greeter.toml" /var/lib/noctalia-greeter/greeter.toml
systemctl --user enable "${USER_UNITS[@]}"
for unit in "${USER_UNITS[@]}"; do
  systemctl --user is-enabled --quiet "$unit" || die "Activation utilisateur non confirmée : $unit"
done
sudo systemctl enable NetworkManager.service
systemctl is-enabled --quiet NetworkManager.service || die 'Activation de NetworkManager non confirmée.'
sudo systemctl enable greetd.service
systemctl is-enabled --quiet greetd.service || die 'Activation de greetd non confirmée.'
sudo systemctl set-default graphical.target
[[ $(systemctl get-default) == graphical.target ]] || die 'Cible graphique non confirmée.'
pacman -Q | sudo tee "$BACKUP/packages-after.txt" >/dev/null
trap - ERR
printf 'Préparation terminée. Sauvegarde : %s\n' "$BACKUP"
printf 'Vous pouvez tester start-umbriel depuis cette TTY, puis redémarrer manuellement.\n'
printf 'Au prochain démarrage, choisir Umbriel dans Greeter. Vérifications : docs/noctalia.md\n'
