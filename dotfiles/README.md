# Configurations modulaires du bureau

Ces fichiers sont préparés pour **Umbriel + Noctalia v5 + Noctalia Greeter**, après une installation CachyOS « No Desktop ». Ils sont copiés par `scripts/umbriel_setup.sh --apply`, après aperçu, confirmation et sauvegarde. Leur présence ici n'active rien sur cet ordinateur.

## Modules et destinations

| Source | Destination sur la cible | Rôle |
| --- | --- | --- |
| `user/umbriel/config.toml` | `$XDG_CONFIG_HOME/umbriel/config.toml` | Point d'entrée avec inclusions natives. |
| `user/umbriel/cfg/autostart.toml` | `umbriel/cfg/` sous le dossier de configuration | Démarrage unique de Noctalia et modificateur Super. |
| `user/umbriel/cfg/input.toml` | même dossier | Clavier paramétrable et pavé tactile. |
| `user/umbriel/cfg/display.toml` | même dossier | Détection automatique ; exemple commenté pour les écrans. |
| `user/umbriel/cfg/layout.toml` | même dossier | Disposition défilante et espacement. |
| `user/umbriel/cfg/appearance.toml` | même dossier | Bordures, coins et flou. |
| `user/umbriel/cfg/rules.toml` | même dossier | Fenêtres Noctalia et portail flottantes, flou des panneaux. |
| `user/umbriel/cfg/keybinds.toml` | même dossier | Applications, fenêtres, verrouillage et captures. |
| `user/umbriel/cfg/workspaces.toml` | même dossier | Neuf espaces et déplacement des fenêtres. |
| `user/umbriel/cfg/media.toml` | même dossier | Volume, lecture multimédia et luminosité. |
| `user/noctalia/config.toml` et `cfg/` | `$XDG_CONFIG_HOME/noctalia/` | Barre, widgets, shell, palette intégrée, captures, accessibilité et suivi système. |
| `user/kitty/kitty.conf` et `cfg/` | `$XDG_CONFIG_HOME/kitty/` | Terminal : apparence et comportement. |
| `user/xdg-desktop-portal/umbriel-portals.conf` | `$XDG_CONFIG_HOME/xdg-desktop-portal/` | Portail Umbriel pour les captures et le partage ; GTK pour le reste. |
| `user/mimeapps.list` | `$XDG_CONFIG_HOME/mimeapps.list` | Firefox, Thunar et Mousepad comme applications par défaut. |
| `system/greetd/config.toml` | `/etc/greetd/config.toml` | Lancement du wrapper de Greeter sur la console 1. |
| `system/noctalia-greeter/*.toml` | assemblés dans `/var/lib/noctalia-greeter/greeter.toml` | Session Umbriel, clavier, apparence et authentification ; paramètres compatibles Greeter 1.6.0. |

Sans variable XDG, le dossier de configuration est `~/.config`. Le déploiement est limité aux dossiers XDG situés sous le dossier personnel. Pour Greeter, aucune inclusion native n'étant documentée, les modules numérotés sont assemblés dans l'ordre dans un seul fichier lors de la préparation. Umbriel, Noctalia et Kitty gardent leurs fichiers séparés sur la machine cible.

## Personnaliser

