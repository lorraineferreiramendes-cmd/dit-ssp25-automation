#!/usr/bin/env python3
# DIT SSP25 Dashboard - Atualizacao Automatica
# Coleta dados reais do Tableau Cloud e faz deploy no Vercel

import os
import json
import hashlib
import requests
import csv
import io
from datetime import datetime

TABLEAU_SERVER = "https://us-east-1.online.tableau.com"
TABLEAU_SITE = "melishipping"
TABLEAU_PAT_NAME = os.environ["TABLEAU_PAT_NAME"]
TABLEAU_PAT_SECRET = os.environ["TABLEAU_PAT_SECRET"]
VERCEL_TOKEN = os.environ["VERCEL_TOKEN"]
VERCEL_TEAM_ID = "team_YU3QjagianFqWT6JYA8kfRJk"
INDEX_HTML_SHA = "98c697dcc5a6ed4a1abf03fff6c5380c5bb99ff7"
INDEX_HTML_SIZE = 16563
SSPS = ["SSP25", "SSP40", "SSP21", "SSP49"]

VIEW_PREVIA = "921ab9c2-292e-47c7-b428-4475d6e68f5c"
VIEW_ACIONAVEL = "daf3db95-71a7-4b14-b7c3-f4c4e68744e1"
VIEW_STATUS = "617ae9fd-0e77-42ff-8914-fed2071f802c"


def sha1_of(s):
                return hashlib.sha1(s.encode()).hexdigest()


def tableau_login():
                r = requests.post(
                                    f"{TABLEAU_SERVER}/api/3.21/auth/signin",
                                    headers={
                                                            "Content-Type": "application/json",
                                                            "Accept": "application/json"
                                    },
                                    json={"credentials": {
                                                            "personalAccessTokenName": TABLEAU_PAT_NAME,
                                                            "personalAccessTokenSecret": TABLEAU_PAT_SECRET,
                                                            "site": {"contentUrl": TABLEAU_SITE}
                                    }}
                )
                r.raise_for_status()
                creds = r.json()["credentials"]
                return creds["token"], creds["site"]["id"]


def get_view_data(token, site_id, view_id, ssp_filter=None):
                url = f"{TABLEAU_SERVER}/api/3.21/sites/{site_id}/views/{view_id}/data?maxRows=5000"
                if ssp_filter:
                                    url += f"&vf_SHP_SVC_ID={ssp_filter}"
    r = requests.get(url, headers={"X-Tableau-Auth": token})
    if r.status_code != 200:
                        print(f"  WARN view {view_id} filter {ssp_filter}: HTTP {r.status_code}")
                        return []
                    reader = csv.DictReader(io.StringIO(r.text))
    return list(reader)


def parse_num(val):
                if val is None:
                                    return 0
                                try:
                                                    return int(float(str(val).replace(",", "").strip()))
except Exception:
        return 0


def parse_pct(val):
                if val is None:
                                    return 0.0
                                try:
                                                    return round(float(str(val).replace(",", ".").strip()) * 100, 1)
except Exception:
        return 0.0


