# Validation réelle sur CachyOS

[Accueil](../README.md) · [Installation](noctalia.md) · [Maintenance](maintenance.md)

Cette fiche sert à consigner les essais sur l'ordinateur cible. **Aucun essai réel n'est déclaré réussi à ce stade.** Les tests isolés et les contrôles macOS ne remplissent pas cette fiche automatiquement. Ne pas y publier de mot de passe, de clé, d'adresse personnelle ou de journal contenant des secrets.

## Contexte de l'essai

| Information | Valeur à renseigner sur la cible |
| --- | --- |
| Date et personne ayant effectué l'essai | Non renseigné |
| Révision de Cachy-setup (`git rev-parse HEAD`, changements locaux éventuels) | Non renseignée |
| Versions (`pacman -Q umbriel noctalia noctalia-greeter kitty`) | Non relevées |
| Matériel GPU/pilote et noyau | Non relevés |
| Écrans annoncés par `umbriel outputs` | Non relevés |
| Clavier de session et de connexion | Attendu : `ca`, variante vide ; non testé |
| Chemins XDG et sauvegardes retenues | Non renseignés ; conserver localement les chemins sensibles |
| Commit externe Kitty (`kitty-source.json`) | Non relevé |

## Parcours à vérifier

Utiliser les états **non testé**, **réussi**, **échoué** ou **sans objet**, puis ajouter une observation factuelle et la date. Un résultat réussi concerne uniquement le matériel et les versions notés ci-dessus.

| Essai | État | Observation |
| --- | --- | --- |
| Installation depuis CachyOS « No Desktop », sauvegardes et journaux présents | Non testé | |
| Redémarrage → Greeter → authentification → Umbriel → Noctalia unique | Non testé | |
| Clavier canadien français dans Greeter et la session, symboles usuels | Non testé | |
| DP-1 à gauche et HDMI-A-2 à droite, 1920 × 1080 à 60 Hz | Non testé | |
| Espaces 1–5 sur DP-1, 6–10 sur HDMI-A-2, déplacement des fenêtres | Non testé | |
| Kitty normal et terminal déroulant `Super+F12`, masquage et réaffichage | Non testé | |
| Lanceur, Thunar, Zed, PDF, images et médias avec leurs associations | Non testé | |
| Barre, presse-papiers, notifications et indicateurs audio | Non testé | |
| Audio : sortie, microphone et changement de périphérique | Non testé | |
| Réseau existant conservé, accès Internet après redémarrage | Non testé | |
| Verrouillage, déverrouillage, veille et retour de veille | Non testé | |
| Trousseau : création/déverrouillage interactif, historiques après connexion | Non testé | |
| Capture de région avec confirmation, capture complète et partage d'écran | Non testé | |
| Diagnostic en session et explication des points à vérifier | Non testé | |
| Mise à jour ciblée d'un profil, autres profils inchangés, copie précédente conservée | Non testé | |
| Refus d'une restauration après modification locale ultérieure | Non testé | |
| Restauration d'un profil et nouvelle sauvegarde de l'état remplacé | Non testé | |
| Retour arrière de l'installation complète dans un contexte de secours maîtrisé | Non testé | |
| SSH depuis un autre ordinateur autorisé, empreinte vérifiée | Non testé | |
| Volumes : UUID, labels, propriétaires/groupes et montage au démarrage | Non testé | |
| Restauration de métadonnées sur un volume de test approprié | Non testé | |

Les essais qui modifient la machine, les services ou les volumes doivent rester des interventions explicitement autorisées. La présence d'une ligne à vérifier ne demande pas d'exécuter automatiquement le script correspondant. Conserver les détails des erreurs dans un compte rendu local expurgé, avec le chemin des journaux utiles.
