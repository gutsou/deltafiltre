#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
gen_fixtures.py — Générateur des fixtures SYNTHÉTIQUES de test logiciel
(Phase 8, DeltaFiltre). Bibliothèque standard uniquement, déterministe
(graines fixes).

!!!! AVERTISSEMENT INTÉGRITÉ !!!!
Tout fichier produit ici est une fixture de TEST LOGICIEL pour les scripts
d'analyse (replay_ac04.py, fit_kn.py, drift_e4.py), au sens de la Phase 7
§6-E3 point 10 (vérification du rejouage sur « une série synthétique
construite à la main dont les alarmes attendues sont connues »). Ce ne sont
PAS des mesures, PAS des résultats, PAS des données d'expérience. Les noms
de fichiers portent le préfixe SYNTHETIC_, les scripts d'analyse impriment
un bandeau « TEST LOGICIEL » dès qu'un nom d'entrée contient SYNTHETIC, et
aucune de ces séries ne doit JAMAIS être versée au registre des résultats.

MODÈLE DE GÉNÉRATION (idéalisé, déclaré) : excès « vrai » E_vrai(t) défini par
scénario (montée lente puis rapide, plateau) ; dP_norm journalisé =
B + E_vrai + bruit gaussien sigma = 0,3 kPa ; dP brut obtenu en inversant la
normalisation de débit avec n = 1,5 ; l'état d'alarme journalisé est simulé
par le moteur EXACT de la Phase 6 §3.6 (delta = 20, persistance 3,
hystérésis 5). La référence _REF pose E_ref = E_vrai (cadence 15 min) et
flow_pct = 100 - max(0, E_ref - 30), plancher 86 %.

SCÉNARIOS
---------
SMOKE   : pointe isolée d'un agrégat (aucune alarme attendue, sauf la
          variante fixe à 1 agrégat) puis rampe soutenue (alarme aux deux
          règles) — vérification Phase 7 §6-E3 point 10.
