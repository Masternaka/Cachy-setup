# Installer Noctalia, Umbriel et Greeter sur CachyOS

[Accueil](../README.md) · [Configuration et raccourcis](configuration.md)

Le script [umbriel_setup.sh](../scripts/umbriel_setup.sh) s'utilise **après avoir installé CachyOS avec le choix « No Desktop »**, puis redémarré sur le disque et ouvert une session en console. Il installe ensuite le bureau Wayland demandé, ses applications de base, NetworkManager et le trousseau de secrets. Le système de base, les pilotes et un accès Internet doivent déjà fonctionner. La [vérification documentaire du 10 novembre 2026](verification-noctalia-2026-11-10.md) explique les recommandations suivies et les limites des contrôles.

## Dans ce guide

- [Prérequis](#prérequis)
- [Aperçu, options et application](#aperçu-et-application)
- [Paquets et applications](#configurations-modulaires-et-applications)
- [Récupération de Kitty](#kitty-depuis-le-dépôt-cachyos)
- [Fichiers modifiés et sauvegardes](#effets-et-fichiers-concernés)
- [Premier lancement et dépannage](#premier-lancement-et-validation-réelle)
- [Retour arrière](#retour-arrière)
- [Sources et versions relevées](#choix-de-version-et-provenance)
- [Vérifications locales](#vérifications-du-dépôt)

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

| Option | Utilisation |
| --- | --- |
| Sans option ou `--plan` | Lire le plan, les paquets et les blocages, sans modification. |
| `--print-config` | Lire les copies locales préparées, sans écriture ni récupération de Kitty. |
| `--keyboard CODE` / `--variant CODE` | Choisir le clavier de la session et de Greeter ; défaut `ca`, variante vide. |
| `--apply` | Appliquer sur la cible après confirmation `INSTALLER`. |
| `--replace-config` | Avec `--apply`, remplacer les profils gérés complets après sauvegarde. |
| `--help` | Consulter l'aide des options. |

### Première installation

Depuis la racine du dépôt, commencer par :

```bash
bash scripts/umbriel_setup.sh --plan
```

L'aperçu n'écrit aucun fichier, n'utilise pas sudo et n'installe rien. Sur macOS ou une autre distribution, il affiche les obstacles ; seul le système CachyOS cible peut être appliqué.

Le clavier d'Umbriel et de Greeter est **canadien français** par défaut : disposition XKB `ca`, variante vide (`variant = ""`). Le script Bash et l'outil Python utilisent le même défaut. La [documentation xkeyboard-config](https://man.archlinux.org/man/xkeyboard-config-2.7.en), consultée le 17 novembre 2026, identifie `ca` comme « French (Canada) » et `ca(multix)` comme « Canadian (CSA) ». Pour afficher explicitement le profil canadien français :

```bash
bash scripts/umbriel_setup.sh --plan --keyboard ca
bash scripts/umbriel_setup.sh --print-config --keyboard ca
```

Sans option, ces commandes sélectionnent déjà le canadien français. Les options du clavier ne sont pas mémorisées entre deux appels : si le défaut est remplacé, conserver les mêmes paramètres dans le plan et l'application. Le canadien multilingue/CSA reste disponible avec `--keyboard ca --variant multix`, et le clavier américain avec `--keyboard us`. Le script ne modifie pas le clavier de la console TTY ni `/etc/vconsole.conf`.

`--print-config` nécessite Python 3 et affiche **chaque fichier local séparément**, précédé de son chemin ; sa sortie complète n'est pas un fichier TOML unique à installer. Pour Kitty, il affiche seulement la référence externe, sans téléchargement ni aperçu du contenu distant. Le plan ne nécessite pas Python ; l'application installe le paquet `python` avant de préparer et de vérifier les copies.

Après examen du plan, sur la machine cible uniquement :

```bash
bash scripts/umbriel_setup.sh --apply --keyboard ca
```

Il faut saisir exactement `INSTALLER`, puis accepter les transactions de paquets. Il n'existe pas de mode de confirmation automatique. Un profil déjà présent bloque l'application ; l'option `--replace-config` autorise le remplacement complet des profils gérés et la mise à l'écart des réglages GUI Noctalia, après sauvegarde. Cela concerne aussi une configuration greetd fournie par un paquet déjà installé. Examiner les fichiers avant d'utiliser cette option : aucune fusion des personnalisations n'est réalisée.

### Réappliquer une configuration existante

Après lecture du nouveau plan et comparaison des personnalisations actives avec celles du dépôt :

```bash
bash scripts/umbriel_setup.sh --apply --replace-config --keyboard ca
```

Cette commande relance aussi la transaction de paquets et la récupération de Kitty. Elle remplace **tous les profils gérés**, y compris un éventuel `umbriel/local.toml` actif et les réglages GUI Noctalia prioritaires ; elle ne fusionne pas les fichiers. La sauvegarde conserve l'ancien état. Aucun remplacement n'est nécessaire pour simplement lire le plan. Après la transaction de paquets et la préparation validée, `--replace-config` affiche les différences des profils utilisateur, signale le retrait des réglages GUI Noctalia et demande une seconde confirmation `REMPLACER` avant copie. Les profils système greetd/Greeter suivent le plan initial. Annuler à cette étape conserve les profils mais n’annule pas les paquets déjà traités. Pour ne remplacer qu’un profil sans paquets ni Greeter, préférer la [maintenance ciblée](maintenance.md).

Après le message de succès, redémarrer manuellement avec `sudo reboot` sur CachyOS. Greeter proposera Umbriel ; se connecter avec le compte créé pendant l'installation. Aucun lancement graphique, arrêt du réseau ou redémarrage n'est forcé pendant le script.

## Configurations modulaires et applications

### Catégories de paquets

Le script déclare les paquets dans des tableaux `PACKAGES_*` séparés et affiche ces catégories dans `--plan`, avant leur provenance. Toutes les catégories sont installées ; ce classement ne constitue pas une sélection de composants facultatifs. Elles sont réunies dans une seule transaction pacman avec mise à jour complète. Les dépendances supplémentaires sont indiquées par pacman lors de cette transaction.

| Catégorie | Paquets | Utilité |
| --- | --- | --- |
| Bureau Wayland | `umbriel`, `noctalia` | Gestion des fenêtres et interface du bureau : barre, lanceur, notifications et panneaux. |
| Écran de connexion | `greetd`, `noctalia-greeter` | Service de connexion et écran graphique de sélection de session/authentification. |
| Applications | `kitty`, `firefox`, `firefox-i18n-fr`, `thunar`, `micro`, `zed`, `papers`, `loupe`, `mpv` | Terminal, Firefox avec langue française, gestionnaire de fichiers, éditeurs Micro/Zed, lecteur PDF, visionneuse d'images et lecteur multimédia. |
| Audio | `pipewire`, `pipewire-audio`, `pipewire-pulse`, `pipewire-alsa`, `wireplumber`, `pavucontrol` | Infrastructure multimédia, compatibilité PulseAudio/ALSA, gestion des périphériques/routages et réglages détaillés par application. |
| Réseau | `networkmanager` | Backend réseau utilisé par Noctalia pour Ethernet, Wi-Fi et ses contrôles de connexion. |
| Trousseau de secrets | `gnome-keyring`, `seahorse` | Fournisseur Secret Service pour les clés des historiques chiffrés de Noctalia et interface de gestion des trousseaux. |
| Intégration du bureau | `dbus`, `polkit`, `xorg-xwayland`, `xdg-utils`, `wl-clipboard` | Respectivement communication entre services, autorisations administratives, compatibilité X11, ouverture des fichiers/liens et commandes de presse-papiers Wayland. |
| Services de fichiers | `gvfs`, `gvfs-smb`, `gvfs-mtp`, `tumbler`, `ffmpegthumbnailer`, `thunar-archive-plugin`, `thunar-volman`, `xarchiver`, `zip`, `unzip` | Corbeille, volumes, partages SMB, appareils MTP, miniatures vidéo, intégration des archives dans Thunar et outils ZIP. |
| Portails XDG | `xdg-desktop-portal`, `xdg-desktop-portal-umbriel`, `xdg-desktop-portal-gtk` | Interface commune des portails, backend Umbriel pour le partage/captures et backend GTK pour les dialogues et fonctions complémentaires. |
| Matériel | `brightnessctl`, `upower` | Contrôle de la luminosité et informations sur la batterie/l'alimentation, selon le matériel. |
| Polices et icônes | `ttf-dejavu`, `ttf-liberation`, `ttf-jetbrains-mono-nerd`, `noto-fonts-emoji`, `adwaita-icon-theme` | Texte courant, polices Liberation, JetBrainsMono Nerd Font demandée par le profil Kitty, emojis et icônes. |
| Préparation des configurations | `python` | Préparation des copies et validation de la syntaxe TOML et des inclusions. |

Le classement permet d'examiner le rôle de chaque composant. La liste complète et sa provenance sont affichées avant confirmation.

Vérification complémentaire du 17 novembre 2026 : les fiches CachyOS indiquent `zed` `1.19.2-1`, `xarchiver` `0.5.4.26-1`, `zip` `3.0-14` et `unzip` `6.0-23` dans `extra`. La [liste des fichiers Arch de Zed](https://archlinux.org/packages/extra/x86_64/zed/files/), alors en `1.28.1-1`, fournit `zeditor` et `dev.zed.Zed.desktop` : ce sont les noms utilisés dans les contrôles et les profils. Les fiches peuvent être décalées par rapport aux bases de la cible ; le script ne fige aucune de ces versions et vérifie les fichiers après installation. Micro s'utilise depuis Kitty avec `micro`. Zed devient l'application par défaut pour les fichiers texte et le raccourci `Super+Maj+E`.

Le [plugin d'archives Thunar](https://docs.xfce.org/xfce/thunar/archive) utilise un gestionnaire externe. [Xarchiver](https://packages.cachyos.org/package/extra/x86_64/xarchiver), [zip](https://packages.cachyos.org/package/extra/x86_64/zip) et [unzip](https://packages.cachyos.org/package/extra/x86_64/unzip) sont donc demandés explicitement. Les autres formats dépendent des outils présents sur la cible. `thunar-volman` fournit l'intégration de gestion des volumes ; ses préférences ne sont pas modifiées par le script.

### Compléments de confort inclus

Ces cinq paquets font partie des catégories Audio et Services de fichiers du script et sont prévus dans la même transaction pacman. Fiches du catalogue CachyOS consultées le 17 novembre 2026 ; leur disponibilité et leur version restent à résoudre dans les dépôts configurés de la cible.

| Paquet | Apport | Usage conseillé |
| --- | --- | --- |
| [pipewire-alsa](https://packages.cachyos.org/package/extra/x86_64/pipewire-alsa) | Routage des applications ALSA vers PipeWire. | Compléter la compatibilité audio. |
| [pavucontrol](https://packages.cachyos.org/package/extra/x86_64/pavucontrol) | Réglage audio détaillé par application, entrée et sortie via la compatibilité PulseAudio. | Compléter les contrôles courants de Noctalia. |
| [ffmpegthumbnailer](https://packages.cachyos.org/package/extra/x86_64/ffmpegthumbnailer) | Génération de miniatures vidéo. | Parcourir les dossiers vidéo dans Thunar avec Tumbler. |
| [gvfs-smb](https://packages.cachyos.org/package/extra/x86_64/gvfs-smb) | Accès client aux partages SMB depuis le gestionnaire de fichiers. | Utilisation d'un NAS ou de partages Windows/Samba ; aucun serveur Samba à configurer. |
| [gvfs-mtp](https://packages.cachyos.org/package/extra/x86_64/gvfs-mtp) | Accès aux appareils MTP, dont les téléphones Android. | Transfert de fichiers par USB. |

Pavucontrol s'ouvre depuis le lanceur ou avec `pavucontrol`. Les accès SMB/MTP et les miniatures s'intègrent à Thunar ; le script ne configure aucun partage, aucun serveur Samba et aucun montage persistant. Un téléphone doit autoriser le transfert de fichiers. L'installation de ces compléments ne crée aucune unité supplémentaire à activer dans le script ; les contrôles existants d'audio et de réseau restent en place. Leur fonctionnement réel reste à vérifier sur CachyOS.

Les catégories Applications et Polices et icônes incluent aussi les cinq compléments suivants :

| Paquet | Utilité et ouverture prévue |
| --- | --- |
| [papers](https://archlinux.org/packages/extra/x86_64/papers/) | Lecteur PDF, associé à `application/pdf` avec `org.gnome.Papers.desktop`. |
| [loupe](https://archlinux.org/packages/extra/x86_64/loupe/) | Visionneuse associée aux images JPEG, PNG, GIF, WebP, BMP, TIFF et SVG avec `org.gnome.Loupe.desktop`. |
| [mpv](https://packages.cachyos.org/package/extra/x86_64/mpv) | Lecteur associé aux vidéos MP4, Matroska, WebM, QuickTime, AVI et MPEG, ainsi qu'aux fichiers audio MP3, FLAC, Ogg et WAV avec `mpv.desktop`. |
| [firefox-i18n-fr](https://packages.cachyos.org/package/extra/any/firefox-i18n-fr) | Pack de langue française de Firefox ; sélectionner le français dans les réglages de langue si nécessaire. Aucun profil Firefox n'est modifié. |
| [ttf-liberation](https://packages.cachyos.org/package/extra/any/ttf-liberation) | Polices compatibles avec les dimensions d'Arial, Times New Roman et Courier New, utiles pour la mise en page des documents. |

Vérification du 17 novembre 2026 : les fiches CachyOS consultées indiquent `mpv` `1:0.41.0-6`, `firefox-i18n-fr` `151.0.4-1` et `ttf-liberation` `2.1.5-2`. Les fiches CachyOS de Papers et Loupe étant inaccessibles, leur présence dans Arch `extra` a été vérifiée (`papers` `51.1-1`, `loupe` `51.2-1`). Les listes de fichiers Arch de [Papers](https://archlinux.org/packages/extra/x86_64/papers/files/), [Loupe](https://archlinux.org/packages/extra/x86_64/loupe/files/) et [mpv](https://archlinux.org/packages/extra/x86_64/mpv/files/) confirment les exécutables et identifiants desktop utilisés. Ces relevés ne figent aucune version ; le script résout tous les noms dans les dépôts configurés de la cible et vérifie les exécutables et fichiers desktop installés avant la copie des profils.

Les fichiers versionnés se trouvent dans [dotfiles/](configuration.md). Ils reprennent l'organisation en modules de l'exemple Niri fourni, avec une syntaxe adaptée à Umbriel et Noctalia. Ils ne dépendent pas du dépôt `cachyos-noctalia-settings` et restent locaux ; seul le profil Kitty est récupéré séparément depuis le dépôt CachyOS après confirmation.

Umbriel sépare démarrage, clavier/pavé tactile, écrans, disposition, apparence, règles, raccourcis, espaces et touches multimédias. Noctalia sépare barre, widgets, comportement du shell, thème, captures, accessibilité et suivi système. Les deux derniers modules préparent `ui_scale = 1.20` et `gpu_poll_seconds = 2.0`, mais leurs inclusions sont actuellement commentées ; leur activation et les valeurs intégrées sont décrites dans le [guide des modules](configuration.md). Kitty utilise les fichiers du dépôt CachyOS, sans second profil local. Les modules Greeter sont assemblés en un seul fichier, son format ne proposant pas d'inclusions documentées.

Le module `umbriel/cfg/display.toml` configure les deux écrans personnels indiqués : **DP-1 à gauche**, position `[0, 0]`, et **HDMI-A-2 à droite**, position `[1920, 0]`. Chacun utilise `1920x1080@60`, une échelle de `1.0` (100 %) et une orientation normale. Le bureau étendu occupe ainsi 3840 × 1080 unités logiques, sans espace ni chevauchement. La base reste en SDR à fréquence fixe (`hdr = "off"`, `vrr = "disabled"`, `tearing = false`), avec détection automatique du GPU. Aucun écran principal n'est imposé.

Ces réglages suivent la [documentation officielle Outputs](https://docs.noctalia.dev/umbriel/outputs/), consultée le 17 novembre 2026. La fiche CachyOS et la source correspondant à l'ancienne révision relevée le 10 novembre n'ont pas pu être consultées lors de cet ajustement : la compatibilité avec le binaire de la cible reste à confirmer par les validateurs prévus dans le script. `umbriel outputs` doit confirmer les connecteurs et les modes réellement annoncés, notamment si le matériel annonce 59,94 Hz plutôt que 60 Hz. Le module concerne la session Umbriel ; la disposition des écrans dans Greeter n'est pas modifiée. Pour revenir à la détection automatique, retirer ou commenter les deux tables `[output."..."]` et leurs valeurs dans le module, puis préparer et valider de nouveau les copies. Une configuration active remplacée reste récupérable dans la sauvegarde décrite plus bas.

Les copies sont préparées dans un dossier temporaire privé. Les fichiers TOML et leurs inclusions sont contrôlés avec Python, puis les validateurs natifs de Noctalia et d'Umbriel sont exécutés **avant le remplacement des profils**, puis sur les profils installés, avant l'activation de greetd. Le script traite aussi les avertissements comme des points bloquants, même si le validateur retourne zéro. Les journaux sont conservés dans la sauvegarde, y compris après un échec de ces validateurs. Le répertoire temporaire est supprimé à la sortie.

Après la transaction, le script recharge les définitions des unités utilisateur, vérifie les unités de session Umbriel et `Type=notify`, puis vérifie que la pile PAM de greetd rejoint `pam_systemd.so`, directement ou par inclusion de session. Aucun fichier PAM n'est réécrit. Une installation de paquet incomplète ou incompatible bloque avant l'activation de l'écran de connexion.

Les nouveaux paquets d'usage courant incluent [Firefox](https://packages.cachyos.org/package/extra/x86_64/firefox) avec sa langue française, [Thunar](https://packages.cachyos.org/package/extra/x86_64/thunar), Micro, Zed, Papers, Loupe, mpv, GVFS, Tumbler, les extensions Thunar et Xarchiver avec les outils ZIP, `xdg-utils`, `wl-clipboard`, `brightnessctl`, `upower`, les polices Liberation, des icônes et une police emoji. Les noms sont résolus avec la même vérification de provenance que ceux du bureau. Les identifiants desktop sont associés aux liens web, dossiers, fichiers texte, PDF et formats courants d'images, de vidéos et d'audio dans `mimeapps.list`.

### Horloge Greeter et version 1.7

Le 17 novembre 2026, la version 1.7 a été signalée disponible par l'utilisateur. La fiche du catalogue CachyOS n'a pas pu être confirmée lors de cette vérification ; l'[exemple officiel du tag v1.7.0](https://github.com/noctalia-dev/noctalia-greeter/blob/v1.7.0/examples/greeter.toml) confirme les quatre champs `[clock]` utilisés. Le relevé `1.6.0-1` du tableau du 10 novembre ci-dessus reste historique. Les paramètres de taille de police de la documentation rolling ne sont pas ajoutés, car ils ne figurent pas dans cet exemple 1.7.0.

Après la transaction de paquets, `pacman -T 'noctalia-greeter>=1.7.0'` contrôle la version installée sans installer de paquet. Si elle est insuffisante, le script s'arrête avant la copie des profils ; la transaction de paquets a toutefois déjà eu lieu. Les versions disponibles restent résolues par les dépôts de la cible.

L'horloge et la date suivent le fuseau horaire et la locale du processus Greeter. Le clavier `ca` ne garantit pas une date en français ; aucune locale système n'est modifiée. La position des écrans Greeter et la synchronisation d'apparence restent inchangées. Pour retirer ces réglages explicites, enlever `dotfiles/system/noctalia-greeter/35-clock.toml`, puis préparer et valider de nouveau les copies ; Greeter utilise alors ses valeurs intégrées. La restauration des profils installés utilise la sauvegarde décrite plus bas. L'affichage réel de l'horloge reste à vérifier sur CachyOS.

### Kitty depuis le dépôt CachyOS

La source unique est [Masternaka/CachyOS — Dotfiles/kitty/.config/kitty](https://github.com/Masternaka/CachyOS/tree/main/Dotfiles/kitty/.config/kitty). Les trois anciens fichiers Kitty de Cachy-setup ont été retirés. Pour faire évoluer le profil, modifier puis publier les fichiers sur `main` dans CachyOS ; la prochaine application confirmée utilisera cette version. La configuration déjà installée ne se met pas à jour toute seule. Une réapplication avec l’installateur complet demande toujours `--replace-config` si les profils gérés existent ; elle remplace aussi les autres profils du bureau après sauvegarde. Pour Kitty seul, utiliser l’[outil de maintenance ciblée](maintenance.md), qui ne relance pas pacman.

`scripts/kitty_source.py` est un outil de préparation, sans installation. Lors de `--apply`, après la confirmation et la transaction pacman, l'outil Python :

1. Résout le dernier commit de `main` via l'API GitHub, puis récupère l'archive de ce commit précis. Une modification de `main` pendant la récupération ne mélange pas deux versions.
2. Lit seulement les fichiers du dossier Kitty, thèmes et documentation compris, sans extraire ni exécuter les autres scripts du dépôt. Il refuse les liens, fichiers spéciaux, chemins ambigus, doublons, contenus non UTF-8 et archives corrompues. Les limites sont de 32 Mio téléchargés, 100 fichiers Kitty, 2 Mio par fichier et 8 Mio pour le profil.
3. Convertit les inclusions `~/.config/kitty/...` en chemins relatifs dans les copies, conformément aux [inclusions Kitty](https://sw.kovidgoyal.net/kitty/conf/). Les autres options et commentaires restent ceux de la source. Les inclusions statiques doivent rester dans le profil, exister et ne pas former de cycle. Les inclusions dynamiques ou générées nécessitent un examen distinct et sont refusées.
4. Prépare les fichiers avec le reste du bureau, puis laisse les validations et les sauvegardes existantes précéder la copie des profils.

Une panne GitHub, une limite de l'API ou un contrôle échoué bloque le remplacement des profils, sans repli silencieux sur une ancienne copie. **La transaction de paquets a cependant déjà eu lieu** : cet échec ne l'annule pas. `--plan` et `--print-config` restent sans accès réseau et ne peuvent donc pas confirmer à l'avance la disponibilité ou le contenu de `main`.

La sauvegarde contient `kitty-source.json` : dépôt, branche, commit, heure de récupération, chemins adaptés et empreintes SHA-256 des fichiers d'origine et préparés. `proposed/user/kitty/` conserve la copie préparée lorsque la validation avant copie a réussi. Le profil précédent reste dans `user/kitty` ou est signalé absent ; la procédure de restauration ci-dessous s'applique sans accès GitHub. `--replace-config` conserve aussi le profil déplacé sous `replaced-user/kitty`.

La police [ttf-jetbrains-mono-nerd](https://packages.cachyos.org/package/extra/any/ttf-jetbrains-mono-nerd), fiche consultée le 17 novembre 2026 (`3.5.1-2`), complète les paquets pour le profil actuel. Le code ne réécrit pas automatiquement une future police ni les réglages personnels de copie, fermeture ou contrôle distant. Les contrôles Kitty portent sur les fichiers et inclusions : ils ne constituent pas une validation native de toutes les options ni du rendu de Kitty. Vérifier le terminal sur CachyOS avant de conclure à sa compatibilité complète.

Validation locale du 17 novembre 2026 : 12 scénarios de récupération simulée couvrent la résolution de `main`, les erreurs réseau/archives/inclusions, la conservation des fichiers existants et la provenance. Les sept fichiers du checkout local CachyOS ont été comparés aux empreintes des blobs GitHub consultés ; leur préparation et l'unique adaptation d'inclusion ont été vérifiées en mémoire. Aucun téléchargement HTTP réel via le nouvel outil, installation ou lancement natif de Kitty n'a été effectué ici.

## Effets et fichiers concernés

Le script affiche la liste exacte des paquets et leur provenance. Elle comprend les composants du bureau, les applications de base ci-dessus, Kitty, Xwayland, D-Bus, Polkit, PipeWire avec WirePlumber et les portails XDG, dont celui d'Umbriel. Les dépendances et hooks des paquets peuvent créer des comptes système, des fichiers et des préréglages de services. La mise à jour peut également toucher le noyau et d'autres logiciels déjà présents.

Avant la transaction, un dossier privé appartenant à root est créé sous `/var/lib/cachy-setup/noctalia-<date>-<identifiant>/`. Il contient :

- `packages-before.txt`, `package-sources.txt` (paquet, dépôt et version de l'aperçu revalidé), l'état d'activation de greetd et la cible de démarrage initiale ;
- une copie de `/etc/greetd/` sous `greetd` et de `/var/lib/noctalia-greeter/` sous `greeter-state`, ou des marqueurs `.absent` ;
- les profils personnels complets `umbriel`, `noctalia`, `kitty`, `xdg-desktop-portal` et le fichier `mimeapps.list` sous `user/`, ou des marqueurs `.absent` ;
- après récupération et préparation, la provenance externe de Kitty dans `kitty-source.json` ;
- une copie des réglages GUI Noctalia sous `noctalia-settings`, ou le marqueur `.absent` ; leurs autres données d'état ne sont pas déplacées ;
- `paths.txt` pour les chemins XDG, l'état d'activation des trois unités audio et du socket GNOME Keyring dans des fichiers `*.before`, ainsi que `NetworkManager.service.before` ;
- `proposed/` pour les copies préparées, `validation-before-copy/` et `validation-installed/` pour les diagnostics natifs, puis `packages-after.txt` après succès.

Lors du remplacement, les profils actifs sont aussi déplacés dans `replaced-user/` et les réglages GUI dans `noctalia-settings-replaced.toml`. Ces copies supplémentaires conservent l'état exact au moment du remplacement, y compris d'éventuels fichiers déposés par les paquets.

Les chemins de configuration contenant un lien symbolique sont refusés. Les sauvegardes restent locales, hors Git, et peuvent contenir des données personnelles.

Les profils sont installés par copie dans `$XDG_CONFIG_HOME` (sinon `~/.config`), sans lien symbolique vers le dépôt. Les chemins XDG doivent être situés sous le dossier personnel, distincts et sans imbrication. Les chemins contenant des composants `.` ou `..`, des doubles barres ou une barre finale sont refusés pour éviter un contournement du contrôle de confinement. Le point d'entrée Umbriel charge ses modules et lance `noctalia` une seule fois ; aucune seconde unité de démarrage Noctalia n'est activée. Les autres dossiers de configuration restent en place.

`/etc/greetd/config.toml` utilise la console virtuelle 1, le compte système `greeter` et `/usr/bin/noctalia-greeter-session`. Le compte et les exécutables attendus doivent être fournis par les paquets. Le helper officiel initialise l'état de Greeter avec `GREETER_USER=greeter` explicite, puis le fichier déclaratif est installé en mode `0600` sous ce compte. Le script n'ajoute aucune règle PAM ni autorisation de synchronisation sans mot de passe. Le module `35-clock.toml` active une horloge au-dessus du panneau, avec heure sur 24 heures (`{:%H:%M}`) et jour/date selon la locale (`%A, %x`). Ces champs sont confirmés dans l'exemple officiel Greeter 1.7.0 ; le script exige cette version au minimum avant de remplacer les profils.

Le script active `greetd.service` et `NetworkManager.service`, sélectionne `graphical.target` et active les unités utilisateur `pipewire.socket`, `pipewire-pulse.socket`, `wireplumber.service` et `gnome-keyring-daemon.socket` pour les prochains démarrages de leurs gestionnaires. Il ne démarre pas greetd immédiatement, ne relance ni réseau ni audio et ne redémarre pas l'ordinateur. Il ne change pas les connexions réseau, Bluetooth, les pilotes, les disques ni un autre bureau. Les paramètres du clavier sont appliqués à la session et au Greeter. Greeter sélectionne Umbriel par défaut et conserve `allow_empty_password = false`.

Les connexions NetworkManager déjà configurées restent en place ; aucune clé Wi-Fi n'est copiée dans le dépôt. Au premier accès aux fonctions chiffrées de Noctalia, créer ou déverrouiller le trousseau via ses dialogues. Seahorse (« Mots de passe et clés ») permet de choisir la collection par défaut. Le script n'enregistre aucun mot de passe et n'ajoute pas de déverrouillage automatique par PAM : une demande de déverrouillage peut donc réapparaître après connexion. Tant que la collection par défaut reste verrouillée, les historiques fonctionnent uniquement pour la session. Les comptes de calendrier et autres identifiants personnels se configurent ensuite dans l'interface.

Le [portail Umbriel](https://github.com/noctalia-dev/xdg-desktop-portal-umbriel) est installé depuis les dépôts pour le partage d'écran, avec le portail GTK pour les fonctions complémentaires. Le partage effectif reste à vérifier dans une session réelle et dans les applications utilisées.

## Premier lancement et validation réelle

Si le script s'arrête, conserver le premier message d'erreur et le chemin de sauvegarde affiché. Corriger sa cause avant de relancer ; ne pas ajouter `--replace-config` pour contourner un problème de service, de réseau ou de validation.

| Blocage ou symptôme | Vérification utile |
| --- | --- |
| Profil déjà présent | Comparer les fichiers ; décider ensuite d'un remplacement complet avec sauvegarde. |
| Autre bureau, gestionnaire de connexion ou de réseau | Examiner la configuration existante ; une migration est une intervention distincte. |
| Paquet absent ou version Greeter insuffisante | Examiner les dépôts et versions affichés ; aucune installation AUR de repli. |
| Récupération Kitty impossible | Examiner réseau, GitHub et diagnostic ; les paquets peuvent déjà avoir été mis à jour, les profils ne sont pas remplacés à cette étape. |
| Avertissement ou erreur de validation | Lire les journaux `validation-before-copy/` ou `validation-installed/` de la sauvegarde. |
| Noctalia ignore un réglage du dépôt | Vérifier les réglages GUI prioritaires et les inclusions, selon le [guide de configuration](configuration.md#réglages-de-linterface-noctalia). |


Après succès, redémarrer manuellement pour vérifier le chemin complet **démarrage → Greeter → Umbriel → Noctalia**. Dans Greeter, la session **Umbriel** est sélectionnée par défaut. Un essai préalable depuis la TTY reste possible avec `start-umbriel`, mais ne vérifie pas l'authentification et les services au démarrage.

Les [raccourcis et réglages quotidiens](configuration.md#utilisation-quotidienne-dumbriel) sont regroupés dans le guide de configuration.

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

## Vérifications du dépôt

Les outils Python sont des auxiliaires du script principal ; ils ne remplacent pas sa confirmation, ses sauvegardes ou son déploiement.

| Outil | Rôle et utilisation |
| --- | --- |
| [profiles.py](../scripts/profiles.py) | Mises à jour ciblées, diagnostic et restauration utilisateur ; voir le [guide de maintenance](maintenance.md). L’installateur utilise aussi sa commande `compare` pour lire les différences avant un remplacement complet. |
| [noctalia_dotfiles.py](../scripts/noctalia_dotfiles.py) | Préparer les copies, remplacer les marqueurs du clavier et contrôler TOML/inclusions. `--check` seul vérifie les sources locales sans écriture ni réseau. Le script principal gère les dossiers temporaires et les validations natives. |
| [kitty_source.py](../scripts/kitty_source.py) | Récupérer et contrôler le profil Kitty pour l'outil de préparation. Ce module n'est pas un installateur ni une commande de synchronisation autonome. |

```bash
bash -n scripts/umbriel_setup.sh
python3 -B tests/test_umbriel_setup.py
# Sur Python >= 3.11, contrôle TOML de tous les modules sans écriture :
python3 -B scripts/noctalia_dotfiles.py --check --keyboard ca
```

Les tests isolent les chemins personnels et interdisent l'appel aux outils de modification pendant les modes de consultation. Ils contrôlent les modules TOML, inclusions et claviers, les refus d'arguments, la provenance avec un faux pacman et les conflits réseau avec un faux systemctl. Une fixture vérifie le remplacement des profils et les sauvegardes. Des sorties natives simulées vérifient que les avertissements et erreurs bloquent l'application. Les inclusions PAM sont vérifiées dans un dossier temporaire. Les tests emploient `tomllib` ou, sur le Python 3.9 local, le parseur TOML déjà livré avec pip ; aucun parseur n'a été installé. Sur CachyOS, l'outil de préparation utilise le `tomllib` du paquet Python actuel. Ces tests ne constituent ni une exécution de pacman/systemd, ni une validation des binaires Linux ou du matériel.

Contrôles effectués sur macOS le 17 novembre 2026 : syntaxe Bash correcte et **77 tests réussis, aucun ignoré** (28 bureau, 12 SSH/disques, 12 récupération Kitty, 22 maintenance et 3 documentation), dont l'analyse de tous les modules TOML. Les tests supplémentaires vérifient les références des applications, les outils d'archives, les chemins XDG ambigus ou imbriqués et les instances dhcpcd actives sans activation persistante ; l'échec de leur diagnostic bloque aussi l'application. La vérification datée du 10 novembre conserve ses résultats historiques. Les validateurs natifs seront exécutés par le script sur CachyOS avant l'activation des services. Aucune installation ni activation n'a été exécutée ici ; le parcours graphique complet reste à valider sur la cible.
