# Cachy-setup

Mes configurations et scripts pour personnaliser mon ordinateur sous **CachyOS**, avec **Umbriel, Noctalia v5 et Noctalia Greeter**. Le bureau se prépare après une installation du système avec le choix **« No Desktop »**.

**Commencer ici**, puis ouvrir le guide correspondant à l'opération souhaitée. Les fichiers du dépôt sont des sources : leur modification ne les installe pas sur l'ordinateur.

## Trouver le bon guide

| Je veux… | Guide |
| --- | --- |
| Installer le bureau, connaître ses paquets ou le restaurer | [Installation Umbriel et Noctalia](docs/noctalia.md) |
| Régler le clavier, les écrans, les espaces, la barre ou le thème | [Configuration du bureau](docs/configuration.md) |
| Mettre à jour uniquement Kitty, Umbriel ou Noctalia | [Maintenance ciblée et différences](docs/maintenance.md) |
| Diagnostiquer le bureau ou restaurer un profil sauvegardé | [Diagnostic et restauration](docs/maintenance.md#diagnostiquer-le-bureau) |
| Consigner les essais réellement faits sur CachyOS | [Fiche de validation](docs/validation-cachyos.md) |
| Retrouver les raccourcis clavier et ouvrir les applications | [Utilisation quotidienne](docs/configuration.md#utilisation-quotidienne-dumbriel) |
| Utiliser ma configuration Kitty du dépôt CachyOS | [Récupération et mises à jour de Kitty](docs/noctalia.md#kitty-depuis-le-dépôt-cachyos) |
| Activer l'accès SSH avec ma configuration existante | [Guide SSH](docs/ssh.md) |
| Préparer mes quatre volumes de données | [Guide des disques](docs/disques.md) |
| Comprendre les contrôles déjà effectués et ceux restant à faire | [Vérifications locales](#vérifications-locales) et [rapport historique du 10 novembre 2026](docs/verification-noctalia-2026-11-10.md) |

## Utiliser les scripts

### 1. Préparer la cible

Copier **le dépôt complet et à jour** sur CachyOS : `scripts/`, `dotfiles/` et les guides sont nécessaires. Copier seulement un fichier `.sh` ne suffit pas pour installer le bureau. Les changements locaux doivent avoir été transférés ; un clone GitHub contient uniquement les changements déjà publiés.

Ouvrir un terminal **dans le dossier Cachy-setup**, à sa racine. Les commandes ci-dessous partent toutes de ce dossier et se lancent sans `sudo` devant le script ; celui-ci le demande au moment prévu.

| Script | Conditions particulières | Effet de l'application |
| --- | --- | --- |
| [umbriel_setup.sh](scripts/umbriel_setup.sh) | CachyOS « No Desktop » installé, compte avec sudo, Internet, pilotes graphiques et console TTY locale hors session graphique. | Mise à jour complète et installation des paquets via pacman, profils du bureau et services activés pour les prochains démarrages. |
| [ssh_setup.sh](scripts/ssh_setup.sh) | OpenSSH et clés d'hôte déjà présents, systemd fonctionnel, terminal local. | Activation et démarrage de `sshd.service` si nécessaire, selon la configuration SSH existante. |
| [disk_setup.sh](scripts/disk_setup.sh) | Compte `gabriel` et quatre UUID ext4 à vérifier, sauvegarde des données, volumes démontés pour l'application. | Labels et propriétaire récursif, groupes conservés ; entrées fstab pour le prochain démarrage. |

SSH et disques sont des opérations indépendantes : **le script du bureau ne les exécute pas**. Lire leur guide avant application, notamment pour les accès réseau SSH et les identifiants des volumes.

### 2. Examiner l'aperçu

Exécuter seulement la commande correspondant à son besoin :

```bash
bash scripts/umbriel_setup.sh --plan
bash scripts/ssh_setup.sh --plan
bash scripts/disk_setup.sh --plan
```

Ces aperçus n'installent rien, n'utilisent pas sudo et n'écrivent aucun fichier. Sans option, les trois scripts affichent aussi leur plan. SSH et disques acceptent également `--dry-run`. Sur macOS, l'application est refusée ; l'inventaire des services et volumes exige la cible CachyOS.

Pour lire les options, remplacer `--plan` par `--help`. Pour examiner les profils locaux du bureau : `bash scripts/umbriel_setup.sh --print-config` ; Kitty reste une référence distante à cette étape, sans téléchargement.

### 3. Appliquer après lecture du guide

| Opération | Commande sur la cible | Confirmation |
| --- | --- | --- |
| Installer le bureau | `bash scripts/umbriel_setup.sh --apply` | `INSTALLER`, puis transaction pacman. |
| Activer SSH | `bash scripts/ssh_setup.sh --apply` | `ACTIVER` si une modification est nécessaire. |
| Préparer les volumes | `bash scripts/disk_setup.sh --apply` | Accord sudo si nécessaire, puis `APPLIQUER`. |

Le bureau utilise par défaut le clavier **canadien français** (`ca`, variante vide), deux écrans Full HD à 60 Hz (**DP-1 à gauche**, **HDMI-A-2 à droite**) et dix espaces (**1–5 à gauche**, **6–10 à droite**). Ces identifiants personnels sont à adapter pour une autre machine.

Pour entretenir un bureau déjà installé, utiliser de préférence la [mise à jour ciblée](docs/maintenance.md), sans transaction pacman :

```bash
python3 -B scripts/profiles.py update kitty --plan
# Aperçu distant explicite, puis application du seul profil Kitty :
python3 -B scripts/profiles.py update kitty --plan --fetch-kitty
python3 -B scripts/profiles.py update kitty --apply
```

Un profil existant bloque l'installation du bureau. L'option `--replace-config` permet une [réapplication complète après sauvegarde](docs/noctalia.md#réappliquer-une-configuration-existante), y compris les réglages GUI Noctalia et les personnalisations actives. Lors de l’installation complète, Kitty et ses thèmes viennent de [CachyOS/main](https://github.com/Masternaka/CachyOS/tree/main/Dotfiles/kitty/.config/kitty) à chaque application confirmée ; aucune synchronisation automatique ne tourne ensuite.

### 4. Vérifier et conserver les sauvegardes

| Opération | Sauvegarde | Vérification et retour arrière |
| --- | --- | --- |
| Bureau | `/var/lib/cachy-setup/noctalia-*` | [Premier lancement](docs/noctalia.md#premier-lancement-et-validation-réelle), puis [restauration](docs/noctalia.md#retour-arrière). Redémarrage manuel après succès. |
| SSH | `/var/lib/cachy-setup/ssh-*` si une action est nécessaire | [État du service, connexion et retour arrière](docs/ssh.md#retour-arrière-et-vérification). Service démarré immédiatement si nécessaire. |
| Disques | `/var/tmp/cachy-setup-disques.*` | [Journal et restauration des métadonnées](docs/disques.md#sauvegarde-et-restauration). Montages persistants au prochain démarrage. |

Conserver le chemin exact affiché par le script. Un arrêt sur erreur peut laisser un état partiel ; aucune restauration automatique ni annulation de la mise à jour des paquets n'est effectuée. Les relevés de métadonnées des volumes ne remplacent pas une sauvegarde de leurs données.

## Organisation du dépôt

| Emplacement | Contenu |
| --- | --- |
| [dotfiles/](dotfiles/) | Sources modulaires Umbriel, Noctalia, Greeter, portails et associations de fichiers ; [carte des modules](docs/configuration.md#modules-et-destinations). |
| [scripts/](scripts/) | Trois scripts principaux, outil de maintenance des profils et auxiliaires Python de préparation/validation. Les outils Python n'installent pas de paquets. |
| [docs/](docs/) | Guides par sujet ; l'ancien README des dotfiles est intégré au guide de configuration. |
| [tests/](tests/) | Tests isolés du bureau, de SSH/disques et de la récupération Kitty. |
| [AGENTS.md](AGENTS.md) | Consignes pour les assistants IA. |

Les procédures détaillées sont maintenues dans leur guide ; ce README sert de point d'entrée commun.

## Vérifications locales

Depuis la racine, sans installer de dépendance ni appliquer les scripts :

```bash
bash -n scripts/umbriel_setup.sh
bash -n scripts/ssh_setup.sh
bash -n scripts/disk_setup.sh
python3 -B -m unittest discover -s tests
python3 -B scripts/check_docs.py
```

Le 17 novembre 2026, les contrôles locaux ont relevé une syntaxe Bash correcte et **77 tests réussis, aucun ignoré**, dont 22 sur la maintenance ciblée et 3 sur la documentation. Ils utilisent des dossiers temporaires et des outils simulés. Ils ne prouvent pas le fonctionnement sur CachyOS : démarrage graphique, écrans, clavier, audio, réseau, trousseau, captures et partage d'écran, connexion SSH, montages et restauration des volumes restent à tester sur la cible. Le [rapport du 10 novembre](docs/verification-noctalia-2026-11-10.md) conserve ses relevés historiques ; les évolutions suivantes figurent dans les guides concernés.

Le [workflow GitHub](.github/workflows/verification.yml) est préparé pour automatiser ces vérifications ; aucun run distant n’est déclaré validé ici. Les nouveaux tests de maintenance couvrent notamment les différences, les sauvegardes, les modifications concurrentes et la restauration dans des dossiers temporaires.

## Confidentialité et interventions sur la machine

Garder secrets, mots de passe, clés privées et données personnelles sensibles hors du dépôt. Les sauvegardes restent locales et peuvent contenir des données personnelles ; examiner les fichiers avant tout ajout à Git.

Une demande de modification du dépôt autorise les fichiers concernés, sans autoriser leur installation sur l'ordinateur. Toute intervention sur la machine ainsi que tout commit ou push nécessite une demande explicite correspondante.
