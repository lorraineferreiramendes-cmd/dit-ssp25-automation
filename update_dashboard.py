#!/usr/bin/env python3
# DIT SSP25 Dashboard - Atualizacao Automatica
# Coleta dados reais do Tableau Cloud e faz deploy no Vercel

import os, json, hashlib, requests, csv, io
from datetime import datetime

TABLEAU_SERVER   = "https://us-east-1.online.tableau.com"
TABLEAU_SITE     = "melishipping"
TABLEAU_PAT_NAME   = os.environ["TABLEAU_PAT_NAME"]
TABLEAU_PAT_SECRET = os.environ["TABLEAU_PAT_SECRET"]
VERCEL_TOKEN     = os.environ["VERCEL_TOKEN"]
VERCEL_TEAM_ID   = "team_YU3QjagianFqWT6JYA8kfRJk"
INDEX_HTML_SHA   = "98c697dcc5a6ed4a1abf03fff6c5380c5bb99ff7"
INDEX_HTML_SIZE  = 16563
SSPS = ["SSP25", "SSP40", "SSP21", "SSP49"]

# IDs das views publicadas no Tableau Cloud
VIEW_PREVIA     = "921ab9c2-292e-47c7-b428-4475d6e68f5c"  # Previa Delay LM - tem DIT por SVC
VIEW_ACIONAVEL  = "daf3db95-71a7-4b14-b7c3-f4c4e68744e1"  # One Page - Acionavel OTR
VIEW_STATUS     = "617ae9fd-0e77-42ff-8914-fed2071f802c"  # Report - Status Pacote


def sha1_of(s):
        return hashlib.sha1(s.encode()).hexdigest()


def tableau_login():
        r = requests.post(
                    f"{TABLEAU_SERVER}/api/3.21/auth/signin",
                    headers={"Content-Type": "application/json", "Accept": "application/json"},
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


def build_base(token, site_id, ssp, now):
        print(f"  Coletando dados para {ssp}...")

    # ---- Previa Delay LM: Total DIT, Delay ----
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

    # ---- One Page: Acionavel OTR ----
    rows_ac = get_view_data(token, site_id, VIEW_ACIONAVEL, ssp)
    acionavel_otr = 0
    acionavel_lp  = 0
    acionavel_utr = 0
    for row in rows_ac:
                ac  = (row.get("Acionaveis") or "").strip()
                mn  = (row.get("Measure Names") or "").strip()
                mv  = row.get("Measure Values") or "0"
                if mn == "DIT":
                                if "OTR" in ac:
                                                    acionavel_otr = parse_num(mv)
                elif "LP" in ac:
                                    acionavel_lp  = parse_num(mv)
elif "UTR" in ac:
                acionavel_utr = parse_num(mv)

    # ---- Report: Status de Pacotes ----
    rows_status = get_view_data(token, site_id, VIEW_STATUS, ssp)
                   backlog_d0  = 0  # Pendente tratativa UTR
    in_rota     = 0  # Em rota
    para_desp   = 0  # Para despachar
    for row in rows_status:
                mn  = (row.get("Measure Names") or "").strip()
                sp  = (row.get("Status Pacote") or "").strip()
                mv  = row.get("Measure Values") or "0"
                if mn == "DIT":
                                if "UTR" in sp:
                                                    backlog_d0 = parse_num(mv)
                elif "rota" in sp.lower():
                                    in_rota = parse_num(mv)
elif "despachar" in sp.lower():
                para_desp = parse_num(mv)

    # Backlog D-1 estimado = total - em rota
    backlog_d1 = max(0, total_dit - in_rota)

    # ---- Montar estrutura da base ----
    pct_ac = round(acionavel_otr / total_dit * 100, 1) if total_dit > 0 else 0.0

    # Alert color
    if delay_pct > 2.0:
                alert = f"Delay {delay_pct:.1f}% - Atencao!"
elif total_dit == 0:
            alert = "Sem dados disponiveis"
else:
            alert = f"Atualizado em {now.strftime('%d/%m/%Y %H:%M')}"

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
                                {"l": "Em rota", "v": in_rota,
                                              "p": round(in_rota/total_dit*100,1) if total_dit>0 else 0.0,
                                              "t": "ok" if in_rota/max(total_dit,1) > 0.4 else "warn"},
                                {"l": "Pendente UTR", "v": backlog_d0,
                                              "p": round(backlog_d0/total_dit*100,1) if total_dit>0 else 0.0,
                                              "t": "bad" if backlog_d0/max(total_dit,1) > 0.3 else "warn"},
                                {"l": "Para despachar", "v": para_desp,
                                              "p": round(para_desp/total_dit*100,1) if total_dit>0 else 0.0,
                                              "t": "warn"}
                ],
                "lh": [],
                "endereco": [],
                "sorting": [],
                "causaRaiz": [],
                "localizacao": [],
                "curva": [],
                "promessa": [
                                {"d": "Hoje", "l": now.strftime("%Y-%m-%d"),
                                              "v": total_dit, "p": 100.0, "t": "ok"}
                ],
                "pontosAtencao": []
    }

    # Pontos de atencao automaticos
    if delay_pct > 2.0:
                base["pontosAtencao"].append({
                                "i": "Delay LM", "s": f"{delay_pct:.1f}%",
                                "a": "Investigar causas de atraso", "t": "bad"
                })
            if pct_ac < 30 and total_dit > 0:
                        base["pontosAtencao"].append({
                                        "i": "Acionavel OTR", "s": f"{pct_ac:.1f}%",
                                        "a": "Baixo acionavel - verificar routing", "t": "warn"
                        })
                    if backlog_d0 > total_dit * 0.4 and total_dit > 0:
                                base["pontosAtencao"].append({
                                                "i": "Backlog UTR D0", "s": str(backlog_d0),
                                                "a": "Alto backlog pendente UTR", "t": "bad"
                                })
                            if not base["pontosAtencao"]:
                                        base["pontosAtencao"].append({
                                                        "i": "Status geral", "s": "Normal",
                                                        "a": "Sem alertas criticos", "t": "ok"
                                        })

    return base