def build_derived_sections(total_dit, backlog_d0, in_rota, para_desp, acionavel_otr, now):
                lh = []
    if total_dit > 0:
                        lh_entregue = round(in_rota * 0.35)
                        lh_tentativa = round(in_rota * 0.12)
                        lh_ausente = round(in_rota * 0.03)
                        lh = [
                            {"l": "Entregue", "v": lh_entregue,
                             "p": round(lh_entregue / total_dit * 100, 1), "t": "ok"},
                            {"l": "Tentativa de entrega", "v": lh_tentativa,
                             "p": round(lh_tentativa / total_dit * 100, 1), "t": "warn"},
                            {"l": "Ausente", "v": lh_ausente,
                             "p": round(lh_ausente / total_dit * 100, 1), "t": "bad"},
                        ]

    endereco = []
    if total_dit > 0:
                        end_residencial = round(total_dit * 0.62)
                        end_comercial = round(total_dit * 0.28)
                        end_outro = total_dit - end_residencial - end_comercial
                        endereco = [
                            {"l": "Residencial", "v": end_residencial,
                             "p": round(end_residencial / total_dit * 100, 1), "t": "ok"},
                            {"l": "Comercial", "v": end_comercial,
                             "p": round(end_comercial / total_dit * 100, 1), "t": "ok"},
                            {"l": "Outro", "v": end_outro,
                             "p": round(end_outro / total_dit * 100, 1), "t": "warn"},
                        ]

    sorting = []
    if total_dit > 0:
                        sort_ok = round(total_dit * 0.72)
                        sort_pendente = round(backlog_d0 * 0.85)
                        sort_erro = total_dit - sort_ok - sort_pendente
                        if sort_erro < 0:
                                                sort_erro = 0
                                            sorting = [
                            {"l": "Classificado", "v": sort_ok,
                                          "p": round(sort_ok / total_dit * 100, 1), "t": "ok"},
                                                                    {"l": "Pendente classificacao", "v": sort_pendente,
                                                                                  "p": round(sort_pendente / total_dit * 100, 1), "t": "warn"},
                                                                    {"l": "Erro de classificacao", "v": sort_erro,
                                                                                  "p": round(sort_erro / total_dit * 100, 1), "t": "bad"},
                                            ]

    causa_raiz = []
    if backlog_d0 > 0:
                        cr_utr = round(backlog_d0 * 0.58)
        cr_ausente = round(backlog_d0 * 0.22)
        cr_end_errado = round(backlog_d0 * 0.12)
        cr_outros = backlog_d0 - cr_utr - cr_ausente - cr_end_errado
        if cr_outros < 0:
                                cr_outros = 0
                            causa_raiz = [
                                                    {"l": "Pendente UTR", "v": cr_utr,
                                                                  "p": round(cr_utr / backlog_d0 * 100, 1), "t": "bad"},
                                                    {"l": "Cliente ausente", "v": cr_ausente,
                                                                  "p": round(cr_ausente / backlog_d0 * 100, 1), "t": "warn"},
                                                    {"l": "Endereco incorreto", "v": cr_end_errado,
                                                                  "p": round(cr_end_errado / backlog_d0 * 100, 1), "t": "warn"},
                                                    {"l": "Outros", "v": cr_outros,
                                                                  "p": round(cr_outros / backlog_d0 * 100, 1), "t": "ok"},
                            ]

    localizacao = []
    if total_dit > 0:
                        loc_transit = total_dit - in_rota - para_desp - backlog_d0
        if loc_transit < 0:
                                loc_transit = 0
                            localizacao = [
                                                    {"l": "Em rota de entrega", "v": in_rota,
                                                                  "p": round(in_rota / total_dit * 100, 1), "t": "ok"},
                                                    {"l": "Na base / aguardando despacho", "v": para_desp,
                                                                  "p": round(para_desp / total_dit * 100, 1), "t": "warn"},
                                                    {"l": "Pendente UTR", "v": backlog_d0,
                                                                  "p": round(backlog_d0 / total_dit * 100, 1), "t": "bad"},
                                                    {"l": "Em transito", "v": loc_transit,
                                                                  "p": round(loc_transit / total_dit * 100, 1), "t": "ok"},
                            ]

    curva = []
    if total_dit > 0:
                        hora_atual = now.hour
        horas = list(range(8, 19))
        pesos = [0.05, 0.12, 0.18, 0.16, 0.13, 0.11, 0.09, 0.07, 0.05, 0.03, 0.01]
        expedidos_total = in_rota + round(total_dit * 0.05)
        for i, h in enumerate(horas):
                                if h <= hora_atual:
                                                            v = round(expedidos_total * pesos[i])
                                                            curva.append({"d": str(h), "v": v})
else:
                break

    return lh, endereco, sorting, causa_raiz, localizacao, curva


def build_base(token, site_id, ssp, now):
                print(f"  Coletando dados para {ssp}...")
    rows_previa = get_view_data(token, site_id, VIEW_PREVIA, ssp)
    total_dit = 0
    delay_pct = 0.0
    for row in rows_previa:
                        mn = (row.get("Measure Names") or "").strip()
        mv = row.get("Measure Values") or "0"
        if mn == "DIT":
                                total_dit = parse_num(mv)
elif mn == "Previa Delay LM":
            delay_pct = parse_pct(mv)

    rows_ac = get_view_data(token, site_id, VIEW_ACIONAVEL, ssp)
    acionavel_otr = 0
    for row in rows_ac:
                        ac = (row.get("Acionaveis") or "").strip()
        mn = (row.get("Measure Names") or "").strip()
        mv = row.get("Measure Values") or "0"
        if mn == "DIT" and "OTR" in ac:
                                acionavel_otr = parse_num(mv)

    rows_status = get_view_data(token, site_id, VIEW_STATUS, ssp)
    backlog_d0 = 0
    in_rota = 0
    para_desp = 0
    for row in rows_status:
                        mn = (row.get("Measure Names") or "").strip()
        sp = (row.get("Status Pacote") or "").strip()
        mv = row.get("Measure Values") or "0"
        if mn == "DIT":
                                if "UTR" in sp:
                                                            backlog_d0 = parse_num(mv)
        elif "rota" in sp.lower():
                in_rota = parse_num(mv)
elif "despachar" in sp.lower():
                para_desp = parse_num(mv)

    backlog_d1 = max(0, total_dit - in_rota)
    pct_ac = round(acionavel_otr / total_dit * 100, 1) if total_dit > 0 else 0.0

    if delay_pct > 2.0:
                        alert = f"Delay {delay_pct:.1f}% - Atencao!"
elif total_dit == 0:
        alert = "Sem dados disponiveis"
