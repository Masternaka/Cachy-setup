# Cachy-setup

Ce dépôt regroupe mes dotfiles et mes scripts de personnalisation pour mon ordinateur sous CachyOS. Il prépare notamment un bureau **Umbriel + Noctalia v5 + Noctalia Greeter** après une installation complète de CachyOS avec le choix **« No Desktop »**.

Il sert à :

- sauvegarder et versionner les configurations de mon environnement ;
- préparer des scripts pour reproduire mes réglages et mes personnalisations ;
- documenter leur utilisation, les sauvegardes et le retour à la configuration précédente.

## Organisation

| Emplacement | Contenu actuel |
| --- | --- |
| [dotfiles/](dotfiles/README.md) | Modules Umbriel, Noctalia, Kitty, Greeter, portails et applications par défaut ; copiés uniquement lors de l'application autorisée. |
| `scripts/` | Script d'installation du bureau et outil Python de préparation/validation des modules ; scripts SSH et disques encore à adapter. |
| `docs/` | [Installation et restauration](docs/noctalia.md), [vérification documentaire et validations restantes](docs/verification-noctalia-2026-11-10.md). |
| `tests/` | Contrôles isolés du script Noctalia. |
| [AGENTS.md](AGENTS.md) | Consignes de travail pour les assistants IA. |
| [.github/copilot-instructions.md](.github/copilot-instructions.md) | Directives Copilot et règles des messages de commit. |

Les guides en français sont regroupés dans `docs/`, et les contrôles isolés dans `tests/`.

Les fichiers sont préparés ici pour être sauvegardés et versionnés. Leur présence dans le dépôt ne les applique pas à la machine et ne les publie pas sur GitHub. Les chemins et les liens symboliques doivent être vérifiés avant toute restauration.

## Installer le bureau après « No Desktop »

Le système CachyOS doit déjà démarrer sur le disque, avec un compte utilisateur, `sudo`, des pilotes graphiques et un accès Internet fonctionnels. Le script s'exécute en console locale, sans session graphique et sans `sudo` devant la commande.

Transférer **la copie complète du dépôt préparé** sur la cible : le script dépend des modules de `dotfiles/` et de son outil Python. Depuis la racine du dépôt, afficher l'aperçu sans modification :

```bash
bash scripts/umbriel_setup.sh --plan
```

Le clavier est `us` par défaut. Exemple pour un clavier canadien multilingue, à adapter à son matériel :

```bash
bash scripts/umbriel_setup.sh --plan --keyboard ca --variant multix
```

Le plan présente les paquets par catégories, leur dépôt/version sur CachyOS, les profils concernés et les points bloquants. Le [guide](docs/noctalia.md) explique ensuite `--apply`, la confirmation `INSTALLER`, les sauvegardes, les conflits et le redémarrage manuel. Conserver les mêmes options de clavier pour l'application ; elles concernent Umbriel et Greeter.

Le script prépare :

- le compositeur, le shell, l'écran de connexion et les portails ;
- Kitty, Firefox, Thunar et Mousepad, avec leurs raccourcis et associations ;
- l'audio PipeWire/WirePlumber, NetworkManager et GNOME Keyring/Seahorse ;
- les profils modulaires, avec contrôles natifs avant et après copie.

