import os
import html
from datetime import datetime
from pathlib import Path
from typing import List, Dict

from config import Config

def _esc_attr(v) -> str:
    """Escapa valor pra caber com segurança dentro de um atributo HTML (data-value=\"...\")
    — título/empresa/local vêm de scraping e podem ter aspas ou '&' sem aviso."""
    return str(v or "").replace("&", "&amp;").replace('"', "&quot;").replace("<", "&lt;").replace(">", "&gt;")

def _esc(v) -> str:
    """Escapa texto vindo de scraping (título/empresa/local/descrição) antes de colocar no
    CORPO do HTML — sem isso, uma vaga com '<script>' na descrição executa no navegador de
    quem abre o relatório. _esc_attr acima só cobre o data-value dos atributos, não o texto
    visível das células da tabela."""
    return html.escape(str(v or ""), quote=True)

def _esc_url(v) -> str:
    """Só permite URL http(s); qualquer outro esquema (javascript:, data:, etc.) vindo de uma
    vaga maliciosa vira link morto em vez de executar algo ao clicar."""
    u = str(v or "").strip()
    if not u.lower().startswith(("http://", "https://")):
        return "#"
    return html.escape(u, quote=True)

# Ordenação por clique no cabeçalho da tabela (mesmo padrão de 3 estados do Histórico da GUI:
# crescente -> decrescente -> sem ordenação) — puro JS vanilla, sem lib nenhuma, porque o
# relatório é um arquivo HTML estático aberto direto no navegador, sem servidor por trás.
_SORT_SCRIPT = """
<script>
(function(){
  var table = document.getElementById('jobsTable');
  if (!table || !table.tBodies[0]) return;
  var tbody = table.tBodies[0];
  var headers = table.querySelectorAll('th[data-sort]');
  var rows = Array.prototype.slice.call(tbody.rows);
  rows.forEach(function(row, i){ row.setAttribute('data-original-index', i); });
  var state = { col: null, dir: null };

  function clearArrows(){
    headers.forEach(function(h){ h.textContent = h.getAttribute('data-label'); });
  }
  headers.forEach(function(h){
    h.setAttribute('data-label', h.textContent.trim());
    h.style.cursor = 'pointer';
    h.title = 'Clique para ordenar';
    h.addEventListener('click', function(){
      var col = h.getAttribute('data-sort');
      if (state.col !== col) { state.col = col; state.dir = 'asc'; }
      else if (state.dir === 'asc') { state.dir = 'desc'; }
      else { state.col = null; state.dir = null; }

      clearArrows();
      var current = Array.prototype.slice.call(tbody.rows);
      if (state.col === null) {
        current.sort(function(a,b){
          return (+a.getAttribute('data-original-index')) - (+b.getAttribute('data-original-index'));
        });
      } else {
        h.textContent = h.getAttribute('data-label') + (state.dir === 'asc' ? ' ▲' : ' ▼');
        var numeric = (col === 'match');
        current.sort(function(a,b){
          var ca = a.querySelector('td[data-col="' + col + '"]');
          var cb = b.querySelector('td[data-col="' + col + '"]');
          var va = ca ? ca.getAttribute('data-value') : '';
          var vb = cb ? cb.getAttribute('data-value') : '';
          var cmp;
          if (numeric) { cmp = (parseFloat(va) || 0) - (parseFloat(vb) || 0); }
          else { cmp = va.localeCompare(vb, 'pt-BR', {sensitivity: 'base'}); }
          return state.dir === 'asc' ? cmp : -cmp;
        });
      }
      current.forEach(function(row){ tbody.appendChild(row); });
    });
  });
})();
</script>
"""

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

        # file:/// aqui é caminho que o próprio app gerou (não vem de scraping), então não
        # precisa do mesmo tratamento de _esc_url — mas o texto ainda passa por _esc por
        # padrão de higiene (path no Windows não deveria ter '<'/'>' mas não custa nada).
        resume_link = f"<a href='file:///{_esc(j.get('resume_pdf_path'))}' target='_blank'>[PDF] Ver CV</a>" if j.get('resume_pdf_path') else "-"
        cover_link = f"<a href='file:///{_esc(j.get('cover_letter_path'))}' target='_blank'>[TXT] Ver Carta</a>" if j.get('cover_letter_path') else "-"

        rows_html += f"""
        <tr>
            <td><strong>#{idx}</strong></td>
            <td data-col="title" data-value="{_esc_attr(j.get('title'))}">
                <strong>{_esc(j.get('title'))}</strong><br>
                <small style="color: #666;">Plataforma: {_esc(j.get('platform', '').upper())}</small>
            </td>
            <td data-col="company" data-value="{_esc_attr(j.get('company'))}">{_esc(j.get('company'))}</td>
            <td data-col="location" data-value="{_esc_attr(j.get('location', 'N/A'))}">{_esc(j.get('location', 'N/A'))}</td>
            <td data-col="match" data-value="{score}"><span class="score-pill {score_class}">{score}%</span></td>
            <td data-col="status" data-value="{_esc_attr(status)}">{status_badge}</td>
            <td><div class="desc-box">{_esc(short_desc)}</div></td>
            <td>
                <a href="{_esc_url(j.get('url'))}" target="_blank" class="btn-link">[Link] Abrir Vaga</a><br>
                {resume_link}<br>
                {cover_link}
            </td>
        </tr>
        """

    html_content = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <title>Relatorio VampHunter - {now_str}</title>
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
        th[data-sort] {{ user-select: none; }}
        th[data-sort]:hover {{ background: #dde6f0; }}
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
        <h1>VampHunter - Relatorio de Candidaturas</h1>
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

        <table id="jobsTable">
            <thead>
                <tr>
                    <th>#</th>
                    <th data-sort="title">Vaga</th>
                    <th data-sort="company">Empresa</th>
                    <th data-sort="location">Local</th>
                    <th data-sort="match">Match</th>
                    <th data-sort="status">Status</th>
                    <th>Descricao Resumida</th>
                    <th>Ações / Links</th>
                </tr>
            </thead>
            <tbody>
                {rows_html if rows_html else '<tr><td colspan="8" style="text-align:center;">Nenhuma vaga encontrada nesta rodada.</td></tr>'}
            </tbody>
        </table>
    </div>
    {_SORT_SCRIPT}
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
        f"# VampHunter - Relatorio Executivo ({now_str})\n",
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