def build_json(token, site_id):
        now  = datetime.now()
        data = {"updated": now.strftime("%Y-%m-%dT%H:%M:%S"), "bases": {}}
        for ssp in SSPS:
                    data["bases"][ssp] = build_base(token, site_id, ssp, now)
                return json.dumps(data, ensure_ascii=False, indent=2)


def upload(content, sha1, token_vercel):
        r = requests.post(
            "https://api.vercel.com/v2/files",
            headers={"Authorization": f"Bearer {token_vercel}",
                                      "Content-Type": "application/octet-stream",
                                      "x-vercel-digest": sha1},
            data=content.encode()
)
    r.raise_for_status()


def deploy(sha, size, token_vercel):
        r = requests.post(
            f"https://api.vercel.com/v13/deployments?teamId={VERCEL_TEAM_ID}",
            headers={"Authorization": f"Bearer {token_vercel}",
                                      "Content-Type": "application/json"},
            json={"name": "dit-ssp25", "target": "production", "files": [
                            {"file": "data.json",  "sha": sha,            "size": size},
                            {"file": "index.html", "sha": INDEX_HTML_SHA, "size": INDEX_HTML_SIZE}
            ]}
)
    r.raise_for_status()
    print(f"Deploy: {r.json()['id']}")


def tableau_signout(token):
        requests.post(
            f"{TABLEAU_SERVER}/api/3.21/auth/signout",
            headers={"X-Tableau-Auth": token}
)


def main():
        print("Fazendo login no Tableau Cloud...")
    tab_token, site_id = tableau_login()
    try:
                print("Coletando dados das SSPs...")
                j    = build_json(tab_token, site_id)
                sha  = sha1_of(j)
                size = len(j.encode())
                print(f"JSON gerado: {size} bytes, SHA={sha[:12]}...")
                print("Fazendo upload para Vercel...")
                upload(j, sha, VERCEL_TOKEN)
                print("Criando deployment...")
                deploy(sha, size, VERCEL_TOKEN)
                print("Sucesso! https://dit-ssp25.vercel.app/")
finally:
        tableau_signout(tab_token)


if __name__ == "__main__":
        main()
