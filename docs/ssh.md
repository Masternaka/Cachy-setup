# Activer SSH en conservant sa configuration

[Accueil](../README.md) · [Installer le bureau](noctalia.md)

Les commandes se lancent depuis la **racine du dépôt complet**, sur CachyOS installé. Ce script est indépendant de celui du bureau.

[Aperçu et prérequis](#aperçu-et-prérequis) · [Application sur la cible](#application-sur-la-cible) · [Retour arrière et vérification](#retour-arrière-et-vérification)

`scripts/ssh_setup.sh` reprend la logique de [01 - systemd_services.sh](https://github.com/Masternaka/CachyOS/blob/main/01%20-%20systemd_services.sh), consulté le 17 novembre 2026 (blob `deae51cb015a520da264f7f7f591982c6aa0742e`). Il ne traite que `sshd.service`. Bluetooth et les timers de l'autre dépôt restent hors de ce script.

## Aperçu et prérequis

```bash
bash scripts/ssh_setup.sh --plan
# Alias : --dry-run ; sans option, le plan est également le défaut.
```

L'aperçu lit le paquet et les propriétés systemd, sans sudo ni écriture. CachyOS doit être démarré sur disque avec systemd fonctionnel, `openssh` déjà installé et ses clés d'hôte déjà préparées. Le script n'installe rien et ne génère pas de clés. Si un prérequis manque, le préparer lors d'une intervention distincte avant de relancer.

Examiner la configuration réelle `/etc/ssh/sshd_config` et ses fragments : les comptes, mots de passe, clés autorisées, interfaces et ports accessibles sont ceux de ces fichiers. **L'ancien profil limité à un compte et un réseau IPv4 privé n'est plus généré.** Ce script ne garantit donc pas une limitation au réseau domestique. Il ne change pas les règles du pare-feu ni celles du routeur. Une ouverture réseau éventuelle doit être préparée séparément ; ne pas désactiver le pare-feu pour faire passer un essai.

Les états acceptés sont `enabled`, `enabled-runtime` ou `disabled`, avec un service `active`, `inactive` ou `failed`. Une unité absente, masquée, personnalisée, surchargée ou dans un état transitoire bloque l'application, tout comme un `sshd.socket` actif ou activé. Aucun démasquage automatique n'est effectué.

## Application sur la cible

```bash
bash scripts/ssh_setup.sh --apply
```

Lancer sans sudo depuis un terminal local interactif. Après lecture du plan, saisir `ACTIVER`. Le script demande sudo, relit les états et refuse de poursuivre s'ils ont changé. Il valide la configuration et les clés existantes avec `sshd -t`, puis sauvegarde les états avant toute action sur le service.

- Déjà activé durablement et actif : aucune modification.
- Déjà actif mais non activé durablement : activer sans redémarrer.
- Déjà activé mais arrêté : démarrer seulement.
- Sinon : activer puis démarrer, et vérifier l'état final.

Les fichiers SSH ne sont ni remplacés ni copiés. Aucun mot de passe n'est demandé par le script, hormis l'authentification sudo ; aucun secret n'est enregistré dans le dépôt.

## Retour arrière et vérification

Le dossier privé `/var/lib/cachy-setup/ssh-*` contient `service-state.txt` et `retour-arriere.sh`, non exécutable et en mode `0600`. Examiner le contenu, le comparer à l'état courant et s'assurer qu'aucune modification volontaire n'est intervenue depuis, puis le lancer manuellement avec `sudo bash CHEMIN/retour-arriere.sh` si un retour arrière est souhaité.

Le fichier rétablit l'activation durable ou temporaire et l'état démarré/arrêté. Il ne recrée pas un ancien état `failed`, n'annule pas les effets d'une connexion et ne restaure pas des configurations modifiées par ailleurs. En cas d'échec partiel, le script conserve ce dossier et affiche son chemin ; il ne lance pas automatiquement le retour arrière.

Sur CachyOS, vérifier `systemctl status sshd.service` et `journalctl -b -u sshd.service --no-pager`. Depuis un autre ordinateur du réseau autorisé par la configuration réelle, tester la connexion avec le compte, l'adresse et le port appropriés, puis comparer l'empreinte du serveur. Ces essais réseau n'ont pas été effectués ici. Les tests locaux utilisent un faux systemctl et un faux sudo ; ils ne prouvent pas une connexion réelle.
