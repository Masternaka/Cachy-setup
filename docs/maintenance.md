# Mettre à jour, diagnostiquer et restaurer les profils

[Accueil](../README.md) · [Configuration et raccourcis](configuration.md) · [Installation complète](noctalia.md)

L'outil [profiles.py](../scripts/profiles.py) gère **un seul profil utilisateur à la fois** : `umbriel`, `noctalia` ou `kitty`. Il n'installe aucun paquet, ne demande pas sudo, ne change aucun service et ne configure pas Greeter. Il est destiné à entretenir un bureau déjà installé.

Toutes les commandes partent de la racine du dépôt complet. **Python 3.11 minimum** est requis pour les vérifications TOML ; le Python du système cible convient s'il satisfait cette version. Une application ou restauration exige CachyOS installé, un utilisateur ordinaire et un terminal local interactif. Aucune modification n'est appliquée à la machine de préparation lors du développement de cet outil.

## Dans ce guide

- [Examiner une mise à jour](#examiner-une-mise-à-jour)
- [Appliquer un seul profil](#appliquer-un-seul-profil)
- [Diagnostiquer le bureau](#diagnostiquer-le-bureau)
- [Lister les sauvegardes](#lister-les-sauvegardes)
- [Restaurer un profil](#restaurer-un-profil)
- [Contrôles GitHub et limites](#contrôles-github-et-limites)

## Examiner une mise à jour

```bash
python3 -B scripts/profiles.py update umbriel --plan
python3 -B scripts/profiles.py update noctalia --plan
python3 -B scripts/profiles.py update kitty --plan
```

Sans `--apply`, le mode aperçu est le défaut. Il ne crée pas de fichiers ni de sauvegarde. Les profils locaux sont préparés en mémoire ; les différences affichent ajouts, modifications et suppressions par rapport aux fichiers actifs. Les fichiers binaires sont signalés sans afficher leur contenu. Les différences peuvent contenir des données personnelles : ne pas publier leur sortie sans relecture.

Pour Kitty, le plan ordinaire indique la source distante **sans accès réseau**. Pour consulter réellement le dernier profil de `CachyOS/main` et ses différences, autoriser explicitement la lecture GitHub :

```bash
python3 -B scripts/profiles.py update kitty --plan --fetch-kitty
```

Cette option récupère Kitty en mémoire et affiche le commit consulté, sans remplacer le profil. Les limites et contrôles d'archive/inclusions sont ceux du [récupérateur existant](noctalia.md#kitty-depuis-le-dépôt-cachyos). Le plan et l'application sont deux appels séparés : si `main` évolue, la copie affichée lors de l'application peut différer. **Le dernier aperçu et sa confirmation portent sur les fichiers effectivement récupérés pour cet appel.**

Les options `--keyboard ca --variant multix` peuvent être utilisées pour un clavier CSA ; le défaut reste `ca` avec variante vide. Elles ne sont pas mémorisées. Mettre à jour Umbriel seul ne met pas à jour le clavier de Greeter : un changement de disposition doit rester coordonné avec la configuration de connexion, selon le [guide du clavier](configuration.md#clavier).

## Appliquer un seul profil

Choisir une seule commande :

```bash
python3 -B scripts/profiles.py update kitty --apply
python3 -B scripts/profiles.py update umbriel --apply
python3 -B scripts/profiles.py update noctalia --apply
```

L'application Kitty autorise la récupération GitHub, puis affiche le commit et les différences **avant** de demander `MODIFIER`. Le profil récupéré est conservé en mémoire jusqu'à la préparation : aucun deuxième téléchargement ne change le contenu après confirmation.

Pour chaque profil, la procédure est : aperçu → saisie `MODIFIER` → verrou → sauvegarde → validation des copies → relecture de l'état actif → remplacement → validation installée. Les erreurs et avertissements Noctalia/Umbriel sont bloquants. Kitty conserve ses contrôles statiques d'inclusions ; le rendu et toutes ses options ne sont pas validés par un binaire Kitty. Les journaux natifs sont conservés dans la sauvegarde, même en cas d'échec avant copie.

**Le dossier du profil choisi est remplacé en entier.** Un fichier supplémentaire comme `umbriel/local.toml`, un thème ajouté localement ou un dossier vide non repris est retiré du profil actif après sauvegarde. Les modes des nouvelles copies sont privés : dossiers `0700`, fichiers `0600`. Les autres profils restent en place. Les liens symboliques, fichiers spéciaux, fichiers appartenant à un autre utilisateur et profils trop volumineux sont refusés (16 Mio de contenu et environ 10 000 entrées au maximum pour les profils actifs). Les chemins XDG doivent rester sous le dossier personnel, sans imbrication ni redirection par des liens.

Pour Noctalia, les réglages GUI prioritaires de `noctalia/settings.toml` sous le dossier XDG d'état sont **conservés par défaut**. Ils peuvent masquer les choix des modules. Pour les retirer explicitement après sauvegarde :

```bash
python3 -B scripts/profiles.py update noctalia --plan --reset-gui
python3 -B scripts/profiles.py update noctalia --apply --reset-gui
```

Le verrou empêche deux opérations simultanées de cet outil. Ne pas lancer l'installateur complet en parallèle. Fermer les éditeurs de configuration et les réglages Noctalia pendant le remplacement : les empreintes sont relues avant copie, mais les applications tierces ne participent pas au verrou. Si un fichier change, la procédure refuse de l'écraser dès qu'elle détecte cette modification.

Après succès, Umbriel surveille ses fichiers ; certains réglages exigent néanmoins une nouvelle session. Fermer et rouvrir Kitty pour vérifier son profil ; vérifier aussi `Super+F12` pour le terminal déroulant. Une modification d'autostart ne relance pas automatiquement Noctalia. Aucun redémarrage n'est imposé.

## Diagnostiquer le bureau

```bash
python3 -B scripts/profiles.py diagnose
```

Le diagnostic est en lecture seule, sans sudo, accès réseau, dossier temporaire ni réparation. Il affiche les versions de paquets, les diagnostics natifs des profils présents, les inclusions Kitty, les états de Greeter/NetworkManager/audio/trousseau/portails et les écrans renvoyés par `umbriel outputs`. Il signale les réglages GUI prioritaires. Les commandes ont un délai d'attente borné.

Le résultat distingue `CORRECT` et `À VÉRIFIER` ; le code de sortie vaut `1` s'il reste un point à examiner, `0` sinon. En TTY, un bureau arrêté ou un portail non encore sollicité peut être normal : le diagnostic ne démarre rien pour faire disparaître ce message. Les écrans sont inventoriés, sans confirmer à lui seul leur position physique ou leur fréquence réelle. Sur macOS, les commandes Linux absentes sont signalées ; le fonctionnement du bureau n'y est pas validé.

## Lister les sauvegardes

```bash
python3 -B scripts/profiles.py backups
```

Les nouvelles sauvegardes sont privées et appartiennent à l'utilisateur :

```text
$XDG_STATE_HOME/cachy-setup/profiles/<date>-<profil>-<identifiant>/
```

Sans variable XDG, il s'agit de `~/.local/state/cachy-setup/profiles/`. Chaque dossier contient :

| Élément | Contenu |
| --- | --- |
| `manifest.json` | Profil et chemins concernés, empreintes/modes avant et après, état de l'opération. |
| `before/` | Copie complète précédente, ou absence documentée dans le manifeste. |
| `settings.before.toml` | Réglages GUI sauvegardés si leur retrait a été demandé et qu'ils existaient. |
| `kitty-source.json` | Commit et provenance pour une récupération Kitty. |
| `validation-before-copy/`, `validation-installed/` | Diagnostics Noctalia/Umbriel lorsqu'ils ont été exécutés. |

La liste concerne les mises à jour ciblées. Les anciennes sauvegardes d'installation, détenues par root sous `/var/lib/cachy-setup/noctalia-*`, restent gérées par le [retour arrière de l'installation complète](noctalia.md#retour-arrière). Les sauvegardes SSH et disques suivent leurs propres guides. Aucune purge automatique n'est ajoutée.

## Restaurer un profil

Utiliser le chemin réel affiché lors de la sauvegarde :

```bash
python3 -B scripts/profiles.py restore /CHEMIN/REEL/DE/LA/SAUVEGARDE --plan
python3 -B scripts/profiles.py restore /CHEMIN/REEL/DE/LA/SAUVEGARDE --apply
```

L'aperçu compare le profil actif à la copie précédente. Après saisie `RESTAURER`, une **nouvelle sauvegarde de l'état courant** est créée, puis le seul profil concerné est restauré et validé. Si le profil était absent avant sa création, la restauration le retire du chemin actif tout en conservant une sauvegarde du profil retiré.

La restauration refuse une sauvegarde altérée, un autre compte/chemin XDG ou un profil actif dont le contenu ou les modes ne correspondent plus à l'état déployé enregistré. Cela protège les changements faits depuis. Il n'y a pas d'option de restauration forcée : dans ce cas, comparer et récupérer manuellement les éléments utiles, après sauvegarde de l'état courant.

Les réglages GUI retirés avec `--reset-gui` ne sont pas réinstallés automatiquement. Le chemin `settings.before.toml` est indiqué : comparer cette copie à tout nouveau fichier `noctalia/settings.toml`, conserver celui-ci à l'abri et remettre la copie souhaitée à son chemin XDG d'origine, en tant qu'utilisateur, lors d'une intervention distincte. Cela évite de remplacer des choix GUI plus récents sans les examiner.

Un échec après remplacement conserve la sauvegarde et les journaux ; examiner le manifeste avant de décider du retour arrière. L'outil ne retire ni ne rétrograde aucun paquet, ne rétablit aucun état de service et ne restaure pas des données de disques. Les sauvegardes des profils ne remplacent pas une sauvegarde des données personnelles.

## Contrôles GitHub et limites

Le workflow [verification.yml](../.github/workflows/verification.yml) prépare les contrôles à chaque push, pull request et lancement manuel : syntaxe Bash, TOML/inclusions, tests isolés et liens locaux Markdown. Deux versions de Python sont prévues. Il ne déploie rien et ne reçoit aucun secret du projet ; ses permissions sont limitées à la lecture du dépôt.

Les commandes équivalentes sont :

```bash
bash -n scripts/umbriel_setup.sh
bash -n scripts/ssh_setup.sh
bash -n scripts/disk_setup.sh
python3 -B scripts/noctalia_dotfiles.py --check --keyboard ca
python3 -B -m unittest discover -s tests
python3 -B scripts/check_docs.py
```

La préparation du workflow ne signifie pas qu'un run GitHub a réussi : son exécution reste à vérifier après publication autorisée. Les contrôles locaux utilisent des fichiers temporaires et des validateurs simulés ; les essais sur CachyOS doivent être consignés dans la [fiche de validation réelle](validation-cachyos.md).
