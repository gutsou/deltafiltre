#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
replay_ac04.py — Rejouage hors ligne E3 / critère AC-04 (projet DeltaFiltre, Phase 8).

RÔLE
----
Applique, sur les séries journalisées par le produit (format CSV 22 colonnes,
Phase 6 §3.9), les DEUX règles d'alarme comparées par le protocole de Phase 7
(§6-E3) sur des agrégats strictement identiques :

  * règle RELATIVE à la base (EF-11) : E >= delta sur 3 fenêtres valides
    consécutives, effacement à E < delta - hystérésis (moteur Phase 6 §3.6) ;
  * règle témoin à SEUIL FIXE « 0,5 bar » (EF-12) : dP brute >= 50 kPa sur
    3 agrégats valides consécutifs (persistance identique, par équité).

puis classe les alarmes contre la vérité terrain FIGÉE (Phase 7 §2.4) lue dans
un fichier de référence compagnon, et applique la RÈGLE DE DÉCISION AC-04
PRÉ-ENREGISTRÉE (Phase 7 §6-E3 point 14, trois issues).

Bibliothèque standard uniquement : l'inventeur peut l'exécuter partout
(Python >= 3.8), sans installation.

ENTRÉES
-------
1. Un ou plusieurs journaux produit au format Phase 6 §3.9 (22 colonnes).
   Le nom de fichier suit la convention Phase 7 §2.1
   (E<exp>_F<filtre>_W<eau>_R<run>_AAAA-MM-JJ.csv) : la cellule (filtre x eau)
   est lue dans le nom ; à défaut, la cellule est « INCONNUE » et un
   avertissement est émis.
2. Pour chaque journal <run>.csv, un fichier de référence compagnon
   <run>_REF.csv (même dossier) au format :
       timestamp_iso8601,E_ref_kPa,flow_pct
   où E_ref_kPa est l'excès de référence (manomètre/colonne + débit
   volumétrique, Phase 7 §2.2) et flow_pct le débit aval en % de sa valeur
   de début de run. SANS fichier _REF, le run est rejoué (alarmes listées)
   mais EXCLU des comptes AC-04 : la vérité terrain n'y est pas datable.
3. Le paramètre --n (exposant de la loi dP = k.Q^n de l'installation, issu de
   l'étalonnage volumétrique EF-08 / fiche F-E1) est OBLIGATOIRE : ni k ni n
   ne sont des colonnes du journal (constat documenté en Phase 8). Q_ref est,
   lui, journalisé (colonne Q_ref_L_min).

RECONSTRUCTION (Phase 6 §3.4, fidèle au firmware v1)
----------------------------------------------------
  dP_norm = dP_mes x (Q_ref / Q_est)^n   si debit_est est journalisé
  dP_norm = dP_mes                        sinon (comparaison par fenêtre seule)
  E       = dP_norm - B_courante (colonne B_current_kPa)
AUCUNE correction de viscosité n'est appliquée : le firmware v1 n'en applique
pas (Phase 6 §3.4) — la température n'intervient qu'en contexte : le script
rapporte l'écart T - T_base (T_base lue dans l'événement BASE_CAPTURE) et le
nombre de fenêtres valides thermiquement éloignées (|dT| > 10 °C), sans
jamais modifier E. Le script confronte aussi la série reconstruite aux
colonnes journalisées (dP_norm_kPa, E_kPa) et aux événements ALARM_ON du
produit : tout écart est rapporté (vérification du rejouage, Phase 7 §6-E3
point 10).

VÉRITÉ TERRAIN (Phase 7 §2.4, figée)
------------------------------------
Un événement débute au premier instant d'une suite de 3 lignes de référence
consécutives vérifiant (E_ref >= 40 kPa) OU (flow_pct <= 90 %, soit une chute
de débit >= 10 %). Alarme manquée : aucune alarme de la règle dans les 2 h
suivant t_event. Alarme fausse/prématurée : alarme sans événement dans
[t_event - 2 h ; t_event + 2 h]. Délai = t_alarme - t_event (résolution de
datation ±2 h : tout écart de délai < 2 h entre règles est signalé comme non
interprétable, Phase 7 §6-E3 point 16).

CONVENTION AJOUTÉE (la seule, déclarée) : le protocole fige le DÉCLENCHEMENT
de la règle fixe mais pas son effacement ; une épisode « fixe » se termine ici
au premier agrégat valide sous le seuil. Cela n'affecte que le « temps en
alarme » (métrique secondaire), jamais les déclenchements ni le verdict.

