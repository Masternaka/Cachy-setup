# Personnaliser et utiliser le bureau

[Accueil](../README.md) · [Installer ou restaurer le bureau](noctalia.md)

Ces fichiers sont préparés pour **Umbriel + Noctalia v5 + Noctalia Greeter**, après une installation CachyOS « No Desktop ». Ils sont copiés par `scripts/umbriel_setup.sh --apply`, après aperçu, confirmation et sauvegarde. Leur présence ici n'active rien sur cet ordinateur.

## Dans ce guide

- [Modules et destinations](#modules-et-destinations)
- [Personnaliser : clavier, écrans, Kitty et Noctalia](#personnaliser)
- [Barre et comportement de Noctalia](#utilisation-quotidienne-de-noctalia)
- [Raccourcis et applications](#utilisation-quotidienne-dumbriel)
- [Provenance](#provenance)

## Modules et destinations

Les chemins locaux de la colonne Source sont relatifs à [dotfiles/](../dotfiles/).

| Source | Destination sur la cible | Rôle |
| --- | --- | --- |
| `user/umbriel/config.toml` | `$XDG_CONFIG_HOME/umbriel/config.toml` | Point d'entrée avec inclusions natives. |
| `user/umbriel/cfg/autostart.toml` | `umbriel/cfg/` sous le dossier de configuration | Démarrage unique de Noctalia et modificateur Super. |
| `user/umbriel/cfg/input.toml` | même dossier | Clavier paramétrable, pavé numérique, pavé tactile, focus et curseur. |
| `user/umbriel/cfg/display.toml` | même dossier | Deux écrans personnels : DP-1 à gauche, HDMI-A-2 à droite, 1920 × 1080 à 60 Hz, échelle 100 %. |
| `user/umbriel/cfg/layout.toml` | même dossier | Disposition défilante et espacement. |
| `user/umbriel/cfg/appearance.toml` | même dossier | Bordures, coins, flou optimisé et barres de titre négociées. |
| `user/umbriel/cfg/rules.toml` | même dossier | Fenêtres Noctalia et portail flottantes, flou des panneaux. |
| `user/umbriel/cfg/keybinds.toml` | même dossier | Applications, fenêtres, passage entre écrans, tailles, onglets, aide, verrouillage et captures. |
| `user/umbriel/cfg/workspaces.toml` | même dossier | Dix espaces fixes : 1 à 5 sur DP-1, 6 à 10 sur HDMI-A-2 ; sélection et déplacement des fenêtres. |
| `user/umbriel/cfg/media.toml` | même dossier | Volume, lecture multimédia et luminosité. |
| `user/noctalia/config.toml` et `cfg/` | `$XDG_CONFIG_HOME/noctalia/` | Barre, widgets, shell, palette intégrée, captures, accessibilité et suivi système. |
| [CachyOS — Dotfiles/kitty/.config/kitty](https://github.com/Masternaka/CachyOS/tree/main/Dotfiles/kitty/.config/kitty) | `$XDG_CONFIG_HOME/kitty/` | Profil récupéré depuis `main` par une opération explicitement demandée ; copie complète avec thèmes et provenance, remplacement après confirmation. Aucun profil Kitty en double dans ce dépôt. |
| `user/xdg-desktop-portal/umbriel-portals.conf` | `$XDG_CONFIG_HOME/xdg-desktop-portal/` | Portail Umbriel pour les captures et le partage ; GTK pour le reste. |
| `user/mimeapps.list` | `$XDG_CONFIG_HOME/mimeapps.list` | Firefox, Thunar, Zed, Papers, Loupe et mpv comme applications par défaut selon le type de fichier. |
| `system/greetd/config.toml` | `/etc/greetd/config.toml` | Lancement du wrapper de Greeter sur la console 1. |
| `system/noctalia-greeter/*.toml` | assemblés dans `/var/lib/noctalia-greeter/greeter.toml` | Session Umbriel, clavier, apparence, horloge et authentification ; Greeter 1.7.0 minimum. |

Sans variable XDG, le dossier de configuration est `~/.config`. Le déploiement est limité aux dossiers XDG situés sous le dossier personnel, distincts et sans imbrication. Les composants `.` et `..`, doubles barres et barres finales sont refusés dans ces chemins. Pour Greeter, aucune inclusion native n'étant documentée, les modules numérotés sont assemblés dans l'ordre dans un seul fichier lors de la préparation. Umbriel, Noctalia et Kitty gardent leurs fichiers séparés sur la machine cible. La récupération Kitty est détaillée dans le [guide](noctalia.md#kitty-depuis-le-dépôt-cachyos).

## Personnaliser

La modification des sources du dépôt ne change pas le profil actif : le script installe des **copies**, sans lien symbolique vers le dépôt. Depuis sa racine, vérifier les changements avant de préparer une nouvelle application :

```bash
bash scripts/umbriel_setup.sh --print-config
bash scripts/umbriel_setup.sh --plan
# Avec Python >= 3.11 déjà disponible : contrôle local sans écriture ni réseau.
python3 -B scripts/noctalia_dotfiles.py --check --keyboard ca
```

`--print-config` rassemble plusieurs fichiers pour lecture ; ne pas rediriger sa sortie vers un fichier de configuration actif. Il n'affiche pas le contenu distant de Kitty. Pour un bureau déjà installé, suivre la [maintenance ciblée](maintenance.md), avec différences, confirmation et sauvegarde. Le [guide d’installation](noctalia.md#aperçu-et-application) concerne le déploiement complet.

### Kitty

Pour Kitty, modifier le profil dans le dépôt CachyOS et publier les changements sur `main`. La prochaine application confirmée récupère ce profil. La [commande ciblée Kitty](maintenance.md#appliquer-un-seul-profil) ne remplace que ce dossier après sauvegarde ; `--replace-config` reste l’option de remplacement global de l’installateur. `--print-config` affiche les fichiers locaux et la référence Kitty, sans accéder au réseau. La police JetBrainsMono Nerd Font est prévue dans les paquets. Les inclusions `~/.config/kitty/...` sont rendues relatives dans les copies ; les autres réglages et commentaires restent ceux de la source.

### Clavier

Les marqueurs `@KEYBOARD@` et `@VARIANT@` sont remplacés **dans les copies préparées** par les options du script ; les sources restent inchangées. Le défaut est le canadien français : `layout = "ca"`, `variant = ""`, identique dans la session et à la connexion. `--keyboard ca --variant multix` sélectionne le canadien multilingue/CSA. Le clavier de la console TTY reste inchangé.

### Écrans

Le module des écrans cible le matériel personnel indiqué : DP-1 à gauche en `[0, 0]` et HDMI-A-2 à droite en `[1920, 0]`, tous deux en `1920x1080@60`, échelle `1.0`, orientation normale, HDR et VRR désactivés. Les deux écrans sont alignés en haut, sans espace entre eux. Utiliser `umbriel outputs` sur la cible pour confirmer les connecteurs et modes ; adapter ce module pour une autre machine. Le GPU reste détecté automatiquement. Un fichier personnel `umbriel/local.toml` peut compléter ou remplacer les réglages des modules, grâce à une inclusion optionnelle. Il n'est pas créé par le dépôt.

### Espaces de travail

Le module `workspaces.toml` complète les tables des écrans avec cinq espaces fixes chacun : noms `1` à `5` à gauche, `6` à `10` à droite. `Super+1…9` sélectionne l'espace correspondant ; `Super+0` sélectionne le 10. Ajouter `Maj` déplace la fenêtre courante vers cet espace. Les commandes utilisent `--name` et `--output` pour cibler le nom numérique sur le bon écran, indépendamment du focus courant. Les espaces fixes restent présents lorsqu'ils sont vides.

### Réglages de l’interface Noctalia

Les réglages faits dans l'interface Noctalia sont enregistrés dans `~/.local/state/noctalia/settings.toml` (ou le dossier XDG de données d'état). Ils ont priorité sur les modules. Avec `--replace-config`, le script les sauvegarde puis les retire du chemin actif ; ils ne sont pas fusionnés. La mise à jour ciblée Noctalia les conserve par défaut ; `--reset-gui` autorise leur retrait après sauvegarde, selon le [guide de maintenance](maintenance.md#appliquer-un-seul-profil).

### Remplacement des profils

Une réapplication avec l’installateur complet remplace les profils gérés **en entier**, y compris un éventuel `local.toml` actif, après sauvegarde. Restaurer ensuite les personnalisations souhaitées depuis la sauvegarde et revalider la configuration.

### Captures

Les captures vont dans le presse-papiers par défaut : aucun dossier personnel ni service d'envoi d'images n'est imposé. Le raccourci `Print` sélectionne une région dans l'image figée, avec dimensions visibles et confirmation par Entrée/Espace ; `Shift+Print` capture l'écran.

### Échelle des interfaces

`noctalia/cfg/accessibility.toml` prépare une échelle des interfaces hors barre de `1.20` (+20 %), mais son inclusion est actuellement commentée dans `noctalia/config.toml`. Décommenter cette ligne pour l'utiliser. La barre et les écrans gardent leurs propres réglages. La valeur intégrée de Noctalia est `1.0`.

### Statistiques GPU

`noctalia/cfg/monitoring.toml` prépare un intervalle GPU de `2.0` secondes, mais son inclusion est actuellement commentée. Décommenter cette ligne pour l'utiliser lorsque des statistiques GPU sont affichées ; aucun widget n'est ajouté. La valeur intégrée est `5.0` secondes ; `0` désactive les relevés GPU.

### Thème et fond

La palette intégrée et la couleur de repli du fond ne nécessitent aucun fichier personnel ni téléchargement d'image. Les images personnelles et les choix de synchronisation Greeter peuvent être ajoutés ensuite.

### Horloge de connexion

Le module Greeter `35-clock.toml` active l'horloge au-dessus du panneau : heure sur 24 heures et jour/date selon la locale de Greeter. Ses réglages sont présents dans l'exemple officiel 1.7.0 ; le script refuse un paquet installé plus ancien avant de copier les profils. Le clavier canadien français ne sélectionne pas la langue des dates. Pour revenir à la configuration sans horloge explicite, retirer le module du dépôt puis préparer de nouveau les copies ; les réglages intégrés du paquet s'appliquent alors.

## Utilisation quotidienne de Noctalia

Revue du 17 novembre 2026 fondée sur la documentation versionnée [Shell 5.4.1](https://docs.noctalia.dev/noctalia/v5.4.1/configuration/shell/), [workspaces](https://docs.noctalia.dev/noctalia/v5.4.1/bar/widgets/workspaces/), [fenêtre active](https://docs.noctalia.dev/noctalia/v5.4.1/bar/widgets/active-window/), [médias](https://docs.noctalia.dev/noctalia/v5.4.1/bar/widgets/media/) et [privacy](https://docs.noctalia.dev/noctalia/v5.4.1/bar/widgets/privacy/). La [fiche CachyOS](https://packages.cachyos.org/package/extra/x86_64/noctalia) consultée indique encore `5.4.1-1` ; les sections barre, verrouillage, notifications et OSD ont aussi été rapprochées du [schéma v5.4.1](https://github.com/noctalia-dev/noctalia/blob/v5.4.1/src/config/schema/config_schema.cpp). Les versions disponibles restent résolues sur la cible.

| Module | Choix préparés |
| --- | --- |
| `bar.toml` | Barre supérieure visible de 34 pixels, espace réservé, infobulles et témoin de capture. |
| `widgets.toml` | Noms des cinq espaces de chaque écran, même vides ; titres bornés et lisibles au survol. Le témoin disparaît au repos et indique les captures détectées par PipeWire. |
| `shell.toml` | Favoris Firefox, Thunar, Zed, Papers, Loupe et mpv ; Alt+Tab par utilisation récente sur les deux écrans et tous les espaces. |
| `capture.toml` | Image figée, dimensions et aide visibles ; confirmer la région avec Entrée/Espace. Copie au presse-papiers conservée. |
| `theme.toml` | Palette sombre Noctalia et fond uni conservés. |
| `accessibility.toml` | Échelle `1.20` préparée, inclusion commentée. |
| `monitoring.toml` | Intervalle GPU `2.0` préparé, inclusion commentée. |

Les confirmations du presse-papiers restent actives. Verrouillage avant veille et absence de délai de déverrouillage sans mot de passe sont déclarés explicitement. Notifications et retours volume/luminosité suivent l'écran utilisé ; au maximum trois notifications sont visibles. Aucune synchronisation automatique vers Greeter n'est activée.

Les deux inclusions commentées sont conservées : les valeurs intégrées s'appliquent tant qu'elles ne sont pas réactivées, sous réserve de réglages GUI ou système prioritaires. Les favoris s'ouvrent par `Super+Espace` ; `Super+V` ouvre le presse-papiers. Chaque choix reste modifiable dans son module. Après modification, préparer et valider de nouveau les copies ; la restauration complète suit la [procédure de restauration](noctalia.md#retour-arrière). Les tests locaux ne remplacent pas les validateurs natifs ni les essais réels de barre, de capture et de verrouillage sur CachyOS.

## Utilisation quotidienne d'Umbriel

`Super` désigne généralement la touche Windows du clavier ; `Maj` correspond à Shift. Ces raccourcis sont définis dans [keybinds.toml](../dotfiles/user/umbriel/cfg/keybinds.toml) et [workspaces.toml](../dotfiles/user/umbriel/cfg/workspaces.toml).

| Raccourci | Usage courant |
| --- | --- |
| `Super+Entrée` | Ouvrir Kitty. |
| `Super+F12` | Afficher ou masquer le terminal déroulant Kitty. |
| `Super+B` / `Super+E` / `Super+Maj+E` | Ouvrir Firefox / Thunar / Zed. |
| `Super+Espace` / `Super+S` / `Super+Virgule` | Lanceur / panneau de contrôle / réglages. |
| `Super+V` | Presse-papiers. |
| `Super+Alt+L` / `Super+Échap` | Verrouiller / ouvrir le menu de session. |
| `Print` / `Maj+Print` | Capturer une région avec confirmation / l'écran, dans le presse-papiers. |
| `Super+Q` / `Super+O` | Fermer la fenêtre / afficher la vue d'ensemble. |
| `Super+flèches` / `Super+Maj+flèches` | Changer le focus / déplacer la fenêtre ou colonne. |
| `Super+1…9` / `Super+0` | Espaces 1 à 9 / espace 10 ; ajouter `Maj` pour y envoyer la fenêtre. |
| `Alt+Tab` | Sélecteur Noctalia, tous les espaces et écrans. |
| `Super+Maj+Échap` | Sortir du mode d'inhibition des raccourcis. |


Les neuf modules ont été relus le 17 novembre 2026 avec l'[exemple officiel](https://github.com/noctalia-dev/umbriel/blob/main/examples/config.toml) et les références [Actions](https://docs.noctalia.dev/umbriel/actions/), [Input](https://docs.noctalia.dev/umbriel/input/), [Appearance](https://docs.noctalia.dev/umbriel/appearance/), [Layout](https://docs.noctalia.dev/umbriel/layout/), [Window Rules](https://docs.noctalia.dev/umbriel/window-rules/) et [intégration Noctalia](https://docs.noctalia.dev/noctalia/compositor-settings/umbriel/). Le démarrage unique de Noctalia, le clavier `ca`, les écrans et la répartition des dix workspaces restent conservés. Les ajouts suivants sont des choix d'ergonomie du dépôt ; tous ne sont pas requis pour démarrer Umbriel.

| Raccourci | Action |
| --- | --- |
| `Super+F1` | Afficher l'aide des raccourcis actifs. |
| `Super+Ctrl+R` | Relire la configuration ; Umbriel surveille aussi les fichiers automatiquement. |
| `Super+Ctrl+Gauche/Droite` | Choisir l'écran voisin. |
| `Super+Ctrl+Maj+Gauche/Droite` | Envoyer la fenêtre courante à l'écran voisin. |
| `Super+M` | Basculer la maximisation, en pleine largeur de colonne dans le pavage défilant. |
| `Super+R` / `Super+Maj+R` | Parcourir les tailles prédéfinies, en avant ou en arrière. |
| `Super+Alt+Gauche/Droite` | Réduire/agrandir la largeur par pas de 5 % dans le pavage défilant. |
| `Super+Alt+Haut/Bas` | Réduire/agrandir la hauteur de la fenêtre par pas de 5 %. |
| `Super+C` | Centrer la colonne courante. |
| `Super+Ctrl+Virgule/Point` | Extraire une fenêtre d'une colonne ou l'empiler avec la colonne voisine. |
| `Super+W` | Basculer les fenêtres empilées entre lignes et onglets. |
| `Super+Alt+Page précédente/suivante` | Choisir l'onglet précédent/suivant. |
| `Super+T` / `Super+Maj+T` | Basculer flottant/pavé, ou retrouver le dernier focus de l'autre catégorie. |
| `Super+N` / `Super+Maj+N` | Minimiser une fenêtre flottante éligible / restaurer la dernière minimisée du workspace. |
| `Super+Page précédente/suivante` | Parcourir les cinq workspaces de l'écran courant. |
| `Super+glisser gauche/droit` | Déplacer / redimensionner une fenêtre depuis un bord ou un coin. |

Les commandes natives utilisent le modificateur `Mod`, fixé à Super dans `autostart.toml`. Les commandes ponctuelles ne se répètent pas lorsqu'une touche reste enfoncée ; navigation et redimensionnement restent répétables. Les raccourcis existants du lanceur, de verrouillage, de captures et de sélection des dix workspaces sont conservés.

Les fenêtres qui négocient une décoration serveur disposent d'une barre de titre de 28 pixels avec boutons lisibles ; les applications qui dessinent leur propre en-tête gardent leur préférence. La minimisation reste limitée aux fenêtres éligibles ; les fenêtres pavées ne sont pas masquées par cette commande. Les dimensions initiales des fenêtres Noctalia et du sélecteur de partage sont fixées pour les écrans Full HD. La vidéo incrustée devient flottante lorsque son titre correspond aux expressions de l'exemple officiel. Les animations de panneaux restent gérées par Noctalia et le flou général reste optimisé.

Le pavé numérique est activé au démarrage. Le focus suit le clic ou le clavier ; le curseur accompagne les changements de fenêtre au clavier entre les écrans. Le pavé tactile conserve le tap et le défilement naturel, avec désactivation pendant la frappe si le matériel le prend en charge. Le pavage recentre les colonnes débordantes et la sélection quittant l'aperçu. Les touches audio, lecture et luminosité restent disponibles au verrouillage, comme dans l'exemple officiel ; les autres raccourcis ne sont pas ouverts au verrouillage.

Ces références suivent la branche actuelle ; la version actuelle du paquet CachyOS n'a pas pu être confirmée dans le catalogue lors de cette revue. Les tests locaux contrôlent TOML, inclusions et doublons de raccourcis, sans valider le schéma ni les actions d'un binaire Umbriel installé. Les validateurs natifs prévus avant et après copie restent indispensables. Pour annuler un choix de confort, retirer sa clé ou son raccourci du module puis préparer et valider de nouveau les copies ; la restauration complète des profils actifs suit la [procédure de restauration](noctalia.md#retour-arrière). L'autostart et certains réglages de décoration peuvent demander une nouvelle session ou une relance des applications.

### Applications et terminal

Micro s'utilise dans Kitty avec `micro` ; `pavucontrol` ouvre les réglages audio détaillés. Thunar utilise Papers pour les PDF, Loupe pour les images, mpv pour les médias et Zed pour le texte, selon [mimeapps.list](../dotfiles/user/mimeapps.list). Xarchiver complète les archives ; les accès SMB/MTP et miniatures dépendent des services et appareils disponibles. Le script ne modifie aucun profil Firefox : sélectionner le français dans ses préférences si nécessaire.

`Super+F12` lance `kitten quick-access-terminal` : le premier appui ouvre le terminal déroulant, les suivants le masquent ou le réaffichent, en conservant sa session. La répétition de touche est désactivée pour éviter plusieurs basculements si F12 reste enfoncée. Selon la [documentation Kitty](https://sw.kovidgoyal.net/kitty/kittens/quick-access-terminal/), il utilise `quick-access-terminal.conf` dans le dossier de configuration Kitty ; ce fichier est repris du profil externe lorsqu'il y figure. `Super+Entrée` ouvre le terminal habituel. L'affichage réel reste à vérifier dans la session Umbriel sur CachyOS.

## Provenance

Fichiers rédigés pour ce dépôt. L'organisation en point d'entrée et modules s'inspire de [cachyos-niri-noctalia](https://github.com/CachyOS/cachyos-niri-noctalia/tree/master/etc/skel/.config/niri), référence d'organisation sous GPL-3.0 ; ses configurations KDL ne sont pas copiées ou installées. Aucun paquet Niri ou Hyprland n'est ajouté.

La syntaxe et les actions sont fondées sur la documentation officielle d'[Umbriel](https://docs.noctalia.dev/umbriel/), de [Noctalia](https://docs.noctalia.dev/noctalia/configuration/) et de [Greeter](https://docs.noctalia.dev/greeter/configuration/), ainsi que sur les [inclusions Kitty](https://sw.kovidgoyal.net/kitty/conf/). Les projets Noctalia concernés sont distribués sous licence MIT. Les paquets installés conservent leurs propres licences ; aucune ressource tierce n'est embarquée.

Le [guide d'installation et de restauration](noctalia.md) décrit les sauvegardes et les limites de validation.
