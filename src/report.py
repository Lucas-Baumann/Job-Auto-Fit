import os
from datetime import datetime
from pathlib import Path
from typing import List, Dict

from config import Config

def generate_html_report(jobs: List[Dict], output_file: Path) -> Path:
    """Gera um relatório HTML completo e elegante das vagas processadas na execução."""
    now_str = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    
    applied_count = sum(1 for j in jobs if j.get('status') in ['applied', 'prepared'])
    high_match_count = sum(1 for j in jobs if j.get('match_score', 0) >= Config.MIN_MATCH_SCORE)
    
    rows_html = ""
    for idx, j in enumerate(jobs, 1):
        score = j.get('match_score', 0)
        score_class = "score-high" if score >= 75 else ("score-med" if score >= 50 else "score-low")
        status = j.get('status', 'pending')
        
        status_badge = {
            'applied': '<span class="badge badge-success">Enviado / Candidatado</span>',
            'prepared': '<span class="badge badge-info">PDF & Carta Prontos</span>',
            'skipped': '<span class="badge badge-warning">Score Baixo (Ignorado)</span>',
            'failed': '<span class="badge badge-danger">Falha no Envio</span>'
        }.get(status, f'<span class="badge">{status}</span>')
        
        desc = j.get('description', '') or ''
        short_desc = (desc[:250] + '...') if len(desc) > 250 else desc
        
        resume_link = f"<a href='file:///{j.get('resume_pdf_path')}' target='_blank'>[PDF] Ver CV</a>" if j.get('resume_pdf_path') else "-"
        cover_link = f"<a href='file:///{j.get('cover_letter_path')}' target='_blank'>[TXT] Ver Carta</a>" if j.get('cover_letter_path') else "-"

        rows_html += f"""
        <tr>
            <td><strong>#{idx}</strong></td>
            <td>
                <strong>{j.get('title')}</strong><br>
                <small style="color: #666;">Plataforma: {j.get('platform', '').upper()}</small>
            </td>
            <td>{j.get('company')}</td>
            <td>{j.get('location', 'N/A')}</td>
            <td><span class="score-pill {score_class}">{score}%</span></td>
            <td>{status_badge}</td>
            <td><div class="desc-box">{short_desc}</div></td>
            <td>
                <a href="{j.get('url')}" target="_blank" class="btn-link">[Link] Abrir Vaga</a><br>
                {resume_link}<br>
                {cover_link}
            </td>
        </tr>
        """

    html_content = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <title>Relatorio JobAutoFit - {now_str}</title>
    <style>
        body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background: #f4f6f9; margin: 0; padding: 20px; color: #333; }}
        .container {{ max-width: 1200px; margin: 0 auto; background: #fff; padding: 30px; border-radius: 10px; box-shadow: 0 4px 15px rgba(0,0,0,0.05); }}
        h1 {{ color: #1a2b4c; margin-top: 0; border-bottom: 2px solid #e2e8f0; padding-bottom: 10px; }}
        .stats {{ display: flex; gap: 20px; margin-bottom: 25px; }}
        .stat-card {{ flex: 1; background: #f8fafc; border: 1px solid #e2e8f0; padding: 15px; border-radius: 8px; text-align: center; }}
        .stat-card h3 {{ margin: 0; font-size: 28px; color: #2b6cb0; }}
        .stat-card p {{ margin: 5px 0 0; color: #718096; font-size: 14px; }}
        table {{ width: 100%; border-collapse: collapse; margin-top: 10px; font-size: 14px; }}
        th, td {{ padding: 12px 15px; text-align: left; border-bottom: 1px solid #e2e8f0; vertical-align: top; }}
        th {{ background: #edf2f7; color: #2d3748; font-weight: 600; }}
        tr:hover {{ background: #f8fafc; }}
        .score-pill {{ display: inline-block; padding: 4px 10px; border-radius: 12px; font-weight: bold; font-size: 13px; }}
        .score-high {{ background: #c6f6d5; color: #22543d; }}
        .score-med {{ background: #feebc8; color: #744210; }}
        .score-low {{ background: #fed7d7; color: #742a2a; }}
        .badge {{ display: inline-block; padding: 4px 8px; border-radius: 4px; font-size: 12px; font-weight: 500; }}
        .badge-success {{ background: #38a169; color: white; }}
        .badge-info {{ background: #3182ce; color: white; }}
        .badge-warning {{ background: #dd6b20; color: white; }}
        .badge-danger {{ background: #e53e3e; color: white; }}
        .desc-box {{ max-width: 300px; max-height: 80px; overflow-y: auto; font-size: 12px; color: #4a5568; line-height: 1.4; }}
        .btn-link {{ color: #3182ce; text-decoration: none; font-weight: 500; }}
        .btn-link:hover {{ text-decoration: underline; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>JobAutoFit - Relatorio de Candidaturas</h1>
        <p><strong>Data da Execução:</strong> {now_str}</p>
        
        <div class="stats">
            <div class="stat-card">
                <h3>{len(jobs)}</h3>
                <p>Vagas Analisadas</p>
            </div>
            <div class="stat-card">
                <h3>{high_match_count}</h3>
                <p>Vagas de Alto Match (&ge; {Config.MIN_MATCH_SCORE}%)</p>
            </div>
            <div class="stat-card">
                <h3>{applied_count}</h3>
                <p>Processadas / Enviadas</p>
            </div>
        </div>

        <table>
            <thead>
                <tr>
                    <th>#</th>
                    <th>Vaga</th>
                    <th>Empresa</th>
                    <th>Local</th>
                    <th>Match</th>
                    <th>Status</th>
                    <th>Descricao Resumida</th>
                    <th>Ações / Links</th>
                </tr>
            </thead>
            <tbody>
                {rows_html if rows_html else '<tr><td colspan="8" style="text-align:center;">Nenhuma vaga encontrada nesta rodada.</td></tr>'}
            </tbody>
        </table>
    </div>
</body>
</html>
"""
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(html_content)
        
    return output_file

def generate_markdown_report(jobs: List[Dict], output_file: Path) -> Path:
    """Gera um relatório alternativo em formato Markdown."""
    now_str = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    
    md = [
        f"# JobAutoFit - Relatorio Executivo ({now_str})\n",
        f"**Total de vagas analisadas:** {len(jobs)}\n",
        "---",
        "| # | Vaga | Empresa | Local | Match | Status | Descricao |",
        "|---|---|---|---|---|---|---|"
    ]
    
    for idx, j in enumerate(jobs, 1):
        desc = (j.get('description', '')[:120] + '...').replace('\n', ' ')
        md.append(f"| {idx} | [{j.get('title')}]({j.get('url')}) | {j.get('company')} | {j.get('location')} | {j.get('match_score')}% | {j.get('status')} | {desc} |")
        
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("\n".join(md))
        
    return output_file