POOL A  : 4 cellules x 2 runs + 2 témoins eau claire. Bases hautes (38–44
          kPa) sur tamis : la règle fixe y accumule fausses alarmes et
          événements manqués (seuil atteint dès E = 6–12 kPa, très en amont
          de l'événement) ; la relative détecte tout. Attendu : CONFIRMÉE
          (exploratoire).
POOL B  : 4 cellules x 2 runs + 2 témoins. Bases basses (11–12 kPa) : les
          deux règles détectent tout ; la cellule DISQUES x EAU-B ajoute une
          excursion thermique (refroidissement, excès apparent visqueux)
          qui fait faussement alarmer la relative 2 fois. Attendu :
          EFFONDRÉE (la fixe est non inférieure sur les deux comptes).
E1      : points (Q, dP) issus de k = 0,055, n = 1,5, bruit multiplicatif
          ±2 % ; plus un fichier à dispersion insuffisante (REFUS attendu).
E4      : B_n saturante (D_max = 6,5 kPa, tau = 2,8 cycles, bruit 0,25 kPa) ;
          attendu : forme SATURANTE par AICc.
"""

import csv
import math
import os
import random
import zlib
from datetime import datetime, timedelta

ICI = os.path.dirname(os.path.abspath(__file__))
FIX = os.path.join(ICI, "fixtures")
HEADER = ("timestamp_iso8601,record_type,P_up_kPa,P_down_kPa,dP_kPa,"
          "dP_norm_kPa,B_current_kPa,E_kPa,T_water_C,pump_state,vib_flag,"
          "V_est_L,debit_mesure_L_min,debit_est_L_min,Q_ref_L_min,"
          "window_valid,zero_valid,state,batt_V,persist_cnt,event_code,"
          "event_detail")
N_EXP = 1.5
DELTA, PERSIST, HYST = 20.0, 3, 5.0
DEBUT = datetime(2026, 1, 1, 6, 0, 0)


def graine(nom):
    return zlib.crc32(nom.encode("utf-8"))


def e_encrassement(t, t_lent, e_lent=15.0, pente=12.0, e_max=46.0):
    """Montée lente linéaire jusqu'à e_lent à t_lent, puis montée rapide."""
    if t < t_lent:
        return e_lent * t / t_lent
    return min(e_max, e_lent + pente * (t - t_lent))


def ligne_event(ts, etat, batt, persist, code, detail):
    """Ligne EVENT à exactement 22 champs (Phase 6 §3.9) : les champs de
    mesure non pertinents restent VIDES."""
    champs = [ts.isoformat(), "EVENT"] + [""] * 13 + [
        "1", "1", etat, "%.2f" % batt, "%d" % persist, code, detail]
    assert len(champs) == 22, len(champs)
    return ",".join(champs)


def ecrire_run(nom, duree_h, B, Q_ref, fonction_e, fonction_t=None,
               fonction_qest=None, fonction_dp_extra=None, avec_ref=True,
               e_ref_decale=None):
    """Écrit un journal produit SYNTHÉTIQUE + son _REF compagnon.

    fonction_e(t_h) -> excès vrai (kPa) ; fonction_qest(t_h) -> débit
    estimé journalisé (L/min) ou None (fenêtre seule) ; fonction_dp_extra
    (t_h) -> surpression brute transitoire (kPa), hors E_ref."""
    rng = random.Random(graine(nom))
    pas = timedelta(minutes=5)
    n_aggs = int(duree_h * 12)
    lignes = [HEADER]
    # Événements de mise en service (format Phase 6 §3.9/§3.10)
    t0 = DEBUT
    lignes.append(ligne_event(t0, "ETALONNAGE", 4.05, 0, "CAL_FIT",
                              "k=0.055; n=1.5; Q_ref=%g L/min" % Q_ref))
    lignes.append(ligne_event(t0, "SURVEILLANCE", 4.05, 0, "BASE_CAPTURE",
                              "B0=%.1f kPa; T0=21.0 C" % B))
    compte, en_alarme = 0, False
    ref_rows = []
    for i in range(n_aggs):
        t = DEBUT + pas * (i + 1)
        th = (i + 1) * 5.0 / 60.0
        e_vrai = fonction_e(th)
        q_est = fonction_qest(th) if fonction_qest else Q_ref
        facteur = (Q_ref / q_est) ** N_EXP if q_est else 1.0
        dp_norm = B + e_vrai + rng.gauss(0, 0.3)
        dp = dp_norm / facteur if q_est else dp_norm
        if fonction_dp_extra:
            dp += fonction_dp_extra(th)
            dp_norm = dp * facteur if q_est else dp
        dp = round(dp, 1)
        dp_norm = round(dp * facteur, 1) if q_est else dp
        e_log = round(dp_norm - B, 1)
        temp = fonction_t(th) if fonction_t else 21.0 + 1.5 * math.sin(
            2 * math.pi * th / 24.0)
        # Moteur d'alarme embarqué (Phase 6 §3.6) — simulation fidèle,
        # effacement compris : en ALARME, E < delta - hystérésis sur une
        # fenêtre valide ramène en SURVEILLANCE (événement ALARM_CLEAR).
        vient_de_s_activer = False
        vient_de_s_effacer = False
        if not en_alarme:
            compte = compte + 1 if e_log >= DELTA else 0
            if compte >= PERSIST:
                en_alarme = True
                vient_de_s_activer = True
        else:
            if e_log < DELTA - HYST:
                en_alarme = False
                compte = 0
                vient_de_s_effacer = True
        etat = "ALARME" if en_alarme else "SURVEILLANCE"
        p_up = round(250.0 + rng.gauss(0, 0.3), 1)
        lignes.append(
            "%s,AGG,%.1f,%.1f,%.1f,%.1f,%.1f,%.1f,%.1f,ON,,%d,,%s,%g,1,1,%s,"
            "%.2f,%d,," % (
                t.isoformat(), p_up, round(p_up - dp, 1), dp, dp_norm, B,
                e_log, round(temp, 1), int(Q_ref * 5 * (i + 1)),
                ("" if q_est is None else "%g" % q_est), Q_ref, etat,
                4.05 - 0.10 * th / duree_h, compte))
        if vient_de_s_activer:
            lignes.append(ligne_event(
                t, "ALARME", 4.05 - 0.10 * th / duree_h, compte, "ALARM_ON",
                "E=%.1f kPa; delta=20 kPa; Bn=%.1f kPa; fenetres "
                "consecutives=3" % (e_log, B)))
        if vient_de_s_effacer:
            lignes.append(ligne_event(
                t, "SURVEILLANCE", 4.05 - 0.10 * th / duree_h, compte,
                "ALARM_CLEAR", "E=%.1f kPa; seuil effacement=%.1f kPa"
                % (e_log, DELTA - HYST)))
        if (i + 1) % 3 == 0 and avec_ref:
            e_ref = e_vrai if e_ref_decale is None else e_ref_decale(th)
            ref_rows.append((t, round(e_ref + rng.gauss(0, 0.2), 1),
                             round(max(86.0, 100.0 - max(0.0, e_ref - 30.0))
                                   , 1)))
    chemin = os.path.join(FIX, nom)
    with open(chemin, "w", encoding="utf-8", newline="") as f:
        f.write("\n".join(lignes) + "\n")
    if avec_ref:
        with open(chemin[:-4] + "_REF.csv", "w", encoding="utf-8",
                  newline="") as f:
            w = csv.writer(f)
            w.writerow(["timestamp_iso8601", "E_ref_kPa", "flow_pct"])
            for t, e_r, fl in ref_rows:
                w.writerow([t.isoformat(), e_r, fl])
    return chemin


def oscillation(debut_h, duree_h, amplitude=8.0):
    def f(t):
        return amplitude if debut_h <= t < debut_h + duree_h else 0.0
    return f


def pas_debit(debut_h, duree_h, q_ref, facteur=1.33):
    def f(t):
        return q_ref * facteur if debut_h <= t < debut_h + duree_h else q_ref
    return f


def bosse_thermique(centre=12.0, demi_largeur=2.0, pic=26.0):
    def f(t):
        return pic * max(0.0, 1.0 - abs(t - centre) / demi_largeur)
    return f


def main():
    os.makedirs(FIX, exist_ok=True)
    Q = 52.0

    # ---------------- SMOKE (vérification §6-E3 point 10)
    def e_smoke(t):
        if t < 3.5:
            return 0.0
        return 50.0
    ecrire_run("SYNTHETIC_E3_FTEST_WTEST_R1_2026-01-01.csv", 6.0, 12.0, Q,
               e_smoke, fonction_dp_extra=oscillation(2.0, 5.0 / 60.0,
                                                       45.0),
               e_ref_decale=lambda t: 0.0 if t < 3.5 else 50.0)

    # ---------------- POOL A
    ecrire_run("SYNTHETIC_E2_FTAMIS_WEAU-CLAIRE_R1_2026-01-01.csv", 24.0,
               44.0, Q, lambda t: 0.0,
               fonction_dp_extra=oscillation(6.0, 20.0 / 60.0))
    ecrire_run("SYNTHETIC_E2_FDISQUES_WEAU-CLAIRE_R1_2026-01-01.csv", 24.0,
               15.0, Q, lambda t: 0.0)
    for run, t_lent in (("R1", 30.0), ("R2", 28.0)):
        ecrire_run("SYNTHETIC_E2_FTAMIS_WEAU-A_%s_2026-01-01.csv" % run,
                   t_lent + 5.0, 44.0, Q,
                   lambda t, tl=t_lent: e_encrassement(t, tl),
                   fonction_dp_extra=oscillation(5.0, 20.0 / 60.0))
    for run, t_lent in (("R1", 30.0), ("R2", 27.0)):
        ecrire_run("SYNTHETIC_E2_FTAMIS_WEAU-B_%s_2026-01-01.csv" % run,
                   t_lent + 5.0, 38.0, Q,
                   lambda t, tl=t_lent: e_encrassement(t, tl),
                   fonction_dp_extra=oscillation(5.0, 20.0 / 60.0))
    for run, t_lent in (("R1", 26.0), ("R2", 24.0)):
        ecrire_run("SYNTHETIC_E2_FDISQUES_WEAU-A_%s_2026-01-01.csv" % run,
                   t_lent + 5.0, 12.0, Q,
                   lambda t, tl=t_lent: e_encrassement(t, tl))
    for run, t_lent in (("R1", 26.0), ("R2", 25.0)):
        ecrire_run("SYNTHETIC_E2_FDISQUES_WEAU-B_%s_2026-01-01.csv" % run,
                   t_lent + 5.0, 15.0, Q,
                   lambda t, tl=t_lent: e_encrassement(t, tl),
                   fonction_qest=pas_debit(8.0, 1.0, Q))

    # ---------------- POOL B
    ecrire_run("SYNTHETIC_POOLB_E2_FTAMIS_WEAU-CLAIRE_R1_2026-01-01.csv",
               24.0, 12.0, Q, lambda t: 0.0)
    ecrire_run("SYNTHETIC_POOLB_E2_FDISQUES_WEAU-CLAIRE_R1_2026-01-01.csv",
               24.0, 11.0, Q, lambda t: 0.0)
    for run, t_lent in (("R1", 26.0), ("R2", 24.0)):
        ecrire_run("SYNTHETIC_POOLB_E2_FTAMIS_WEAU-A_%s_2026-01-01.csv"
                   % run, t_lent + 5.0, 12.0, Q,
                   lambda t, tl=t_lent: e_encrassement(t, tl))
        ecrire_run("SYNTHETIC_POOLB_E2_FTAMIS_WEAU-B_%s_2026-01-01.csv"
                   % run, t_lent + 5.0, 12.0, Q,
                   lambda t, tl=t_lent: e_encrassement(t, tl))
        ecrire_run("SYNTHETIC_POOLB_E2_FDISQUES_WEAU-A_%s_2026-01-01.csv"
                   % run, t_lent + 5.0, 11.0, Q,
                   lambda t, tl=t_lent: e_encrassement(t, tl))
    for run, t_lent in (("R1", 26.0), ("R2", 25.0)):
        bosse = bosse_thermique()
        ecrire_run("SYNTHETIC_POOLB_E2_FDISQUES_WEAU-B_%s_2026-01-01.csv"
                   % run, t_lent + 5.0, 11.0, Q,
                   lambda t, tl=t_lent, b=bosse:
                       e_encrassement(t, tl) + b(t),
                   fonction_t=lambda t, b=bosse:
                       21.0 - (12.0 / 26.0) * b(t),
                   e_ref_decale=lambda t, tl=t_lent:
                       e_encrassement(t, tl))

    # ---------------- E1 (points volumétriques)
    rng = random.Random(graine("E1"))
    with open(os.path.join(FIX, "SYNTHETIC_E1_points.csv"), "w",
              encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["Q_L_min", "dP_kPa", "sens"])
        for q in (24.0, 36.0, 48.0, 60.0, 72.0):
            for rep in range(3):
                for sens in ("M", "D"):
                    dp = 0.055 * q ** 1.5 * (1 + rng.gauss(0, 0.02))
                    w.writerow(["%g" % q, "%.2f" % dp, sens])
    with open(os.path.join(FIX, "SYNTHETIC_E1_points_REFUS.csv"), "w",
              encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["Q_L_min", "dP_kPa"])
        for q in (58.0, 60.0, 62.0):
            for _ in range(2):
                w.writerow(["%g" % q,
                            "%.2f" % (0.055 * q ** 1.5)])

    # ---------------- E4 (cycles de dérive)
    rng = random.Random(graine("E4"))
    with open(os.path.join(FIX, "SYNTHETIC_E4_cycles.csv"), "w",
              encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["cycle", "B_kPa", "r_n"])
        for n_c in range(0, 11):
            b_v = 18.0 + 6.5 * (1 - math.exp(-n_c / 2.8)) \
                + (0.0 if n_c == 0 else rng.gauss(0, 0.25))
            w.writerow([n_c, "%.2f" % b_v,
                        "%.3f" % (0.93 - 0.04 * n_c) if n_c >= 1 else ""])
    print("Fixtures SYNTHÉTIQUES écrites dans %s" % FIX)
    print("RAPPEL : données de test logiciel — AUCUNE mesure réelle.")


if __name__ == "__main__":
    main()
