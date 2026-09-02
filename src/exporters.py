import requests
import json
from pathlib import Path
from typing import List, Dict

def export_to_notion(jobs: List[Dict], notion_token: str, database_id: str) -> dict:
    """Exporta vagas para Notion Database via API."""
    if not notion_token or not database_id:
        return {"ok": False, "error": "Notion token/database_id não configurados"}
    headers = {
        "Authorization": f"Bearer {notion_token}",
        "Notion-Version": "2022-06-28",
        "Content-Type": "application/json"
    }
    success = 0
    errors = []
    for job in jobs[:20]:  # limita a 20 para não estourar rate limit
        payload = {
            "parent": {"database_id": database_id},
            "properties": {
                "Name": {"title": [{"text": {"content": job.get('title','')[:100]}}]},
                "Company": {"rich_text": [{"text": {"content": job.get('company','')}}]},
                "Location": {"rich_text": [{"text": {"content": job.get('location','')}}]},
                "Platform": {"select": {"name": job.get('platform','other')[:20]}},
                "URL": {"url": job.get('url','')},
                "Match": {"number": job.get('match_score',0)},
                "Status": {"select": {"name": job.get('status','pending')[:20]}}
            }
        }
        try:
            r = requests.post("https://api.notion.com/v1/pages", headers=headers, json=payload, timeout=10)
            if r.status_code in (200,201):
                success += 1
            else:
                errors.append(f"{job.get('title')}: {r.status_code}")
        except Exception as e:
            errors.append(str(e))
    return {"ok": success>0, "success": success, "errors": errors[:5]}

def export_to_sheets_webhook(jobs: List[Dict], webhook_url: str) -> dict:
    """Exporta via webhook genérico (Google Sheets via Apps Script, Zapier, Make)."""
    if not webhook_url:
        return {"ok": False, "error": "webhook_url não configurado"}
    # payload simples com lista de vagas
    payload = {
        "jobs": [{"title": j.get('title'), "company": j.get('company'), "location": j.get('location'), "url": j.get('url'), "platform": j.get('platform'), "match": j.get('match_score',0), "status": j.get('status')} for j in jobs[:30]],
        "count": len(jobs),
        "generated_at": __import__('datetime').datetime.now().isoformat()
    }
    try:
        r = requests.post(webhook_url, json=payload, timeout=10)
        return {"ok": r.status_code in (200,201,202,204), "status": r.status_code, "response": r.text[:300]}
    except Exception as e:
        return {"ok": False, "error": str(e)}

def export_jobs(jobs: List[Dict], notion_token: str = "", notion_db: str = "", webhook_url: str = "") -> dict:
    """Orquestra exports configurados."""
    results = {}
    if notion_token and notion_db:
        results['notion'] = export_to_notion(jobs, notion_token, notion_db)
    if webhook_url:
        results['webhook'] = export_to_sheets_webhook(jobs, webhook_url)
    return results
