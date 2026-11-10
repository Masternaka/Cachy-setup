# Guide pour les assistants IA

## Rôle du dépôt

Ce dépôt est consacré aux dotfiles et aux scripts de personnalisation de l’ordinateur personnel de l’utilisateur sous CachyOS. Il sert à sauvegarder et versionner les configurations, à préparer les scripts qui reproduisent les réglages et à documenter leur utilisation et leur restauration.

Limiter les changements à ce périmètre. Le développement d’applications ou de logiciels indépendants demande une nouvelle demande explicite de l’utilisateur.

## Organisation

- `dotfiles/` : configurations modulaires du bureau Umbriel/Noctalia, de Greeter et des applications. Consulter `dotfiles/README.md` avant de les modifier.
- `scripts/umbriel_setup.sh` : installation du bureau après CachyOS « No Desktop », avec aperçu par défaut, confirmation, sauvegardes et activation au prochain démarrage.
- `scripts/noctalia_dotfiles.py` : préparation des copies, vérification TOML et inclusions, appels aux validateurs natifs et lecture des inclusions PAM. Ce fichier n'installe aucun paquet.
- Autres fichiers de `scripts/` : scripts de configuration et de personnalisation, à examiner individuellement.
- `README.md` : présentation du dépôt et état des fonctionnalités disponibles.
- `docs/noctalia.md` : guide canonique d'installation, effets, prérequis, sauvegardes et retour arrière.
- `docs/verification-noctalia-2026-11-10.md` : vérification documentaire datée, preuves locales et validations restantes sur CachyOS.
- `tests/test_umbriel_setup.py` : contrôles isolés des scripts et modules ; services, paquets et validateurs Linux simulés lorsque nécessaire.
- `.github/copilot-instructions.md` : directives Copilot cohérentes avec le présent guide ; ne pas y maintenir une seconde procédure d'installation.

Les scripts SSH et disques contiennent encore des références à Omarchy et à des guides absents. Ne pas les présenter comme validés sur CachyOS. Leur adaptation constitue un travail distinct de la rédaction de cette documentation.

## Règle impérative : autorisation préalable

**Ne jamais rien installer ni rien modifier sur l’ordinateur de l’utilisateur sans son autorisation explicite préalable pour l’intervention concernée.**

- Une demande de modification de fichiers dans ce dépôt autorise les changements nécessaires à cette demande dans le dépôt. Elle n’autorise pas leur application à l’ordinateur.
- Avant toute installation ou modification de l’environnement de la machine, expliquer précisément l’action proposée, les fichiers ou réglages concernés et ses effets, puis attendre l’autorisation explicite de l’utilisateur si elle n’a pas déjà été donnée pour cette intervention.
- Cette règle couvre notamment l’installation, la mise à jour et la suppression de logiciels ou de dépendances, la copie de configurations hors du dépôt, la création de liens symboliques, ainsi que la modification des dotfiles actifs, des services et des paramètres système.
- Ne pas exécuter un script d’installation, de configuration ou de maintenance susceptible de modifier la machine sans cette autorisation, même si son exécution est présentée comme un test.
- Ne jamais considérer une proposition, une absence de réponse ou une autorisation donnée pour une autre intervention comme un accord.

## Manière de travailler

- Rédiger la documentation, les explications et les messages de commit en français.
- Préserver les personnalisations existantes et les modifications en cours qui ne concernent pas la demande.
- Garder distinctes la préparation des fichiers dans le dépôt et leur installation ou leur activation sur la machine.
- Vérifier la distribution, l’environnement de bureau, les outils disponibles et les configurations existantes avant de préparer une adaptation. Ne pas présumer de l’utilisation de KDE Plasma, GNOME ou Hyprland.
- Avant une intervention autorisée sur des configurations existantes, prévoir une sauvegarde identifiable, examiner les conflits et documenter le retour à l’état précédent.
- Pour les scripts qui modifient la machine, prévoir un aperçu sans modification et une confirmation explicite avant application. Documenter les paramètres à remplir, les prérequis, les fichiers ou réglages concernés et la restauration.
- Vérifier les chemins, les liens symboliques et les identifiants de périphériques avant de proposer une copie ou une activation ; ne pas supposer qu’ils conviennent à une autre installation.
- Conserver les licences et la provenance des configurations et plugins tiers.
- Ne pas ajouter de secrets, de mots de passe, de clés privées ou de données personnelles sensibles aux fichiers versionnés. Examiner les fichiers avant leur ajout à Git.
- Tenir le README à jour en distinguant les fonctionnalités présentes, les adaptations à faire et les validations restantes. Ne pas créer de liens vers des guides absents.
- Ne pas créer de commit, pousser sur GitHub ou publier une version sans demande explicite de l’utilisateur pour l’action concernée.

## Bureau après une installation « No Desktop »

