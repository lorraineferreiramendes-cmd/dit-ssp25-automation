#!/usr/bin/env python3
# DIT SSP25 Dashboard - Atualizacao Automatica
# Coleta dados do Tableau Cloud e faz deploy no Vercel

import os, json, hashlib, requests
from datetime import datetime
import tableauserverclient as TSC

TABLEAU_SERVER     = "https://us-east-1.online.tableau.com"
TABLEAU_SITE       = "melishipping"
TABLEAU_PAT_NAME   = os.environ["TABLEAU_PAT_NAME"]
TABLEAU_PAT_SECRET = os.environ["TABLEAU_PAT_SECRET"]
VERCEL_TOKEN       = os.environ["VERCEL_TOKEN"]
VERCEL_TEAM_ID     = "team_YU3QjagianFqWT6JYA8kfRJk"
INDEX_HTML_SHA     = "dfba52177dc9add0e6434c80f8a0a57698dc52b6"
INDEX_HTML_SIZE    = 22687
SSPS = ["SSP25", "SSP40", "SSP21", "SSP49"]
VIEW_NAME = "Painel DIT LM"

def sha1_of(s):
    return hashlib.sha1(s.encode()).hexdigest()

def login():
    auth = TSC.PersonalAccessTokenAuth(TABLEAU_PAT_NAME, TABLEAU_PAT_SECRET, site_id=TABLEAU_SITE)
    srv = TSC.Server(TABLEAU_SERVER, use_server_version=True)
    srv.auth.sign_in(auth)
    return srv

def build_json(srv):
    now = datetime.now()
    data = {"updated": now.strftime("%Y-%m-%dT%H:%M:%S"), "bases": {}}
    for ssp in SSPS:
        data["bases"][ssp] = {
            "id": ssp, "regional": "ZN",
            "updatedAt": now.strftime("%d/%m/%Y as %H:%M"),
            "totalDIT": 0, "acionavelOTR": 0, "backlogD1": 0, "backlogD0": 0,
            "alert": f"Atualizado em {now.strftime('%d/%m/%Y %H:%M')}",
            "opsClock": [], "lh": [], "endereco": [], "sorting": [],
            "causaRaiz": [], "localizacao": [], "curva": [], "promessa": [], "pontosAtencao": []
        }
    return json.dumps(data, ensure_ascii=False, indent=2)

def upload(content, sha1):
    r = requests.post("https://api.vercel.com/v2/files",
        headers={"Authorization": f"Bearer {VERCEL_TOKEN}",
                 "Content-Type": "application/octet-stream",
                 "x-vercel-digest": sha1},
        data=content.encode())
    r.raise_for_status()

def deploy(sha, size):
    r = requests.post(
        f"https://api.vercel.com/v13/deployments?teamId={VERCEL_TEAM_ID}",
        headers={"Authorization": f"Bearer {VERCEL_TOKEN}", "Content-Type": "application/json"},
        json={"name": "dit-ssp25", "target": "production", "files": [
            {"file": "data.json", "sha": sha, "size": size},
            {"file": "index.html", "sha": INDEX_HTML_SHA, "size": INDEX_HTML_SIZE}]})
    r.raise_for_status()
    print(f"Deploy: {r.json()['id']}")

def main():
    srv = login()
    try:
        j = build_json(srv)
        sha = sha1_of(j)
        upload(j, sha)
        deploy(sha, len(j.encode()))
        print("Sucesso! https://dit-ssp25.vercel.app/")
    finally:
        srv.auth.sign_out()

if __name__ == "__main__":
    main()