- Modifier les modules du dépôt pour versionner ses choix, puis examiner `--print-config` et `--plan` avant une nouvelle application.
- Les marqueurs `@KEYBOARD@` et `@VARIANT@` sont remplacés **dans les copies préparées** par les options du script ; les sources restent inchangées. Le clavier est identique dans la session et à la connexion.
- Pour les écrans, ne pas recopier un connecteur d'exemple. Utiliser `umbriel outputs` sur la cible. Un fichier personnel `umbriel/local.toml` peut compléter ou remplacer les réglages des modules, grâce à une inclusion optionnelle. Il n'est pas créé par le dépôt.
- Les réglages faits dans l'interface Noctalia sont enregistrés dans `~/.local/state/noctalia/settings.toml` (ou le dossier XDG de données d'état). Ils ont priorité sur les modules. Avec `--replace-config`, le script les sauvegarde puis les retire du chemin actif ; ils ne sont pas fusionnés.
- Une réapplication remplace les profils gérés **en entier**, y compris un éventuel `local.toml` actif, après sauvegarde. Restaurer ensuite les personnalisations souhaitées depuis la sauvegarde et revalider la configuration.
- Les captures vont dans le presse-papiers par défaut : aucun dossier personnel ni service d'envoi d'images n'est imposé. Le raccourci `Print` capture une région ; `Shift+Print` capture l'écran.
- `noctalia/cfg/accessibility.toml` fixe l'échelle des interfaces hors barre à `1.20` (+20 %). La barre et les écrans gardent leurs propres réglages. Revenir à `1.0` dans ce module pour l'échelle par défaut de Noctalia.
- `noctalia/cfg/monitoring.toml` fixe les relevés GPU à `2.0` secondes lorsqu'ils sont affichés, sans ajouter de widget à la barre. Revenir à `5.0` pour l'intervalle par défaut ou choisir `0` pour désactiver ces relevés.
- La palette intégrée et la couleur de repli du fond ne nécessitent aucun fichier personnel ni téléchargement d'image. Les images personnelles et les choix de synchronisation Greeter peuvent être ajoutés ensuite.

## Base disponible après installation

Kitty, Firefox, Thunar et Mousepad sont installés et accessibles par raccourcis. Les profils configurent les fenêtres, espaces, notifications, barre système, presse-papiers, verrouillage, captures et portails. L'audio PipeWire/WirePlumber est activé pour l'utilisateur au prochain démarrage de son gestionnaire de services ; le script n'arrête aucun service audio en cours.

Le réseau Internet doit déjà fonctionner avant l'installation. NetworkManager est installé et activé au prochain démarrage pour les contrôles réseau de Noctalia. Les connexions et le réseau actif restent en place ; un autre gestionnaire actif ou activé bloque la procédure pour éviter une migration implicite. GNOME Keyring et Seahorse fournissent le trousseau de secrets et son interface. Le socket utilisateur du trousseau est activé ; sa collection par défaut doit être créée et déverrouillée via ses dialogues. Le script ne demande ni n'enregistre le mot de passe du trousseau et ne modifie pas PAM pour le déverrouiller automatiquement.

Bluetooth et les profils d'énergie restent les choix du système cible. Les fonctionnalités de luminosité, audio, verrouillage et partage d'écran dépendent aussi du matériel et restent à vérifier sur CachyOS. Tant que le trousseau n'est pas déverrouillé, les historiques chiffrés de Noctalia restent limités à la session. La [vérification documentaire](../docs/verification-noctalia-2026-11-10.md) détaille les contrôles et les limites.

## Provenance

Fichiers rédigés pour ce dépôt. L'organisation en point d'entrée et modules s'inspire de [cachyos-niri-noctalia](https://github.com/CachyOS/cachyos-niri-noctalia/tree/master/etc/skel/.config/niri), référence d'organisation sous GPL-3.0 ; ses configurations KDL ne sont pas copiées ou installées. Aucun paquet Niri ou Hyprland n'est ajouté.

La syntaxe et les actions sont fondées sur la documentation officielle d'[Umbriel](https://docs.noctalia.dev/umbriel/), de [Noctalia](https://docs.noctalia.dev/noctalia/configuration/) et de [Greeter](https://docs.noctalia.dev/greeter/configuration/), ainsi que sur les [inclusions Kitty](https://sw.kovidgoyal.net/kitty/conf/). Les projets Noctalia concernés sont distribués sous licence MIT. Les paquets installés conservent leurs propres licences ; aucune ressource tierce n'est embarquée.

Le [guide d'installation et de restauration](../docs/noctalia.md) décrit les sauvegardes et les limites de validation.
