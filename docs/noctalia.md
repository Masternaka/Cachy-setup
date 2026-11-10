# Installer Noctalia, Umbriel et Greeter sur CachyOS

Le script [umbriel_setup.sh](../scripts/umbriel_setup.sh) s'utilise **après avoir installé CachyOS avec le choix « No Desktop »**, puis redémarré sur le disque et ouvert une session en console. Il installe ensuite le bureau Wayland demandé, ses applications de base, NetworkManager et le trousseau de secrets. Le système de base, les pilotes et un accès Internet doivent déjà fonctionner. La [vérification documentaire du 10 novembre 2026](verification-noctalia-2026-11-10.md) explique les recommandations suivies et les limites des contrôles.

## Choix de version et provenance

Références consultées le 10 novembre 2026 :

- [Noctalia](https://noctalia.dev/) et [installation actuelle](https://docs.noctalia.dev/noctalia/getting-started/installation/) : le bureau actuel est Noctalia v5, paquet `noctalia`. L'ancien Shell v4 basé sur Quickshell est archivé ; ce script cible v5.
- [Installation Umbriel](https://docs.noctalia.dev/umbriel/installation/) : démarrage avec `start-umbriel`. Pour les paquets, le catalogue CachyOS ci-dessous prévaut sur les instructions génériques Arch/AUR.
- [Installation Greeter](https://docs.noctalia.dev/greeter/installation/) : paquet `noctalia-greeter` disponible pour CachyOS ; greetd lance son wrapper de session.
- [Intégration du bureau](https://docs.noctalia.dev/noctalia/compositor-settings/umbriel/) et [configuration Umbriel](https://docs.noctalia.dev/umbriel/configuration/) pour l'autostart et les fichiers TOML.
- [Installation CachyOS](https://wiki.cachyos.org/installation/installation_on_root/) et [après installation](https://wiki.cachyos.org/configuration/post_install_setup/) pour le système de base et sa mise à jour.

Les paquets conservent leurs licences et leurs sources amont. Aucun code tiers n'est recopié dans ce dépôt. Aucun dépôt de paquets supplémentaire ni aucune clé de confiance ne sont ajoutés.

### Paquets vérifiés dans le catalogue CachyOS

Le [catalogue officiel](https://packages.cachyos.org/) couvre les dépôts CachyOS et les dépôts Arch disponibles sur cette distribution. Fiches consultées le 10 novembre 2026 pour les composants du bureau :

| Composant | Nom exact | Dépôt de la fiche x86_64 | Version observée |
| --- | --- | --- | --- |
| Compositeur | [umbriel](https://packages.cachyos.org/package/cachyos/x86_64/umbriel) | `cachyos` | `0.1.0.r1459.2952bbc-1` |
| Bureau Noctalia actuel | [noctalia](https://packages.cachyos.org/package/extra/x86_64/noctalia) | `extra` (Arch) | `5.4.1-1` |
| Écran de connexion | [noctalia-greeter](https://packages.cachyos.org/package/cachyos/x86_64/noctalia-greeter) | `cachyos` | `1.6.0-1` |
| Portail Umbriel | [xdg-desktop-portal-umbriel](https://packages.cachyos.org/package/cachyos/x86_64/xdg-desktop-portal-umbriel) | `cachyos` | `0.1.0.r69.17739df-1` |

Ces versions ne sont pas figées par le script. Le script utilise explicitement le paquet `noctalia` et les commandes v5 ; la compatibilité d'un autre paquet doit être vérifiée par sa version et ses exécutables, sans la déduire de son seul nom. Le paquet `umbriel` de CachyOS dépend déjà du portail Umbriel ; celui-ci est également demandé explicitement pour rendre le plan lisible.

**Aucun accès à l'AUR et aucun assistant AUR ne sont nécessaires.** Le script demande exclusivement des paquets à pacman. Pour chaque paquet, y compris les outils complémentaires, il lit le dépôt et la version dans les bases locales, les affiche et utilise une cible explicite `dépôt/paquet`. Il respecte ainsi la priorité configurée, notamment les variantes optimisées CachyOS, et enregistre cette provenance dans la sauvegarde. Les dépendances transitives restent résolues par pacman, dont la transaction doit être examinée avant validation.

## Prérequis

- CachyOS démarré sur le disque, hors ISO live, avec systemd et accès Internet.
- Copie complète du dépôt préparé sur la cible : `scripts/`, `dotfiles/` et la documentation. Copier uniquement `umbriel_setup.sh` ne suffit pas. Les modifications locales ne sont pas publiées automatiquement sur GitHub.
- Compte utilisateur ordinaire avec mot de passe et accès à `sudo`, `pacman` et aux outils GNU usuels. Ne pas lancer le script avec `sudo`.
- Pilotes graphiques déjà installés et périphérique `/dev/dri/card*` présent. Cette présence ne garantit pas la compatibilité du GPU avec Wayland ; le script ne choisit aucun pilote.
- Console virtuelle locale, par exemple `Ctrl+Alt+F3`, sans session graphique active ni autre gestionnaire de connexion activé. Les sessions de bureau déjà installées sont signalées et bloquées : ce script ne les migre pas.
- Bases locales de paquets utilisables. L'aperçu utilise `pacman -Si`, sans synchronisation ni accès réseau ; des métadonnées anciennes peuvent signaler un paquet absent alors qu'il existe sur le miroir. Leur actualisation est une intervention distincte. L'application utilise une mise à jour complète `pacman -Syu`, jamais une mise à jour partielle `-Sy`.
- Les dépôts CachyOS et Arch requis doivent être activés. Si un paquet est absent des bases locales, le script bloque et demande de vérifier ces dépôts et leurs métadonnées ; il ne bascule pas vers l'AUR. Après synchronisation pendant l'application, les versions peuvent différer de l'aperçu : examiner aussi la transaction pacman.
- Aucun autre gestionnaire réseau actif ou activé (`systemd-networkd`, ConnMan, dhcpcd, ou iwd autonome). NetworkManager peut conserver son backend iwd existant. Une installation utilisant une autre organisation réseau nécessite une migration préparée séparément ; le script n'arrête pas ces services.

## Aperçu et application

Depuis la racine du dépôt, commencer par :

```bash
bash scripts/umbriel_setup.sh --plan
```

L'aperçu n'écrit aucun fichier, n'utilise pas sudo et n'installe rien. Sur macOS ou une autre distribution, il affiche les obstacles ; seul le système CachyOS cible peut être appliqué.

Le clavier d'Umbriel et de Greeter est `us` par défaut. Exemple pour le clavier canadien multilingue ; adapter les valeurs XKB à son clavier :

```bash
bash scripts/umbriel_setup.sh --plan --keyboard ca --variant multix
bash scripts/umbriel_setup.sh --print-config --keyboard ca --variant multix
```

Les options du clavier ne sont pas mémorisées entre deux appels : conserver les mêmes paramètres dans le plan et l'application.

`--print-config` nécessite Python 3 et affiche **chaque fichier séparément**, précédé de son chemin ; sa sortie complète n'est pas un fichier TOML unique à installer. Le plan ne nécessite pas Python ; l'application installe le paquet `python` avant de préparer et de vérifier les copies.

Après examen du plan, sur la machine cible uniquement :

```bash
bash scripts/umbriel_setup.sh --apply --keyboard ca --variant multix
```

Il faut saisir exactement `INSTALLER`, puis accepter les transactions de paquets. Il n'existe pas de mode de confirmation automatique. Un profil déjà présent bloque l'application ; l'option `--replace-config` autorise le remplacement complet des profils gérés et la mise à l'écart des réglages GUI Noctalia, après sauvegarde. Cela concerne aussi une configuration greetd fournie par un paquet déjà installé. Examiner les fichiers avant d'utiliser cette option : aucune fusion des personnalisations n'est réalisée.

Après le message de succès, redémarrer manuellement avec `sudo reboot` sur CachyOS. Greeter proposera Umbriel ; se connecter avec le compte créé pendant l'installation. Aucun lancement graphique, arrêt du réseau ou redémarrage n'est forcé pendant le script.

## Configurations modulaires et applications

### Catégories de paquets

Le script déclare les paquets dans des tableaux `PACKAGES_*` séparés et affiche ces catégories dans `--plan`, avant leur provenance. Toutes les catégories sont installées ; ce classement ne constitue pas une sélection de composants facultatifs. Elles sont réunies dans une seule transaction pacman avec mise à jour complète. Les dépendances supplémentaires sont indiquées par pacman lors de cette transaction.

| Catégorie | Paquets | Utilité |
| --- | --- | --- |
| Bureau Wayland | `umbriel`, `noctalia` | Gestion des fenêtres et interface du bureau : barre, lanceur, notifications et panneaux. |
| Écran de connexion | `greetd`, `noctalia-greeter` | Service de connexion et écran graphique de sélection de session/authentification. |
| Applications | `kitty`, `firefox`, `thunar`, `mousepad` | Respectivement terminal, navigateur web, gestionnaire de fichiers et éditeur de texte. |
| Audio | `pipewire`, `pipewire-audio`, `pipewire-pulse`, `wireplumber` | Infrastructure multimédia, prise en charge audio, compatibilité PulseAudio et gestion des périphériques/routages. |
| Réseau | `networkmanager` | Backend réseau utilisé par Noctalia pour Ethernet, Wi-Fi et ses contrôles de connexion. |
| Trousseau de secrets | `gnome-keyring`, `seahorse` | Fournisseur Secret Service pour les clés des historiques chiffrés de Noctalia et interface de gestion des trousseaux. |
| Intégration du bureau | `dbus`, `polkit`, `xorg-xwayland`, `xdg-utils`, `wl-clipboard` | Respectivement communication entre services, autorisations administratives, compatibilité X11, ouverture des fichiers/liens et commandes de presse-papiers Wayland. |
| Services de fichiers | `gvfs`, `tumbler` | Corbeille et accès aux volumes pour le gestionnaire de fichiers ; génération des miniatures. |
| Portails XDG | `xdg-desktop-portal`, `xdg-desktop-portal-umbriel`, `xdg-desktop-portal-gtk` | Interface commune des portails, backend Umbriel pour le partage/captures et backend GTK pour les dialogues et fonctions complémentaires. |
| Matériel | `brightnessctl`, `upower` | Contrôle de la luminosité et informations sur la batterie/l'alimentation, selon le matériel. |
| Polices et icônes | `ttf-dejavu`, `noto-fonts-emoji`, `adwaita-icon-theme` | Police du terminal et texte courant, emojis et icônes. |
| Préparation des configurations | `python` | Préparation des copies et validation de la syntaxe TOML et des inclusions. |

Le classement permet d'examiner le rôle de chaque composant. La liste complète et sa provenance sont affichées avant confirmation.

Les fichiers versionnés se trouvent dans [dotfiles/](../dotfiles/README.md). Ils reprennent l'organisation en modules de l'exemple Niri fourni, avec une syntaxe adaptée à Umbriel et Noctalia. Ils ne dépendent pas du dépôt `cachyos-noctalia-settings` et ne sont pas téléchargés lors de l'installation.

Umbriel sépare démarrage, clavier/pavé tactile, écrans, disposition, apparence, règles, raccourcis, espaces et touches multimédias. Noctalia sépare barre, widgets, comportement du shell, thème, captures, accessibilité et suivi système. Les deux derniers modules utilisent `ui_scale = 1.20` et `gpu_poll_seconds = 2.0` ; leur rôle et le retour aux valeurs par défaut sont décrits dans le [guide des modules](../dotfiles/README.md). Kitty sépare apparence et comportement. Les modules Greeter sont assemblés en un seul fichier, son format ne proposant pas d'inclusions documentées.

Les copies sont préparées dans un dossier temporaire privé. Les fichiers TOML et leurs inclusions sont contrôlés avec Python, puis les validateurs natifs de Noctalia et d'Umbriel sont exécutés **avant le remplacement des profils**, puis sur les profils installés, avant l'activation de greetd. Le script traite aussi les avertissements comme des points bloquants, même si le validateur retourne zéro. Les journaux sont conservés dans la sauvegarde, y compris après un échec de ces validateurs. Le répertoire temporaire est supprimé à la sortie.

Après la transaction, le script recharge les définitions des unités utilisateur, vérifie les unités de session Umbriel et `Type=notify`, puis vérifie que la pile PAM de greetd rejoint `pam_systemd.so`, directement ou par inclusion de session. Aucun fichier PAM n'est réécrit. Une installation de paquet incomplète ou incompatible bloque avant l'activation de l'écran de connexion.

Les nouveaux paquets d'usage courant incluent [Firefox](https://packages.cachyos.org/package/extra/x86_64/firefox), [Thunar](https://packages.cachyos.org/package/extra/x86_64/thunar), Mousepad, GVFS, Tumbler, `xdg-utils`, `wl-clipboard`, `brightnessctl`, `upower`, des icônes et une police emoji. Les noms sont résolus avec la même vérification de provenance que ceux du bureau. Les identifiants desktop sont associés aux liens web, dossiers et fichiers texte dans `mimeapps.list`.

## Effets et fichiers concernés

Le script affiche la liste exacte des paquets et leur provenance. Elle comprend les composants du bureau, les applications de base ci-dessus, Kitty, Xwayland, D-Bus, Polkit, PipeWire avec WirePlumber et les portails XDG, dont celui d'Umbriel. Les dépendances et hooks des paquets peuvent créer des comptes système, des fichiers et des préréglages de services. La mise à jour peut également toucher le noyau et d'autres logiciels déjà présents.

Avant la transaction, un dossier privé appartenant à root est créé sous `/var/lib/cachy-setup/noctalia-<date>-<identifiant>/`. Il contient :

- `packages-before.txt`, `package-sources.txt` (paquet, dépôt et version de l'aperçu revalidé), l'état d'activation de greetd et la cible de démarrage initiale ;
- une copie de `/etc/greetd/` sous `greetd` et de `/var/lib/noctalia-greeter/` sous `greeter-state`, ou des marqueurs `.absent` ;
- les profils personnels complets `umbriel`, `noctalia`, `kitty`, `xdg-desktop-portal` et le fichier `mimeapps.list` sous `user/`, ou des marqueurs `.absent` ;
- une copie des réglages GUI Noctalia sous `noctalia-settings`, ou le marqueur `.absent` ; leurs autres données d'état ne sont pas déplacées ;
- `paths.txt` pour les chemins XDG, l'état d'activation des trois unités audio et du socket GNOME Keyring dans des fichiers `*.before`, ainsi que `NetworkManager.service.before` ;
- `proposed/` pour les copies préparées, `validation-before-copy/` et `validation-installed/` pour les diagnostics natifs, puis `packages-after.txt` après succès.

Lors du remplacement, les profils actifs sont aussi déplacés dans `replaced-user/` et les réglages GUI dans `noctalia-settings-replaced.toml`. Ces copies supplémentaires conservent l'état exact au moment du remplacement, y compris d'éventuels fichiers déposés par les paquets.

Les chemins de configuration contenant un lien symbolique sont refusés. Les sauvegardes restent locales, hors Git, et peuvent contenir des données personnelles.

Les profils sont installés par copie dans `$XDG_CONFIG_HOME` (sinon `~/.config`), sans lien symbolique vers le dépôt. Les chemins XDG doivent être situés sous le dossier personnel. Le point d'entrée Umbriel charge ses modules et lance `noctalia` une seule fois ; aucune seconde unité de démarrage Noctalia n'est activée. Les autres dossiers de configuration restent en place.

`/etc/greetd/config.toml` utilise la console virtuelle 1, le compte système `greeter` et `/usr/bin/noctalia-greeter-session`. Le compte et les exécutables attendus doivent être fournis par les paquets. Le helper officiel initialise l'état de Greeter avec `GREETER_USER=greeter` explicite, puis le fichier déclaratif est installé en mode `0600` sous ce compte. Le script n'ajoute aucune règle PAM ni autorisation de synchronisation sans mot de passe. Les réglages d'horloge de la documentation rolling sont omis car ils ne sont pas reconnus par Greeter 1.6.0 relevé dans CachyOS.

Le script active `greetd.service` et `NetworkManager.service`, sélectionne `graphical.target` et active les unités utilisateur `pipewire.socket`, `pipewire-pulse.socket`, `wireplumber.service` et `gnome-keyring-daemon.socket` pour les prochains démarrages de leurs gestionnaires. Il ne démarre pas greetd immédiatement, ne relance ni réseau ni audio et ne redémarre pas l'ordinateur. Il ne change pas les connexions réseau, Bluetooth, les pilotes, les disques ni un autre bureau. Les paramètres du clavier sont appliqués à la session et au Greeter. Greeter sélectionne Umbriel par défaut et conserve `allow_empty_password = false`.

Les connexions NetworkManager déjà configurées restent en place ; aucune clé Wi-Fi n'est copiée dans le dépôt. Au premier accès aux fonctions chiffrées de Noctalia, créer ou déverrouiller le trousseau via ses dialogues. Seahorse (« Mots de passe et clés ») permet de choisir la collection par défaut. Le script n'enregistre aucun mot de passe et n'ajoute pas de déverrouillage automatique par PAM : une demande de déverrouillage peut donc réapparaître après connexion. Tant que la collection par défaut reste verrouillée, les historiques fonctionnent uniquement pour la session. Les comptes de calendrier et autres identifiants personnels se configurent ensuite dans l'interface.

Le [portail Umbriel](https://github.com/noctalia-dev/xdg-desktop-portal-umbriel) est installé depuis les dépôts pour le partage d'écran, avec le portail GTK pour les fonctions complémentaires. Le partage effectif reste à vérifier dans une session réelle et dans les applications utilisées.

## Premier lancement et validation réelle

Après succès, redémarrer manuellement pour vérifier le chemin complet **démarrage → Greeter → Umbriel → Noctalia**. Dans Greeter, la session **Umbriel** est sélectionnée par défaut. Un essai préalable depuis la TTY reste possible avec `start-umbriel`, mais ne vérifie pas l'authentification et les services au démarrage.

Raccourcis préparés : `Super+Entrée` ouvre Kitty, `Super+B` Firefox, `Super+E` Thunar, `Super+Maj+E` Mousepad, `Super+Espace` le lanceur, `Super+S` le panneau de contrôle, `Super+Virgule` les réglages, `Super+V` le presse-papiers et `Super+Alt+L` le verrouillage. `Print` capture une région et `Maj+Print` l'écran, dans le presse-papiers. `Super+Q` ferme une fenêtre, `Super+O` ouvre la vue d'ensemble et `Super+Échap` ouvre le menu de session. Les flèches avec Super déplacent le focus ; avec Maj elles déplacent les fenêtres/colonnes. `Super+1…9` change d'espace, `Super+Maj+1…9` y déplace la fenêtre. Les touches multimédias passent par Noctalia pour afficher les indicateurs.

`Alt+Tab` utilise le sélecteur de fenêtres Noctalia. `Super+Maj+Échap` permet de sortir du mode d'inhibition des raccourcis de certaines applications. Les lancements d'applications et captures sont configurés sans répétition automatique.

Vérifier le clavier avant de saisir des mots de passe, les écrans, l'audio, le verrouillage et le retour à Greeter après déconnexion. Depuis une console ou le terminal, consulter :

```bash
systemctl status greetd
journalctl -b -u greetd --no-pager
umbriel config validate
systemctl --user status pipewire.socket pipewire-pulse.socket wireplumber.service
systemctl status NetworkManager
nmcli general status
systemctl --user status gnome-keyring-daemon.socket
```

En cas d'échec, conserver la TTY de secours et consulter aussi `~/.cache/umbriel/`. Le script s'arrête à la première erreur ; une transaction interrompue peut laisser une installation partielle. Il n'effectue pas de restauration automatique et une mise à jour de paquets n'est pas une transaction réversible par ce script.

## Retour arrière

Effectuer ces actions manuellement sur CachyOS, après avoir identifié la bonne sauvegarde. Ne pas les exécuter sur la machine de préparation macOS. Rejoindre une TTY de secours et fermer les sessions avant de désactiver greetd.

1. Noter le chemin affiché par le script et examiner son contenu avec `sudo ls -la /var/lib/cachy-setup/`. Affecter ce chemin à une variable `backup`, par exemple `backup=/var/lib/cachy-setup/noctalia-...` avec son nom réel.
2. Arrêter et désactiver l'écran de connexion : `sudo systemctl disable --now greetd.service`.
3. Lire `sudo cat "$backup/default-target-before.txt"`, puis rétablir cette cible avec `sudo systemctl set-default NOM_LU`.
4. Préserver les fichiers actuels dans un nouveau dossier de secours avant leur remplacement. Pour `/etc/greetd`, déplacer le dossier actuel vers un nom libre, puis copier `sudo cp -a "$backup/greetd" /etc/greetd` si cette sauvegarde existe. Si `greetd.absent` existe, laisser le chemin absent. Même principe pour `/var/lib/noctalia-greeter` avec `greeter-state`.
5. Lire `paths.txt` pour retrouver le dossier XDG initial. Mettre chaque profil généré à l'écart, puis restaurer les éléments de `user/` à leurs chemins d'origine avec `sudo cp -a` pour préserver leurs propriétaires. Si un marqueur `user/NOM.absent` existe, laisser ce chemin absent après mise à l'écart du profil généré. Ne pas toucher aux autres dossiers de configuration. `replaced-user/` peut servir à examiner l'état juste avant le remplacement ; `user/` conserve l'état antérieur à la transaction de paquets.
6. Si `noctalia-settings` existe, restaurer ce fichier sous le chemin XDG d'état `noctalia/settings.toml`, en conservant son propriétaire. Sinon, déplacer à l'écart un éventuel fichier créé entre-temps par Noctalia. Pour les services utilisateur, consulter `pipewire.socket.before`, `pipewire-pulse.socket.before`, `wireplumber.service.before` et `gnome-keyring-daemon.socket.before`. Pour chaque unité initialement désactivée ou absente, utiliser `systemctl --user disable NOM` ; pour une unité initialement activée, la laisser activée. Les états spéciaux demandent un examen spécifique. Sans `--now`, cela ne coupe pas les services de la session courante.
7. Lire `greetd-enabled-before.txt`. Si l'état était `enabled`, réactiver avec `sudo systemctl enable greetd.service`. Les états `masked`, `static`, etc. nécessitent un examen spécifique ; ne pas les remplacer par `enabled`.
8. Consulter `NetworkManager.service.before`. Si le service était désactivé ou absent, `sudo systemctl disable NetworkManager.service` annule son activation au démarrage ; ne pas employer `--now` depuis une connexion qui en dépend. Si le service était déjà activé, conserver cet état. Aucun autre gestionnaire n'ayant été désactivé par le script, aucune migration inverse n'est à exécuter.
9. Comparer `packages-before.txt` à `packages-after.txt`, ou à `pacman -Q` après un échec. Désinstaller uniquement les paquets nouvellement ajoutés dont l'absence d'utilisation a été vérifiée, après examen de la transaction proposée. Ne pas retirer des dépendances ou rétrograder tout le système aveuglément. Les mises à jour de paquets existants et les fichiers créés par les hooks ne sont pas annulés par la restauration des configurations. Les trousseaux que l'utilisateur a créés ensuite sont ses données personnelles ; ne pas les supprimer.

Une sauvegarde système ou un instantané Btrfs préparé séparément reste nécessaire pour revenir sur une mise à jour complète. Le script ne crée aucun instantané et ne touche pas aux partitions.

## Vérifications du dépôt

```bash
bash -n scripts/umbriel_setup.sh
python3 -B tests/test_umbriel_setup.py
# Sur Python >= 3.11, contrôle TOML de tous les modules sans écriture :
python3 -B scripts/noctalia_dotfiles.py --check --keyboard ca --variant multix
```

Les tests isolent les chemins personnels et interdisent l'appel aux outils de modification pendant les modes de consultation. Ils contrôlent les modules TOML, inclusions et claviers, les refus d'arguments, la provenance avec un faux pacman et les conflits réseau avec un faux systemctl. Une fixture vérifie le remplacement des profils et les sauvegardes. Des sorties natives simulées vérifient que les avertissements et erreurs bloquent l'application. Les inclusions PAM sont vérifiées dans un dossier temporaire. Les tests emploient `tomllib` ou, sur le Python 3.9 local, le parseur TOML déjà livré avec pip ; aucun parseur n'a été installé. Sur CachyOS, l'outil de préparation utilise le `tomllib` du paquet Python actuel. Ces tests ne constituent ni une exécution de pacman/systemd, ni une validation des binaires Linux ou du matériel.

Contrôles effectués sur macOS le 10 novembre 2026 : syntaxe Bash correcte et **22 tests réussis, aucun ignoré**, dont l'analyse de tous les modules TOML. Les validateurs natifs seront exécutés par le script sur CachyOS avant l'activation des services. Aucune installation ni activation n'a été exécutée ici ; le parcours graphique complet reste à valider sur la cible.