- Cibler le système CachyOS déjà installé sur disque, avec compte utilisateur, accès sudo, pilotes et Internet fonctionnels. Ne pas transformer ce dépôt en installateur du système de base.
- Conserver la pile choisie : Umbriel, Noctalia v5 et Noctalia Greeter. Niri sert de référence d'organisation des modules ; ne pas ajouter Niri, Hyprland, UWSM ou un autre bureau par supposition.
- Garder les configurations versionnées dans `dotfiles/`, avec points d'entrée et modules. Umbriel, Noctalia et Kitty disposent d'inclusions ; les modules Greeter sont assemblés lors de la préparation. Éviter de réintroduire un profil monolithique dans le script Bash.
- Utiliser des chemins relatifs pour les inclusions, conserver la cohérence du clavier entre Umbriel et Greeter et laisser la détection des écrans/GPU automatique tant que les identifiants de la cible ne sont pas connus.
- Démarrer la session avec le `start-umbriel` du paquet, puis Noctalia une seule fois via l'autostart d'Umbriel. greetd doit lancer `noctalia-greeter-session`, pas directement l'exécutable d'interface.
- Conserver les contrôles des unités de session, de leur ordre de démarrage et de la pile PAM fournie par la distribution. Le fonctionnement actuel ne réécrit pas PAM et laisse le déverrouillage du trousseau interactif ; toute évolution doit être documentée avec ses effets dans l'aperçu avant application.
- Préserver les connexions réseau. Un gestionnaire concurrent nécessite une migration distincte ; ne pas le désactiver pour faire passer le script. Le backend iwd d'un NetworkManager existant doit rester possible.
- Garder la confirmation avant application et l'activation des services sans démarrage immédiat. Ne pas forcer un redémarrage.
- Traiter les profils existants et les réglages GUI Noctalia prioritaires comme des conflits explicites. `--replace-config` autorise un remplacement complet après sauvegarde, pas une suppression sans trace. Mettre à jour la restauration lorsqu'un profil ou un service géré est ajouté.

## Paquets, versions et sources

- Vérifier les paquets dans [le catalogue CachyOS](https://packages.cachyos.org/) avant de conclure qu'un paquet Arch nécessite l'AUR. Le script du bureau utilise exclusivement pacman et les dépôts configurés ; ne pas ajouter un assistant AUR ou un dépôt tiers sans demande explicite.
- Conserver les tableaux `PACKAGES_*` par catégories, l'explication de leur rôle, l'affichage des dépôts/versions et l'assemblage en une seule transaction avec mise à jour complète. Ne pas introduire de mise à jour partielle `pacman -Sy`.
- Consulter les documentations officielles Noctalia, Umbriel et Greeter pour leurs réglages et commandes. Vérifier aussi la version des paquets et, si nécessaire, les sources correspondantes : une option de la documentation rolling peut ne pas être prise en charge par un paquet publié.
- Ne pas déduire la génération du shell du seul nom d'un paquet. La configuration actuelle utilise le paquet `noctalia` et les commandes v5.
- Consigner dans la documentation la date et les versions observées, sans les présenter comme éternellement actuelles ou les figer implicitement dans le script.

## Vérifications

Privilégier les contrôles de syntaxe et les tests isolés sans effet sur la machine. Par exemple, la syntaxe des scripts actuels peut être vérifiée depuis la racine du dépôt avec :

```bash
bash -n scripts/ssh_setup.sh
bash -n scripts/disk_setup.sh
bash -n scripts/umbriel_setup.sh
python3 -B tests/test_umbriel_setup.py
```

Lire un script avant d’exécuter son mode d’aide ou de prévisualisation afin de vérifier l’absence d’effets de bord. Un test ne doit pas installer de dépendance, monter un disque, changer des droits ou activer un service sans autorisation préalable pour cette intervention.

Pour le bureau, analyser tous les modules TOML, les inclusions et les claviers, puis conserver les tests isolés de provenance, conflits réseau, sauvegardes et diagnostics. Les tests peuvent utiliser le parseur TOML déjà présent avec pip si le Python local est ancien ; ne pas installer une dépendance pour éviter un test ignoré sans autorisation.

Pendant l'application autorisée sur CachyOS, les validateurs natifs doivent contrôler les copies préparées avant leur déploiement, puis les profils installés avant activation. Les avertissements Noctalia et diagnostics Umbriel sont bloquants ; conserver leurs journaux dans la sauvegarde même en cas d'échec. Ne pas prétendre avoir exécuté ces binaires Linux sur la base de sorties simulées dans les tests locaux.

Indiquer les vérifications réellement effectuées et distinguer les contrôles des fichiers d’une validation sur une installation CachyOS réelle. Les tests locaux ne prouvent ni le fonctionnement du bureau, ni l’accès SSH depuis un autre ordinateur, ni le montage et la restauration des disques.