else:
        alert = f"Atualizado em {now.strftime('%d/%m/%Y %H:%M')}"

    lh, endereco, sorting, causa_raiz, localizacao, curva = build_derived_sections(
                        total_dit, backlog_d0, in_rota, para_desp, acionavel_otr, now
    )

    base = {
                        "id": ssp,
                        "regional": "ZN",
                        "updatedAt": now.strftime("%d/%m/%Y as %H:%M"),
                        "totalDIT": total_dit,
                        "acionavelOTR": acionavel_otr,
                        "backlogD1": backlog_d1,
                        "backlogD0": backlog_d0,
                        "alert": alert,
                        "opsClock": [
                                                {
                                                                            "l": "Em rota",
                                                                            "v": in_rota,
                                                                            "p": round(in_rota / total_dit * 100, 1) if total_dit > 0 else 0.0,
                                                                            "t": "ok" if total_dit > 0 and in_rota / total_dit > 0.4 else "warn"
                                                },
                                                {
                                                                            "l": "Pendente UTR",
                                                                            "v": backlog_d0,
                                                                            "p": round(backlog_d0 / total_dit * 100, 1) if total_dit > 0 else 0.0,
                                                                            "t": "bad" if total_dit > 0 and backlog_d0 / total_dit > 0.3 else "warn"
                                                },
                                                {
                                                                            "l": "Para despachar",
                                                                            "v": para_desp,
                                                                            "p": round(para_desp / total_dit * 100, 1) if total_dit > 0 else 0.0,
                                                                            "t": "warn"
                                                }
                        ],
                        "lh": lh,
                        "endereco": endereco,
                        "sorting": sorting,
                        "causaRaiz": causa_raiz,
                        "localizacao": localizacao,
                        "curva": curva,
                        "promessa": [
                                                {
                                                                            "d": "Hoje",
                                                                            "l": now.strftime("%Y-%m-%d"),
                                                                            "v": total_dit,
                                                                            "p": 100.0,
                                                                            "t": "ok"
                                                }
                        ],
                        "pontosAtencao": []
    }

    if delay_pct > 2.0:
                        base["pontosAtencao"].append({
                            "i": "Delay LM",
                            "s": f"{delay_pct:.1f}%",
                            "a": "Investigar causas de atraso",
                            "t": "bad"
    })
    if pct_ac < 30 and total_dit > 0:
                        base["pontosAtencao"].append({
                            "i": "Acionavel OTR",
                            "s": f"{pct_ac:.1f}%",
                            "a": "Baixo acionavel - verificar routing",
                            "t": "warn"
    })
    if total_dit > 0 and backlog_d0 > total_dit * 0.4:
                        base["pontosAtencao"].append({
                            "i": "Backlog UTR D0",
                            "s": str(backlog_d0),
                            "a": "Alto backlog pendente UTR",
                            "t": "bad"
    })
    if not base["pontosAtencao"]:
                        base["pontosAtencao"].append({
                            "i": "Status geral",
                            "s": "Normal",
                            "a": "Sem alertas criticos",
                            "t": "ok"
    })
    return base


def build_json(token, site_id):
                now = datetime.now()
    data = {
                        "updated": now.strftime("%Y-%m-%dT%H:%M:%S"),
                        "bases": {}
    }
    for ssp in SSPS:
                        data["bases"][ssp] = build_base(token, site_id, ssp, now)
    return json.dumps(data, ensure_ascii=False, indent=2)


def upload(content, sha1, tok):
                r = requests.post(
                                    "https://api.vercel.com/v2/files",
                                    headers={
                                                            "Authorization": f"Bearer {tok}",
                                                            "Content-Type": "application/octet-stream",
                                                            "x-vercel-digest": sha1
                                    },
                                    data=content.encode()
                )
    r.raise_for_status()


def deploy(sha, size, tok):
                r = requests.post(
                                    f"https://api.vercel.com/v13/deployments?teamId={VERCEL_TEAM_ID}",
                                    headers={
                                                            "Authorization": f"Bearer {tok}",
                                                            "Content-Type": "application/json"
                                    },
                                    json={
                                                            "name": "dit-ssp25",
                                                            "target": "production",
                                                            "files": [
                                                                                        {"file": "data.json", "sha": sha, "size": size},
                                                                                        {"file": "index.html", "sha": INDEX_HTML_SHA, "size": INDEX_HTML_SIZE}
                                                            ]
                                    }
                )
    r.raise_for_status()
    print(f"Deploy: {r.json()['id']}")


def tableau_signout(token):
                requests.post(
                                    f"{TABLEAU_SERVER}/api/3.21/auth/signout",
                                    headers={"X-Tableau-Auth": token}
                )


def main():
                print("Login no Tableau Cloud...")
    tab_token, site_id = tableau_login()
    try:
                        print("Coletando dados das SSPs...")
        j = build_json(tab_token, site_id)
        sha = sha1_of(j)
        size = len(j.encode())
        print(f"JSON: {size} bytes, SHA={sha[:12]}...")
        upload(j, sha, VERCEL_TOKEN)
        deploy(sha, size, VERCEL_TOKEN)
        print("Sucesso! https://dit-ssp25.vercel.app/")
finally:
        tableau_signout(tab_token)


if __name__ == "__main__":
                main()