SORTIE
------
Rapport texte : par run (type F-E3), par cellule, poolé, rejouages de
sensibilité pré-déclarés (delta = 30 / 40 kPa ; fixe à 1 agrégat — secondaires,
ils ne modifient jamais le verdict principal), puis le VERDICT AC-04 selon la
règle figée : CONFIRMÉE (niveau exploratoire) / EFFONDRÉE / INDÉCIDABLE
(plancher d'événements, ou cas mixte non couvert par la règle figée).

INTÉGRITÉ : ce script ne contient et ne produit AUCUNE donnée. Si un nom de
fichier d'entrée contient « SYNTHETIC », le rapport est étiqueté TEST
LOGICIEL. Aucun paramètre n'est ajusté par run.
"""

import argparse
import csv
import math
import os
import sys
from datetime import datetime

# ---------------------------------------------------------------- constantes
# Constantes de protocole FIGÉES (Phase 7 §1.4) — valeurs par défaut du script.
DELTA_DEFAUT = 20.0        # kPa (rejouages de sensibilité : 30, 40)
PERSISTANCE = 3            # fenêtres valides consécutives
HYSTERESIS = 5.0           # kPa (effacement règle relative)
SEUIL_FIXE = 50.0          # kPa (0,5 bar, règle témoin)
EVENT_E_REF = 40.0         # kPa (vérité terrain, condition i)
EVENT_FLOW_PCT = 90.0      # %   (vérité terrain, condition ii : -10 %)
FENETRE_MATCH_H = 2.0      # h   (fenêtre de rattachement alarme/événement)
DT_THERMIQUE = 10.0        # °C  (drapeau de contexte, aucune correction)

HEADER_PRODUIT = [
    "timestamp_iso8601", "record_type", "P_up_kPa", "P_down_kPa", "dP_kPa",
    "dP_norm_kPa", "B_current_kPa", "E_kPa", "T_water_C", "pump_state",
    "vib_flag", "V_est_L", "debit_mesure_L_min", "debit_est_L_min",
    "Q_ref_L_min", "window_valid", "zero_valid", "state", "batt_V",
    "persist_cnt", "event_code", "event_detail",
]


# ---------------------------------------------------------------- utilitaires
def parse_ts(txt):
    return datetime.fromisoformat(txt.strip())


def flottant(txt):
    """Chaîne CSV -> float, ou None si vide/illisible (jamais de 0 fictif)."""
    if txt is None:
        return None
    txt = txt.strip()
    if txt == "":
        return None
    try:
        return float(txt)
    except ValueError:
        return None


def mediane(valeurs):
    if not valeurs:
        return None
    s = sorted(valeurs)
    n = len(s)
    if n % 2 == 1:
        return s[n // 2]
    return 0.5 * (s[n // 2 - 1] + s[n // 2])


# --- Intervalles de confiance exacts de Clopper–Pearson (Phase 7 §6-E3-13) --
def _betacf(a, b, x):
    """Fraction continue de Numerical Recipes pour la bêta incomplète."""
    MAXIT, EPS, FPMIN = 200, 3e-12, 1e-300
    qab, qap, qam = a + b, a + 1.0, a - 1.0
    c = 1.0
    d = 1.0 - qab * x / qap
    if abs(d) < FPMIN:
        d = FPMIN
    d = 1.0 / d
    h = d
    for m in range(1, MAXIT + 1):
        m2 = 2 * m
        aa = m * (b - m) * x / ((qam + m2) * (a + m2))
        d = 1.0 + aa * d
        if abs(d) < FPMIN:
            d = FPMIN
        c = 1.0 + aa / c
        if abs(c) < FPMIN:
            c = FPMIN
        d = 1.0 / d
        h *= d * c
        aa = -(a + m) * (qab + m) * x / ((a + m2) * (qap + m2))
        d = 1.0 + aa * d
        if abs(d) < FPMIN:
            d = FPMIN
        c = 1.0 + aa / c
        if abs(c) < FPMIN:
            c = FPMIN
        d = 1.0 / d
        delta = d * c
        h *= delta
        if abs(delta - 1.0) < EPS:
            break
    return h


def beta_reg(x, a, b):
    if x <= 0.0:
        return 0.0
    if x >= 1.0:
        return 1.0
    bt = math.exp(math.lgamma(a + b) - math.lgamma(a) - math.lgamma(b)
                  + a * math.log(x) + b * math.log(1.0 - x))
    if x < (a + 1.0) / (a + b + 2.0):
        return bt * _betacf(a, b, x) / a
    return 1.0 - bt * _betacf(b, a, 1.0 - x) / b


def beta_quantile(p, a, b):
    lo, hi = 0.0, 1.0
    for _ in range(100):
        mid = 0.5 * (lo + hi)
        if beta_reg(mid, a, b) < p:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)


def clopper_pearson(k, n, alpha=0.05):
    """IC exact (k succès sur n essais). Retourne (bas, haut) ou None."""
    if n == 0:
        return None
    bas = 0.0 if k == 0 else beta_quantile(alpha / 2.0, k, n - k + 1)
    haut = 1.0 if k == n else beta_quantile(1.0 - alpha / 2.0, k + 1, n - k)
    return (bas, haut)


# ---------------------------------------------------------------- chargement
def cellule_depuis_nom(path):
    """Convention Phase 7 §2.1 : ..._F<filtre>_W<eau>_R<run>_... ."""
    nom = os.path.basename(path)
    filtre = eau = None
    morceaux = nom.replace(".csv", "").split("_")
    for m in morceaux:
        if m.startswith("F") and len(m) > 1 and filtre is None:
            filtre = m[1:]
        elif m.startswith("W") and len(m) > 1 and eau is None:
            eau = m[1:]
    if filtre and eau:
        return "%s x %s" % (filtre, eau)
    return "INCONNUE"


def charger_run(path):
    """Lit un journal produit 22 colonnes. Retourne un dict de séries."""
    with open(path, newline="", encoding="utf-8") as f:
        lecteur = csv.reader(f)
        lignes = [l for l in lecteur if l]
    if not lignes:
        raise ValueError("fichier vide")
    entete = [c.strip() for c in lignes[0]]
    if entete != HEADER_PRODUIT:
        raise ValueError("en-tête différent du format Phase 6 §3.9 : %s"
                         % ",".join(entete[:4]))
    aggs, alarmes_produit, t_base, avert = [], [], None, []
    for l in lignes[1:]:
        if len(l) != 22:
            avert.append("ligne à %d champs ignorée" % len(l))
            continue
        d = dict(zip(HEADER_PRODUIT, [c.strip() for c in l]))
        if d["record_type"] == "EVENT":
            if d["event_code"] == "ALARM_ON":
                alarmes_produit.append(parse_ts(d["timestamp_iso8601"]))
            if d["event_code"] in ("BASE_CAPTURE", "BASE_RECAPTURE",
                                   "BASE_NEW") and t_base is None:
                # détail type : « B0=18.0 kPa; T0=21.0 C » (Phase 6 §3.10)
                for morceau in d["event_detail"].replace(";", " ").split():
                    if morceau.startswith("T0=") or morceau.startswith("T="):
                        t_base = flottant(morceau.split("=", 1)[1])
            continue
        if d["record_type"] != "AGG":
            continue
        aggs.append({
            "ts": parse_ts(d["timestamp_iso8601"]),
            "dP": flottant(d["dP_kPa"]),
            "dP_norm_log": flottant(d["dP_norm_kPa"]),
            "B": flottant(d["B_current_kPa"]),
            "E_log": flottant(d["E_kPa"]),
            "T": flottant(d["T_water_C"]),
            "Q_est": flottant(d["debit_est_L_min"]),
            "Q_ref": flottant(d["Q_ref_L_min"]),
            "valide": d["window_valid"] == "1",
        })
    return {"path": path, "aggs": aggs, "alarmes_produit": alarmes_produit,
            "t_base": t_base, "avert": avert,
            "cellule": cellule_depuis_nom(path)}


def charger_reference(path):
    """Fichier _REF compagnon -> liste d'événements (horodatages de début)."""
    with open(path, newline="", encoding="utf-8") as f:
        lecteur = csv.DictReader(f)
        rows = []
        for l in lecteur:
            rows.append({
                "ts": parse_ts(l["timestamp_iso8601"]),
                "E_ref": flottant(l["E_ref_kPa"]),
                "flow": flottant(l["flow_pct"]),
            })
    evenements, serie = [], 0
    for r in rows:
        cond = ((r["E_ref"] is not None and r["E_ref"] >= EVENT_E_REF)
                or (r["flow"] is not None and r["flow"] <= EVENT_FLOW_PCT))
        if cond:
            if serie == 0:
                debut = r["ts"]
            serie += 1
            if serie == 3:
                evenements.append(debut)
        else:
            serie = 0
    return evenements, len(rows)


# ------------------------------------------------------------------ rejouages
def reconstruire(run, n_exp):
    """Reconstruit dP_norm et E (Phase 6 §3.4) ; confronte au journalisé."""
    ecart_norm, ecart_e, eloignes, t_ref_temp = [], [], 0, run["t_base"]
    for a in run["aggs"]:
        if a["dP"] is None or a["B"] is None:
            a["dP_norm"] = a["E"] = None
            continue
        if a["Q_est"] is not None and a["Q_ref"] not in (None, 0):
            facteur = (a["Q_ref"] / a["Q_est"]) ** n_exp
        else:
            facteur = 1.0
        a["dP_norm"] = a["dP"] * facteur
        a["E"] = a["dP_norm"] - a["B"]
        if a["dP_norm_log"] is not None:
            ecart_norm.append(abs(a["dP_norm"] - a["dP_norm_log"]))
        if a["E_log"] is not None:
            ecart_e.append(abs(a["E"] - a["E_log"]))
        if t_ref_temp is None and a["T"] is not None:
            t_ref_temp = a["T"]
        if (a["valide"] and t_ref_temp is not None and a["T"] is not None
                and abs(a["T"] - t_ref_temp) > DT_THERMIQUE):
            eloignes += 1
    return {"ecart_norm_max": max(ecart_norm) if ecart_norm else None,
            "ecart_e_max": max(ecart_e) if ecart_e else None,
            "eloignes": eloignes, "t_base": t_ref_temp}


def rejouer_relative(aggs, delta, persistance, hysteresis, champ="E"):
    """Moteur Phase 6 §3.6 sur les fenêtres valides. Retourne les épisodes
    [(début, fin ou None)] ; le début est l'horodatage de la fenêtre qui
    complète la persistance."""
    episodes, compte, en_alarme, debut = [], 0, False, None
    for a in aggs:
        if not a["valide"] or a[champ] is None:
            continue  # fenêtres invalides : ni incrément ni remise à zéro
        e = a[champ]
        if not en_alarme:
            compte = compte + 1 if e >= delta else 0
            if compte >= persistance:
                en_alarme, debut = True, a["ts"]
        else:
            if e < delta - hysteresis:
                episodes.append((debut, a["ts"]))
                en_alarme, compte = False, 0
    if en_alarme:
        episodes.append((debut, None))
    return episodes


def rejouer_fixe(aggs, seuil, persistance):
    """Règle témoin : dP brute >= seuil sur `persistance` agrégats valides
    consécutifs. Fin d'épisode (convention déclarée, voir en-tête) : premier
    agrégat valide sous le seuil."""
    episodes, compte, en_alarme, debut = [], 0, False, None
    for a in aggs:
        if not a["valide"] or a["dP"] is None:
            continue
        if not en_alarme:
            compte = compte + 1 if a["dP"] >= seuil else 0
            if compte >= persistance:
                en_alarme, debut = True, a["ts"]
        else:
            if a["dP"] < seuil:
                episodes.append((debut, a["ts"]))
                en_alarme, compte = False, 0
    if en_alarme:
        episodes.append((debut, None))
    return episodes


# -------------------------------------------------------------- classification
def classer(episodes, evenements, fin_serie):
    """Apparie alarmes et événements (§2.4). Retourne métriques du run.
    Appariement glouton chronologique : chaque événement prend la plus
    ancienne alarme encore libre dans [t_event - 2 h ; t_event + 2 h] ;
    chaque alarme ne sert qu'une fois."""
    debuts = sorted(d for d, _ in episodes)
    utilises = set()
    manques, delais = 0, []
    fen = FENETRE_MATCH_H * 3600
    for t_ev in evenements:
        choix = None
        for i, d in enumerate(debuts):
            if i in utilises:
                continue
            ecart = (d - t_ev).total_seconds()
            if -fen <= ecart <= fen:
                choix = i
                break
        if choix is not None:
            utilises.add(choix)
            delais.append((debuts[choix] - t_ev).total_seconds() / 3600.0)
        else:
            manques += 1
    fausses = len(debuts) - len(utilises)
    temps_alarme = 0.0
    for d, fin in episodes:
        temps_alarme += ((fin or fin_serie) - d).total_seconds() / 3600.0
    return {"alarmes": len(debuts), "fausses": fausses, "manques": manques,
            "delais": delais, "temps_alarme_h": temps_alarme,
            "debuts": debuts}


# --------------------------------------------------------------------- main
def fmt(x, nd=2):
    return "—" if x is None else ("%.*f" % (nd, x))


def analyser_run(path, n_exp, delta):
    run = charger_run(path)
    verif = reconstruire(run, n_exp)
    aggs = run["aggs"]
    valides = [a for a in aggs if a["valide"] and a["E"] is not None]
    fin_serie = aggs[-1]["ts"] if aggs else None
    ep_rel = rejouer_relative(aggs, delta, PERSISTANCE, HYSTERESIS)
    ep_fix = rejouer_fixe(aggs, SEUIL_FIXE, PERSISTANCE)
    ref_path = path[:-4] + "_REF.csv" if path.endswith(".csv") else None
    evenements, exploitable = None, False
    if ref_path and os.path.exists(ref_path):
        evenements, _ = charger_reference(ref_path)
        exploitable = True
    res = {"run": run, "verif": verif, "ep_rel": ep_rel, "ep_fix": ep_fix,
           "exploitable": exploitable, "evenements": evenements or [],
           "fin_serie": fin_serie, "n_valides": len(valides)}
    if exploitable:
        res["m_rel"] = classer(ep_rel, evenements, fin_serie)
        res["m_fix"] = classer(ep_fix, evenements, fin_serie)
        # Sensibilités pré-déclarées (secondaires — Phase 7 §6-E3 point 9)
        res["sens"] = {}
        for d2 in (30.0, 40.0):
            if d2 != delta:
                res["sens"]["delta=%g" % d2] = classer(
                    rejouer_relative(aggs, d2, PERSISTANCE, HYSTERESIS),
                    evenements, fin_serie)
        res["sens"]["fixe_persist1"] = classer(
            rejouer_fixe(aggs, SEUIL_FIXE, 1), evenements, fin_serie)
    return res


def verdict_ac04(res_list):
    """Règle de décision FIGÉE (Phase 7 §6-E3 point 14). Retourne
    (verdict, motifs[]) — aucun seuil n'est ajusté ici."""
    expl = [r for r in res_list if r["exploitable"]]
    motifs = []
    if len(expl) < 8:
        return ("INDÉCIDABLE",
                ["plancher figé non atteint : %d runs exploitables (< 8) — "
                 "extension des runs prescrite avant tout verdict"
                 % len(expl)])
    # Événements par cellule (cellules sans aucun événement = témoins/eau
    # claire, exclues de la médiane par convention déclarée).
    ev_cell, cellules = {}, set()
    for r in expl:
        c = r["run"]["cellule"]
        cellules.add(c)
        ev_cell[c] = ev_cell.get(c, 0) + len(r["evenements"])
    cellules_ev = [c for c in cellules if ev_cell.get(c, 0) > 0]
    if cellules_ev:
        med = mediane([ev_cell[c] for c in cellules_ev])
        if med is not None and med < 2:
            return ("INDÉCIDABLE",
                    ["plancher figé non atteint : médiane d'événements par "
                     "cellule = %s (< 2) — extension prescrite" % fmt(med, 1)])
    # Comptes poolés et par cellule
    def tot(res_list_, cle, regle):
        return sum(r[regle][cle] for r in res_list_)
    fa_r, fa_f = tot(expl, "fausses", "m_rel"), tot(expl, "fausses", "m_fix")
    mq_r, mq_f = tot(expl, "manques", "m_rel"), tot(expl, "manques", "m_fix")
    motifs.append("poolé — fausses alarmes : relative %d, fixe %d ; "
                  "événements manqués : relative %d, fixe %d"
                  % (fa_r, fa_f, mq_r, mq_f))
    par_cellule = {}
    for c in cellules:
        rs = [r for r in expl if r["run"]["cellule"] == c]
        par_cellule[c] = (tot(rs, "fausses", "m_rel"),
                          tot(rs, "fausses", "m_fix"),
                          tot(rs, "manques", "m_rel"),
                          tot(rs, "manques", "m_fix"))
    cell_fa_pire = [c for c, v in par_cellule.items() if v[0] > v[1]]
    cell_mq_pire = [c for c, v in par_cellule.items() if v[2] > v[3]]
    # --- EFFONDREMENT (conditions figées, l'une suffit)
    if fa_f <= fa_r and mq_f <= mq_r:
        return ("EFFONDRÉE",
                motifs + ["la règle fixe est non inférieure sur les deux "
                          "comptes poolés : la relative « ne fait pas mieux » "
                          "(condition Phase 3 §4.3 / Phase 7 §6-E3-14)"])
    if len(cell_mq_pire) >= 2:
        return ("EFFONDRÉE",
                motifs + ["la relative manque plus d'événements que la fixe "
                          "dans %d cellules (>= 2)" % len(cell_mq_pire)])
    if len(cell_fa_pire) >= 2:
        return ("EFFONDRÉE",
                motifs + ["la relative produit plus de fausses alarmes que "
                          "la fixe dans %d cellules (>= 2)"
                          % len(cell_fa_pire)])
    # --- CONFIRMATION (toutes les conditions figées requises)
    # Délais appariés : événements détectés par les DEUX règles (point 13)
    paires_r, paires_f = [], []
    for r in expl:
        evs = r["evenements"]
        for t_ev in evs:
            dr = [d for d in r["m_rel"]["debuts"]
                  if abs((d - t_ev).total_seconds()) <= FENETRE_MATCH_H * 3600]
            df = [d for d in r["m_fix"]["debuts"]
                  if abs((d - t_ev).total_seconds()) <= FENETRE_MATCH_H * 3600]
            if dr and df:
                paires_r.append((min(dr) - t_ev).total_seconds() / 3600.0)
                paires_f.append((min(df) - t_ev).total_seconds() / 3600.0)
    med_r, med_f = mediane(paires_r), mediane(paires_f)
    cellules_pires = set(cell_fa_pire) | set(cell_mq_pire)
    cond = (fa_r <= fa_f and mq_r <= mq_f and (fa_r < fa_f or mq_r < mq_f)
            and len(cellules_pires) <= 1)
    if med_r is None or med_f is None:
        return ("INDÉCIDABLE",
                motifs + ["aucun événement détecté par les deux règles : la "
                          "clause de délai médian de la règle figée n'est "
                          "pas évaluable"])
    motifs.append("délai médian (événements détectés par les deux) : "
                  "relative %s h, fixe %s h (résolution de datation ±2 h)"
                  % (fmt(med_r), fmt(med_f)))
    if abs(med_r - med_f) < 2.0:
        motifs.append("écart de délai < 2 h : déclaré non interprétable "
                      "(Phase 7 §6-E3 point 16)")
    if cond and med_r <= med_f + 1.0:
        return ("CONFIRMÉE AU NIVEAU EXPLORATOIRE", motifs)
    if fa_r <= fa_f and mq_r <= mq_f:
        return ("INDÉCIDABLE",
                motifs + ["comptes favorables à la relative mais une "
                          "condition figée de confirmation n'est pas remplie "
                          "(délai médian ou cellules) — cas non tranché par "
                          "la règle figée, renvoyé à la revue critique"])
    return ("INDÉCIDABLE",
            motifs + ["cas mixte : la relative est meilleure sur un type "
                      "d'erreur et pire sur l'autre au niveau poolé — la "
                      "règle de décision figée ne couvre pas ce cas (constat "
                      "pour la Phase 9) ; aucun verdict n'est forcé"])


def main():
    ap = argparse.ArgumentParser(
        description="Rejouage E3 / AC-04 — règle relative vs seuil fixe "
                    "0,5 bar (DeltaFiltre). Bibliothèque standard uniquement.")
    ap.add_argument("runs", nargs="+", help="journaux CSV (format Phase 6 "
                                            "§3.9) ; compagnon <run>_REF.csv "
                                            "cherché automatiquement")
    ap.add_argument("--n", type=float, required=True,
                    help="exposant n de la loi dP = k.Q^n de l'installation "
                         "(étalonnage volumétrique, fiche F-E1) — absent du "
                         "journal, obligatoire ici")
    ap.add_argument("--k", type=float, default=None,
                    help="coefficient k de l'installation (informatif)")
    ap.add_argument("--delta", type=float, default=DELTA_DEFAUT,
                    help="seuil de la règle relative (défaut figé : 20 kPa)")
    ap.add_argument("--out", default=None,
                    help="fichier de sortie du rapport (défaut : stdout)")
    args = ap.parse_args()

    synthetique = any("SYNTHETIC" in os.path.basename(p).upper()
                      for p in args.runs)
    L = []
    L.append("=" * 72)
    L.append("DeltaFiltre — REJOUAGE E3 / AC-04 (outil d'analyse, Phase 8)")
    L.append("Règles figées (Phase 7 §1.4/§2.4) : delta = %g kPa, persistance "
             "= %d, hystérésis = %g kPa ; fixe : dP brute >= %g kPa, "
             "persistance %d." % (args.delta, PERSISTANCE, HYSTERESIS,
                                   SEUIL_FIXE, PERSISTANCE))
    L.append("Reconstruction (Phase 6 §3.4) avec n = %g%s ; aucune correction "
             "de viscosité (v1)." % (args.n,
                                      "" if args.k is None else
                                      ", k = %g" % args.k))
    if synthetique:
        L.append("*" * 72)
        L.append("*** ENTRÉES SYNTHÉTIQUES — TEST LOGICIEL UNIQUEMENT ***")
        L.append("*** AUCUNE DONNÉE RÉELLE, AUCUN RÉSULTAT EXPÉRIMENTAL ***")
        L.append("*" * 72)
    L.append("=" * 72)

    resultats = []
    for path in args.runs:
        try:
            res = analyser_run(path, args.n, args.delta)
        except (ValueError, KeyError, FileNotFoundError) as exc:
            L.append("\n[ERREUR] %s : %s" % (path, exc))
            continue
        resultats.append(res)
        run, v = res["run"], res["verif"]
        L.append("\n--- RUN %s (cellule : %s) ---"
                 % (os.path.basename(path), run["cellule"]))
        L.append("agrégats valides comparables : %d ; écarts reconstruction "
                 "vs journalisé : dP_norm max %s kPa, E max %s kPa ; "
                 "fenêtres thermiquement éloignées (|dT| > %g °C) : %d"
                 % (res["n_valides"], fmt(v["ecart_norm_max"], 3),
                    fmt(v["ecart_e_max"], 3), DT_THERMIQUE, v["eloignes"]))
        onsets_log = [d for d, _ in res["ep_rel"]]
        L.append("alarmes relatives (reconstruit) : %s ; (sur E journalisé) "
                 ": %s ; ALARM_ON du produit : %s"
                 % ([d.isoformat() for d in onsets_log],
                    [d.isoformat() for d, _ in
                     rejouer_relative(run["aggs"], args.delta, PERSISTANCE,
                                      HYSTERESIS, champ="E_log")],
                    [t.isoformat() for t in run["alarmes_produit"]]))
        for a in run["avert"]:
            L.append("  avertissement : %s" % a)
        if not res["exploitable"]:
            L.append("PAS de fichier _REF : vérité terrain non datable — "
                     "run EXCLU des comptes AC-04.")
            continue
        L.append("événements (vérité terrain §2.4) : %s"
                 % [t.isoformat() for t in res["evenements"]])
        for nom, m in (("relative", res["m_rel"]), ("fixe", res["m_fix"])):
            ic = clopper_pearson(m["manques"], len(res["evenements"]))
            L.append("  %-8s alarmes %d | fausses %d | manqués %d/%d%s | "
                     "délais (h) %s | temps en alarme %s h"
                     % (nom, m["alarmes"], m["fausses"], m["manques"],
                        len(res["evenements"]),
                        "" if ic is None else
                        " (IC95%% manqués %.2f–%.2f)" % ic,
                        [fmt(d) for d in m["delais"]],
                        fmt(m["temps_alarme_h"], 1)))
        for nom, m in res.get("sens", {}).items():
            L.append("  [sensibilité %s] fausses %d | manqués %d"
                     % (nom, m["fausses"], m["manques"]))

    if resultats:
        L.append("\n" + "=" * 72)
        verdict, motifs = verdict_ac04(resultats)
        L.append("VERDICT AC-04 (règle de décision pré-enregistrée, Phase 7 "
                 "§6-E3 point 14) :")
        L.append(">>> %s" % verdict)
        for m in motifs:
            L.append("  - %s" % m)
        if synthetique:
            L.append("  - RAPPEL : verdict calculé sur fixtures synthétiques "
                     "— il valide le LOGICIEL, pas le produit.")
        L.append("=" * 72)

    texte = "\n".join(L) + "\n"
    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            f.write(texte)
    sys.stdout.write(texte)
    return 0


if __name__ == "__main__":
    sys.exit(main())
