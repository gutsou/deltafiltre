# DeltaFiltre

**Enregistreur autonome de pression différentielle (ΔP) pour têtes de filtration manuelles d'irrigation goutte-à-goutte, à alarme relative à la base propre du filtre.**

> ## ⚠ État du projet — à lire avant tout
> **Conception et première implémentation du firmware. Aucun test physique n'a été réalisé. Aucun résultat expérimental n'existe.**
> Le matériel n'a pas été acheté ni assemblé. Les valeurs marquées « cible » ou « calculé » sont des objectifs de conception ou des résultats de calcul, jamais des mesures. La porte **G0** (confirmation écrite du fournisseur sur la tenue en surpression des transmetteurs) doit être franchie avant tout achat.

## Le problème

Sur une tête de filtration manuelle (tamis, disques ou sable), l'encrassement du filtre se traduit par une perte de charge ΔP croissante entre l'amont et l'aval. Aujourd'hui, le nettoyage se fait « au jugé » : trop tôt (travail et eau perdus) ou trop tard (débit et uniformité d'arrosage dégradés). Les seuils fixes universels (par ex. 0,5 bar) ne tiennent pas compte du filtre, de l'eau ni du régime de débit propres à chaque installation.

## Le concept

DeltaFiltre mesure en continu les pressions amont et aval du filtre, calcule ΔP, et la compare à la **base propre mesurée à la mise en service sur l'installation elle-même** — pas à un seuil d'usine. Il journalise la série temporelle complète sur carte SD (format CSV documenté), suit la dérive de la base après chaque nettoyage, et intègre un **contrôle de zéro par égalisation** qui distingue la dérive du filtre de la dérive des capteurs.

**Ce que DeltaFiltre n'est pas :** un contrôleur. Il est **alarme seule** — aucune sortie d'actionnement, ni vanne, ni pompe, ni rétrolavage. Autonome (batterie), **hors ligne** (aucune connectivité), **indépendant de marque**.

## La méthode en bref

- Loi du filtre propre : **ΔP = k · Qⁿ**, ajustée à la mise en service par étalonnage volumétrique (récipient gradué + chronomètre, 2–3 points) → paramètres propres (k, n, Q_ref).
- Excès : **E(t) = ΔP_norm(t) − B_n**. Alarme si E ≥ δ de façon persistante sur **3 fenêtres valides consécutives** ; effacement avec hystérésis **h = 5 kPa**. δ par défaut **20 kPa**, réglable de 20 à 40 kPa.
- Après chaque nettoyage confirmé, nouvelle base **B_n** ; le rapport **r_n = B_n / B_0** est suivi comme **indicateur de dérive — en cours de validation, jamais présenté comme un diagnostic**.
- Contrôle de zéro par égalisation (vanne transversale ouverte, pompe arrêtée) : si **|ΔP_zéro| > 2 kPa**, avertissement distinct « dérive capteur suspectée » et données marquées « zéro non vérifié » depuis le dernier contrôle valide.
- Pourquoi la méthode relative : avec la même paire de capteurs, les erreurs constantes se compensent — l'incertitude élargie sur l'excès vaut **U(E) ≈ ±1,6 kPa** (calcul, Phase 4 du dossier), contre ±5,9 à ±10,3 kPa sur la ΔP absolue.

Détails : [docs/06-method.md](docs/06-method.md).

## Matrice d'état

| Composant | Conçu | Implémenté | Simulé | Testé au banc | Testé au terrain |
|---|---|---|---|---|---|
| Spécification produit | ✅ | — | — | — | — |
| Design prototype (hydraulique + électronique) | ✅ | — | — | ❌ | ❌ |
| Firmware ESP32 | ✅ | ✅ (v0.1) | ✅ (tests natifs du cœur logique) | ❌ | ❌ |
| Scripts d'analyse Python | ✅ | ✅ | ✅ (données synthétiques étiquetées) | — | ❌ |
| Protocole expérimental E0–E7 | ✅ | — | — | ❌ | ❌ |
| Données expérimentales | — | — | — | ❌ aucune | ❌ aucune |

## Architecture

- **Hydraulique :** deux transmetteurs relatifs inox 0–600 kPa sur tubes montants symétriques à même cote (±5 cm), manifold d'égalisation laiton à vanne unique, pointeaux d'isolement/amortissement, purges d'air. Zéro soudure.
- **Électronique :** ESP32-WROOM-32 (module nu), ADS1115 16 bits alimenté en 5 V commuté (PGA ±6,144 V ; AIN3 mesure le rail d'excitation → mesure ratiométrique), DS3231 (RTC), DS18B20 (T_eau), microSD, pack 1S 3×18650 + MCP1700, boost MT3608 commuté. Le CAN interne de l'ESP32 est **exclu** de la chaîne de mesure.
- **Rythme :** rafale de mesure chaque minute, agrégat journalisé = **médiane sur 5 minutes** ; budget calculé ≈ 47 mAh/jour → **≈ 130 jours** d'autonomie cible (calcul, non mesuré).

Détails : [docs/02-architecture.md](docs/02-architecture.md) · Nomenclature (≈ **1 445 MAD**, prix vérifiés/estimés distingués) : [docs/03-bom.md](docs/03-bom.md).

## Structure du dépôt

```
docs/        Spécification, architecture, méthode, format de données, protocole de validation
firmware/    Firmware ESP32 (PlatformIO) — cœur logique indépendant du matériel + tests natifs
analysis/    Scripts Python d'analyse (rejeu, dérive, ajustement k·Qⁿ) — validés sur données SYNTHÉTIQUES
data/        Aucune donnée expérimentale (voir data/README.md)
```

## Validation prévue (rien de tout cela n'a été exécuté)

Protocole E0–E7 pré-enregistré : étalonnage au banc contre manomètre de référence, encrassement contrôlé, comparaison de la règle relative à la base contre le témoin « seuil fixe 0,5 bar » **sur les mêmes séries**, puis pilote terrain. Critères d'acceptation fixés **avant** les mesures. Voir [docs/05-validation-protocol.md](docs/05-validation-protocol.md).

## Résultats

**Aucun.** Toute sortie de simulation présente dans ce dépôt est étiquetée « synthétique — démontre la logique, pas la performance ».

## Contexte

Projet de R&D personnel. Le dossier complet (phases 1–12 : carte des problèmes, art antérieur, fondement scientifique, revue critique, faisabilité, évaluation PI) existe hors dépôt.

⚠ **Propriété intellectuelle :** une évaluation PI interne conclut que les revendications larges sur le dispositif sont anticipées (art antérieur ancien) ; seule la méthode intégrée (base + dérive + contrôle de zéro + porte d'incertitude) mériterait un examen professionnel.

## Licence

Code : MIT (voir [LICENSE](LICENSE)). La documentation et le design restent © l'auteur jusqu'à décision contraire.