Tous les paquets proviennent des dépôts configurés via pacman, sans AUR. Ils sont répartis dans le script en catégories documentées dans le [guide des paquets](docs/noctalia.md#catégories-de-paquets). Les connexions réseau existantes sont conservées ; un gestionnaire concurrent bloque la procédure. La création et le déverrouillage du trousseau restent interactifs. Bluetooth et les pilotes ne sont pas configurés par ce script.

Les services prévus sont activés pour les prochains démarrages de leurs gestionnaires. Le script ne lance pas Greeter immédiatement et ne force pas le redémarrage. Les profils existants bloquent l'application sans `--replace-config` ; cette option les remplace en entier après sauvegarde, y compris les réglages GUI Noctalia prioritaires. Lire la restauration avant son utilisation.

## État des scripts

Les scripts SSH et disques proviennent de la préparation pour Omarchy. Ils contiennent encore des références à Omarchy et renvoient à des guides `docs/ssh.md` et `docs/disques.md` absents de ce dépôt. Leur adaptation et leur fonctionnement sur CachyOS restent à valider avant toute utilisation de `--apply`.

| Script | Fonction prévue et effets en mode application |
| --- | --- |
| [umbriel_setup.sh](scripts/umbriel_setup.sh) | Après installation CachyOS avec « No Desktop » : bureau, applications, NetworkManager et trousseau depuis les dépôts, sans AUR. Modules vérifiés par les binaires installés avant copie, sauvegardes et confirmation. Greeter, réseau, audio et socket du trousseau activés pour le prochain démarrage. Installation réelle non validée. Voir le [guide](docs/noctalia.md) et la [vérification documentaire](docs/verification-noctalia-2026-11-10.md). |
| [ssh_setup.sh](scripts/ssh_setup.sh) | Configurer un accès SSH sur un réseau IPv4 privé : installation éventuelle d’OpenSSH, remplacement de la configuration après sauvegarde et activation du service SSH. Le pare-feu et le routeur ne sont pas modifiés. |
| [disk_setup.sh](scripts/disk_setup.sh) | Configurer exactement quatre partitions ext4 existantes : montage sous `/mnt/<label>`, modification de `fstab`, des labels et des propriétaires après sauvegarde. La prise de possession est récursive par défaut ; aucun formatage n’est prévu. |

Pour consulter l’aide sans appliquer de changements :

```bash
bash scripts/ssh_setup.sh --help
bash scripts/disk_setup.sh --help
bash scripts/umbriel_setup.sh --help
```

Les scripts proposent un mode `--plan` par défaut et un mode `--apply` avec confirmation interactive. Le plan des disques exige de renseigner les quatre UUID dans le script ; il ne remplace pas les vérifications des périphériques effectuées lors de l’application.

Les noms et versions des paquets sont vérifiés à partir du [catalogue CachyOS](https://packages.cachyos.org/) et des bases de la cible. La documentation rolling peut décrire des paramètres absents des paquets disponibles : les sources des versions relevées ont aussi été examinées. Les réglages d'horloge non reconnus par Greeter 1.6.0 sont ainsi omis.

## Vérifications et état de validation

La dernière [vérification documentée, le 10 novembre 2026](docs/verification-noctalia-2026-11-10.md), relève une syntaxe correcte et **22 tests locaux réussis, aucun ignoré**, avec analyse des modules TOML. Les contrôles de provenance, de services et des sorties des validateurs utilisent des simulations et des dossiers temporaires.

Pour les contrôles locaux sans installation :

```bash
bash -n scripts/umbriel_setup.sh
bash -n scripts/ssh_setup.sh
bash -n scripts/disk_setup.sh
python3 -B tests/test_umbriel_setup.py
```

L'installation réelle reste à valider : démarrage de Greeter, connexion, écrans, réseau, audio, verrouillage/déverrouillage, trousseau et partage d'écran. Le script exécutera les validateurs des binaires installés sur CachyOS et conservera leurs journaux ; cela ne remplace pas ces essais dans une session réelle. Aucun résultat local sur macOS ne prouve le fonctionnement graphique de la cible.

## Sauvegarde et confidentialité

Avant d’appliquer une configuration, sauvegarder les fichiers existants et prévoir le retour arrière. Les secrets, mots de passe, clés privées et données personnelles sensibles doivent rester hors du dépôt. Vérifier les fichiers avant de les ajouter à Git : les exclusions du dépôt ne suffisent pas à garantir leur confidentialité.

Les contrôles de syntaxe et les tests automatisés ne remplacent pas une validation sur l’installation CachyOS réelle, avec son environnement de bureau et ses réglages.

## Autorisation avant toute intervention

Le travail dans ce dépôt ne constitue pas une autorisation d’installer des logiciels ou d’appliquer des configurations à mon ordinateur. Toute installation ou modification de l’environnement de la machine doit recevoir mon autorisation explicite au préalable.

Les assistants IA doivent suivre les consignes du fichier [AGENTS.md](AGENTS.md).
