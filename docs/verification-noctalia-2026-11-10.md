# Vérification de l'installation Noctalia après « No Desktop »

Vérification documentaire et locale du 10 novembre 2026. Le parcours préparé est : **installation complète de CachyOS sans bureau → console utilisateur → script avec confirmation → redémarrage manuel → Greeter → Umbriel avec Noctalia**.

Les configurations ont été comparées aux documentations officielles et, pour les écarts entre documentation rolling et paquets, aux sources des versions relevées. La préparation couvre le bureau et les applications de base. Le parcours graphique sur une installation CachyOS réelle n'a pas été exécuté depuis cette machine macOS.

## Recommandations vérifiées

| Sujet | Constat et traitement dans le dépôt | Référence primaire |
| --- | --- | --- |
| Installation par paquets | `noctalia`, `umbriel`, `noctalia-greeter` et le portail sont demandés à pacman dans les dépôts configurés. Provenance affichée et sauvegardée ; aucun assistant AUR. | [Catalogue CachyOS](https://packages.cachyos.org/) et [installation Noctalia](https://docs.noctalia.dev/noctalia/getting-started/installation/). |
| Session Umbriel | La session du paquet passe par `start-umbriel`. Le script vérifie les unités de session et `Type=notify`, qui assure l'ordre de démarrage des portails. Il n'invente aucun override systemd. | [Installation et démarrage Umbriel](https://docs.noctalia.dev/umbriel/installation/) et [unité de la révision 2952bbc](https://github.com/noctalia-dev/umbriel/blob/2952bbc/data/umbriel.service.in). |
| Démarrage du shell | `general.autostart = ["noctalia"]` ; aucune seconde unité Noctalia activée. | [Intégration Noctalia/Umbriel](https://docs.noctalia.dev/noctalia/compositor-settings/umbriel/). |
| Modules Umbriel | Inclusions relatives requises et inclusion personnelle optionnelle, tables de raccourcis réparties sans doublons. Clavier et disposition défilante utilisent les champs documentés. Aucune identité d'écran ou de GPU imposée. | [Configuration Umbriel](https://docs.noctalia.dev/umbriel/configuration/), [entrée](https://docs.noctalia.dev/umbriel/input/) et [disposition](https://docs.noctalia.dev/umbriel/layout/). |
| Animation et flou | Animation des couches laissée désactivée. Correction du flou : seuil alpha, puis flou non optimisé pour les panneaux au-dessus des fenêtres ; la barre garde le chemin optimisé. | [Règles de couches](https://docs.noctalia.dev/umbriel/layer-rules/) et [intégration](https://docs.noctalia.dev/noctalia/compositor-settings/umbriel/). |
| Raccourcis | Commandes IPC documentées. Lancements, captures et bascules ponctuelles sans répétition. Ajout du sélecteur Alt+Tab et du raccourci de sortie de l'inhibition. Les commandes de volume restent répétables. | [Raccourcis Umbriel](https://docs.noctalia.dev/umbriel/keybinds/). |
| Configuration Noctalia | Point d'entrée TOML et modules inclus. Les paramètres modifiés par l'interface sont prioritaires : le script les sauvegarde et les met à l'écart uniquement lors d'un remplacement autorisé. | [Configuration Noctalia](https://docs.noctalia.dev/noctalia/configuration/). |
| Greeter et greetd | `default_session.command` lance le wrapper `noctalia-greeter-session`, avec le compte `greeter`. Le helper officiel initialise l'état sous ce compte explicite. Le fichier déclaratif appartient au greeter et la session par défaut est le nom `Umbriel`. | [Installation Greeter](https://docs.noctalia.dev/greeter/installation/) et [configuration](https://docs.noctalia.dev/greeter/configuration/). |
| Compatibilité Greeter 1.6.0 | Écart confirmé : les paramètres `[clock]` de la documentation rolling n'existent pas dans la version 1.6.0 relevée dans CachyOS. Ils ont été retirés ; les autres paramètres utilisés sont présents dans cette version. | [Exemple Greeter v1.6.0](https://github.com/noctalia-dev/noctalia-greeter/blob/v1.6.0/examples/greeter.toml) et [lecture des paramètres](https://github.com/noctalia-dev/noctalia-greeter/blob/v1.6.0/src/greeter/greeter_config_io.cpp). |
| Session et PAM | Vérification que les inclusions de session de greetd rejoignent `pam_systemd.so`. Aucun patch PAM automatique : les inclusions de la distribution sont prises en compte. | [Préparation amont du runtime greetd](https://github.com/noctalia-dev/noctalia-greeter/blob/main/scripts/setup_greetd_pam.sh) et [fichiers du paquet greetd](https://archlinux.org/packages/extra/x86_64/greetd/files/). |
| Portails | Backend Umbriel pour ScreenCast, Screenshot et InputCapture ; GTK pour les interfaces complémentaires. Le portail relevé expose bien ces trois interfaces. PipeWire/WirePlumber sont présents. | [Interface du portail révision 17739df](https://github.com/noctalia-dev/xdg-desktop-portal-umbriel/blob/17739df/data/umbriel.portal). |
| Réseau | Lacune corrigée : ajout de NetworkManager, utilisé par le contrôle réseau de Noctalia. Activation au prochain démarrage et conservation des connexions ; conflit bloquant si un autre gestionnaire est actif ou activé. | [Widget réseau Noctalia](https://docs.noctalia.dev/noctalia/bar/widgets/network/), [administration NetworkManager](https://networkmanager.dev/docs/admins/) et [paquet](https://packages.cachyos.org/package/extra/x86_64/networkmanager). |
| Secrets et historiques | Lacune corrigée : ajout de GNOME Keyring et Seahorse, et activation du socket utilisateur. La collection par défaut doit être créée/déverrouillée par l'utilisateur. Aucun mot de passe généré, versionné ou demandé par le script ; pas de déverrouillage PAM ajouté. | [Secret Service Noctalia](https://docs.noctalia.dev/noctalia/configuration/secret-service/) et [paquet GNOME Keyring](https://packages.cachyos.org/package/extra/x86_64/gnome-keyring). |
| Vérification avant activation | Ajout d'une validation native des copies préparées **avant remplacement**. Avertissements Noctalia et diagnostics Umbriel deviennent bloquants. Nouvelle validation après copie, puis activation des services ; journaux conservés même en cas d'échec de ces contrôles. | [Validation Noctalia](https://docs.noctalia.dev/noctalia/configuration/#validating-your-configuration) et [diagnostics Umbriel](https://docs.noctalia.dev/umbriel/configuration/#diagnostics). |

Les options visuelles, raccourcis choisis, police, navigateur et gestionnaire de fichiers constituent des choix de ce dépôt. Ce ne sont pas des prérequis imposés par Noctalia. Les délais d'inactivité restent aux valeurs par défaut ; aucune politique de veille automatique n'est imposée. La synchronisation de l'apparence vers Greeter reste désactivée tant que l'utilisateur ne la configure pas.

## Compatibilité des versions

Les références de paquets relevées sont Noctalia `5.4.1-1`, Umbriel `0.1.0.r1459.2952bbc-1`, Greeter `1.6.0-1` et portail Umbriel `0.1.0.r69.17739df-1`. Elles servent à expliquer les choix, pas à figer l'installation : pacman installe les versions disponibles dans les dépôts de la cible.

Les réglages Noctalia ont également été rapprochés du [schéma de la version v5.4.1](https://github.com/noctalia-dev/noctalia/blob/v5.4.1/src/config/schema/config_schema.cpp). Les champs généraux et de disposition d'Umbriel sont présents dans les sources de la révision `2952bbc`. Le script vérifiera les schémas réellement installés, ce qui reste nécessaire lorsque ces paquets évoluent. Greeter ne dispose pas ici d'un validateur natif équivalent : son fichier est analysé comme TOML et comparé aux paramètres de la version citée.

## Vérifications effectivement exécutées

- Syntaxe Bash et compilation syntaxique du code Python, sans installation de dépendance.
- **22 tests réussis, aucun ignoré** : modes de consultation sans écriture personnelle ni appel privilégié, refus d'arguments et de cible incompatible, provenance simulée, détection des conflits réseau, analyse TOML complète et inclusions, claviers identiques, préparation isolée, remplacement avec sauvegarde, conservation des fichiers hors périmètre et lecture des inclusions PAM.
- Des sorties de validateurs simulées vérifient le blocage sur erreur ou avertissement, y compris quand Noctalia retourne zéro. Elles ne constituent pas une exécution des binaires Linux.
- Les tests TOML utilisent le parseur déjà présent avec pip sur le Python local 3.9. Sur CachyOS, le programme de préparation utilise `tomllib` du paquet Python actuel. Aucun nouveau parseur n'a été installé ici.

Ni pacman, ni les services de la cible, ni le greeter graphique, ni un montage ou une installation de pilote n'ont été exécutés. Les versions affichées par les catalogues et les sources ne prouvent pas à elles seules le résultat d'une transaction sur la cible.

## Parcours à valider sur CachyOS

Suivre le [guide d'installation](noctalia.md), avec la copie complète de ce dépôt et le clavier adapté. Après succès du script, redémarrer manuellement et vérifier :

1. Greeter apparaît, utilise le bon clavier et permet la connexion au compte existant dans Umbriel.
2. Noctalia démarre une seule fois ; terminal, navigateur, gestionnaire de fichiers et éditeur s'ouvrent par leurs raccourcis et le lanceur.
3. Les écrans, le pavé tactile et les espaces fonctionnent ; les paramètres propres au matériel peuvent être complétés après `umbriel outputs`.
4. Le réseau déjà configuré revient et les contrôles réseau fonctionnent. Aucun secret de connexion ne doit être ajouté au dépôt.
5. La création ou le déverrouillage de la collection par défaut du trousseau se fait via les dialogues ou Seahorse. Vérifier ensuite la persistance des historiques après reconnexion. Sans modification PAM, un nouveau déverrouillage peut être demandé.
6. Audio, volume, captures dans le presse-papiers, notifications, verrouillage **et déverrouillage** fonctionnent. Vérifier enfin le partage d'écran dans une application et le retour à Greeter après déconnexion.

Ces essais restent nécessaires pour annoncer un poste effectivement validé. Une analyse des fichiers sur macOS ne prouve pas la compatibilité du GPU, l'authentification ou le démarrage de cette installation CachyOS.
