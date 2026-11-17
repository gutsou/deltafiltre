# Firmware DeltaFiltre — v0.1.0

**Première implémentation. Non testée au banc. Aucun prototype physique n'existe.**

## Organisation

```
src/
  config.h          Broches, constantes, seuils (design Phase 6)
  main.cpp          Câblage ESP32 + pilotes minimaux (ADS1115, DS3231, DS18B20, SD)
  core/             Logique indépendante du matériel — AUCUN include Arduino
    flags.h           Drapeaux qualité des enregistrements
    median.h          Médiane à taille fixe (rejet des transitoires)
    pressure_conv.h   Tension -> kPa, correction ratiométrique (rail mesuré sur AIN3)
    flow_model.h      Ajustement ΔP = k·Qⁿ (log-log) + normalisation
    baseline.h        Base propre B_0 / B_n, rapport de récupération r_n
    alarm.h           Machine à états d'alarme (persistance 3, hystérésis 5 kPa)
    zero_check.h      Contrôle de zéro par égalisation (offset uniquement)
    window.h          Agrégation 5 min : médiane des ΔP par échantillon
test/
  test_core.cpp     Tests unitaires natifs du cœur logique (données synthétiques)
```

Le cœur (`src/core/`) compile sur PC : la même logique peut rejouer les CSV journalisés, ce qui servira aussi à évaluer hors ligne le témoin « seuil fixe 0,5 bar » sur les mêmes séries (protocole E5).

## Tests natifs (logique uniquement)

```bash
g++ -std=c++17 -I firmware/src firmware/test/test_core.cpp -o /tmp/df_test && /tmp/df_test
# -> ALL CORE TESTS PASSED
```

Ces tests vérifient le calcul (médiane, conversion ratiométrique, ajustement k·Qⁿ sur loi synthétique exacte, persistance/hystérésis de l'alarme, r_n, tolérance de zéro). **Ils ne disent rien de la performance de mesure.**

## Build ESP32

PlatformIO, environnement `esp32` (voir `platformio.ini`). Non compilé sur cible à ce jour — à vérifier à la première session de banc.

## Limites connues de la v0.1 (déclarées)

- **Pas d'estimation de débit en direct** : la comparaison se fait sur fenêtres de régime conformes ; `dp_norm` = `dp` mesurée. L'estimation de Q reste un problème ouvert (voir `docs/06-method.md` §2).
- **État d'écoulement par proxy** : fenêtre valide si P_aval > 5 kPa. Un détecteur d'état plus fin est à concevoir au banc.
- **Veille légère** au lieu du deep-sleep du design : le budget d'autonomie (≈130 jours calculés) exige le module nu + rails commutés du design complet ; aucune autonomie n'est revendiquée pour cette v0.1.
- **Interface de mise en service** (capture guidée de B_0, étalonnage volumétrique, séquence de contrôle de zéro par boutons) : la persistance (NVS) et les machines à états sont en place ; le guidage utilisateur complet est le prochain incrément.
- Watchdog et journalisation d'événements complète (BOOT, BASE_CAPTURED, ZERO_CHECK…) : partiels.
