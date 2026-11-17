# Préparer les quatre volumes secondaires

[Accueil](../README.md) · [Installer le bureau](noctalia.md)

Les commandes se lancent depuis la **racine du dépôt complet**, sur CachyOS installé. Ce script est indépendant de celui du bureau.

[Aperçu et prérequis](#aperçu) · [Application sur la cible](#application-autorisée-sur-la-cible) · [Sauvegarde et restauration](#sauvegarde-et-restauration)

`scripts/disk_setup.sh` est adapté de [10 - disk_setup.sh](https://github.com/Masternaka/CachyOS/blob/main/10%20-%20disk_setup.sh), consulté le 17 novembre 2026 (blob `175644549a28c9fcb3c1f1981eed1ae248c3294e`). Le compte et les partitions ci-dessous sont repris de ce dépôt ; leur identité reste à confirmer sur la machine cible. Ce ne sont pas des valeurs universelles pour une autre installation.

| Label prévu | UUID ext4 | Montage au démarrage |
| --- | --- | --- |
| Backup Medias | `58cdcfb4-b7c7-45aa-9d27-97d3567e77ba` | `/mnt/Backup Medias` |
| Disque Samsung | `7c61158b-ac8c-42e6-90ed-1f659acf4335` | `/mnt/Disque Samsung` |
| Medias | `cab0291d-9a2a-4110-a02f-6783238dcda3` | `/mnt/Medias` |
| SSD | `d594fd69-fb7d-485a-aab4-272da6bee7e0` | `/mnt/SSD` |

Le propriétaire prévu est `gabriel`, identifié par son UID réel sur la cible. Les groupes des fichiers restent inchangés. La prise de possession concerne la racine et tout le contenu, fichiers cachés et liens symboliques compris ; les cibles des liens ne sont pas suivies. Aucun formatage, repartitionnement ou changement d'UUID n'est effectué.

## Aperçu

```bash
bash scripts/disk_setup.sh --plan
# --dry-run et le lancement sans option donnent aussi l'aperçu.
```

L'aperçu fonctionne sur CachyOS installé : il lit l'inventaire `lsblk`, les montages par numéro majeur:mineur et le compte `gabriel`, sans sudo, écriture ni montage. Un clone avec le même UUID, une partition absente ou d'un autre type bloque la préparation. Les noms `/dev/sdX` ne sont pas codés en dur.

Avant application, sauvegarder les données importantes, fermer les applications utilisant ces volumes et les démonter manuellement. Le script ne démonte pas une partition déjà utilisée pour faire passer les vérifications. Il ne peut pas inspecter tous les espaces de montage d'autres systèmes ou conteneurs : réserver une période sans autres opérations sur les disques.

Les commandes de la distribution doivent être disponibles, notamment util-linux, e2fsprogs, les outils GNU, `getfacl`/`setfacl` (ACL) et `getfattr`/`setfattr` (attributs étendus). Le script n'installe aucune dépendance manquante.

## Application autorisée sur la cible

```bash
bash scripts/disk_setup.sh --apply
```

L'application exige un terminal local interactif. Elle affiche l'inventaire et permet de l'actualiser après démontage. Si le script n'est pas root, il propose explicitement de poursuivre avec sudo, puis relance les contrôles. Il faut ensuite saisir `APPLIQUER` après lecture du plan administratif.

Les contrôles portent sur UUID, type ext4, numéro de périphérique, absence de montage et accès en écriture. Un verrou commun avec le script de référence (`/run/cachyos-disk-setup.lock`) empêche deux applications simultanées de ces scripts. Les identités sont relues avant la première écriture, puis avant chaque volume.

Les entrées fstab identiques sont réutilisées. Une entrée concurrente visant un volume ou un point de montage géré, y compris un montage imbriqué, bloque l'application au lieu d'être remplacée. Les dossiers `/mnt/<label>` existants doivent être vides, sans lien symbolique et non montés. Les espaces des labels sont échappés dans fstab.

Chaque volume est monté temporairement dans un dossier privé, avec `nosuid,nodev,noexec`. Après vérification de l'identité du montage, les propriétaires d'origine, modes, ACL et capacités sont enregistrés. Le propriétaire des entrées concernées est changé, les groupes sont conservés et le résultat est vérifié. Le volume est démonté, puis son label est corrigé si nécessaire et relu.

Les lignes ajoutées dans `/etc/fstab` utilisent exactement `defaults,nofail`, comme dans l'autre dépôt. L'ancien ajout `x-gvfs-show` et le délai spécifique de dix secondes ne sont plus imposés. Le fichier préparé est validé avec `findmnt --verify`, puis installé après traitement des quatre volumes et contrôle qu'il n'a pas changé entre-temps. Les unités systemd sont rechargées, sans monter les volumes. **Le montage persistant prend effet au prochain démarrage.** Aucun redémarrage n'est forcé.

## Sauvegarde et restauration

Un dossier privé `/var/tmp/cachy-setup-disques.*` conserve :

- `journal.tsv` : étapes commencées et terminées, même lors d'un échec partiel ;
- `fstab.avant` et `fstab.verification` si de nouvelles entrées étaient nécessaires ;
- `<uuid>.label` : ancien label ;
- `<uuid>.proprietaires` : UID, GID, mode, inode et chemin relatif des entrées concernées, en groupes de cinq champs délimités par NUL ;
- `<uuid>.acl`, `<uuid>.capabilities`, `<uuid>.mount-path` et `<uuid>.metadata-complete` : sauvegardes de métadonnées terminées avant tout chown sur ce volume.

Les montages temporaires sont démontés à la sortie lorsque c'est possible. Un échec de démontage est signalé ; vérifier alors le chemin affiché avant de supprimer ou déplacer un dossier. Il n'y a pas de restauration automatique après un chown partiel. Ne pas supprimer le relevé avant validation du résultat et de la sauvegarde des données.

Pour restaurer, effectuer une intervention distincte sur CachyOS :

1. Examiner le journal et confirmer de nouveau l'UUID de chaque volume. Fermer ses utilisateurs et le démonter avant toute correction de label ou remontage de restauration.
2. Comparer `fstab.avant` à `/etc/fstab`. Mettre le fichier courant à l'abri, puis retirer les seules entrées ajoutées ou restaurer la sauvegarde si aucune autre modification n'est intervenue. Valider fstab et recharger systemd. Les entrées préexistantes identiques n'ont pas été changées.
3. Pour les métadonnées, vérifier que `<uuid>.metadata-complete` existe. Les ACL et capacités contiennent des chemins absolus sous le montage temporaire enregistré dans `<uuid>.mount-path` : après vérification des parents, de l'absence de liens et de montage, recréer ce dossier privé vide et y monter uniquement le volume dont l'UUID a été confirmé. Ne pas appliquer ces sauvegardes à un autre chemin ou à un autre volume.
4. Vérifier chemins et inodes à l'aide du relevé NUL avant de restaurer des entrées qui ont pu être déplacées depuis. Restaurer les propriétaires des liens eux-mêmes avec `chown -h -- +UID CHEMIN` selon le relevé ; les sauvegardes ACL physiques ne suivent pas les liens. Restaurer ensuite les fichiers et dossiers avec `setfacl --restore=FICHIER.acl`, puis les capacités avec `setfattr --restore=FICHIER.capabilities`, sous sudo. Les groupes restent ceux de la sauvegarde. Examiner les commandes avec les chemins réels avant exécution.
5. Démonter le volume de restauration, puis rétablir son ancien label avec `sudo e2label PÉRIPHÉRIQUE ANCIEN_LABEL`, y compris un argument vide si le label était absent. Relire le label et vérifier les propriétaires et droits de fichiers représentatifs.

Ces relevés ne remplacent pas une sauvegarde des données. Un chown peut supprimer des bits spéciaux et capacités ; les copies de métadonnées facilitent la restauration mais celle-ci n'a pas été exécutée sur des volumes réels ici. Les tests locaux vérifient des fonctions avec des outils simulés, pas les montages ext4 ni les outils ACL natifs.
