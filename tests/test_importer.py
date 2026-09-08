#!/usr/bin/env python3
"""Regressão fixa do parser de currículo (src/importer.py) — rode com:
python tests/test_importer.py

Usa 5 currículos SINTÉTICOS (gerados por IA, nenhuma pessoa real) cobrindo áreas e modelos
diferentes: TI (2 formatos), Direito, Comercial/Vendas, RH/Administrativo. Servem pra travar
bugs concretos já corrigidos uma vez (ex: nome quebrado em várias linhas, empresa/período
colados na mesma linha, vazamento de cabeçalho de seção) sem precisar testar manualmente com
currículos reais toda vez que o parser heurístico for alterado.
"""
import sys, pathlib

BASE = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE / "src"))

from importer import heuristic_parse_curriculum

results = {}

def check(name, condition, detail=""):
    results[name] = bool(condition)
    status = "PASS" if condition else "FAIL"
    print(f"  [{status}] {name}" + (f" — {detail}" if detail and not condition else ""))

# --- Fixture 1: Direito (2 linhas "Cargo - Empresa" / período sozinho na linha seguinte) ---
DIREITO = """
MARIA SOUZA ADVOGADA

email: maria@ex.com
(11) 98888-7777

RESUMO PROFISSIONAL
Advogada com 8 anos de experiência em direito trabalhista e contratos, atuando em escritórios de médio porte com foco em contencioso e consultivo.

HABILIDADES
Direito Trabalhista
Direito Contratual
Excel Avançado
Negociação

EXPERIENCIA PROFISSIONAL
Advogada Sênior - Escritório Alves e Souza
01/2019 - Atual
Responsável por contencioso trabalhista.
Elaboração de pareceres jurídicos.
Negociação de acordos extrajudiciais.

Advogada Júnior - Costa Advocacia
03/2016 - 12/2018
Suporte em processos cíveis.
Análise de contratos comerciais.

FORMAÇÃO
Bacharel em Direito
Universidade Federal - 2015
"""

# --- Fixture 2: TI, formato pipe (CARGO – EMPRESA | LOCAL | DATA), o que o próprio app gera ---
TI_PIPE = """João Silva
email: joao@ex.com

COMPETÊNCIAS TÉCNICAS E TECNOLOGIAS
Python • Django • Docker • React

RESUMO PROFISSIONAL
Desenvolvedor backend com foco em APIs escaláveis.

EXPERIÊNCIA PROFISSIONAL
DESENVOLVEDOR – AUTÔNOMO | LAVRAS/MG | 05/2024 – ATUAL
Atividades desempenhadas: Criação de APIs REST. Manutenção de sistemas legados.

FORMAÇÃO ACADÊMICA
Tecnólogo em Análise e Desenvolvimento de Sistemas
Centro Universitário Unilavras – Conclusão: 2022
"""

# --- Fixture 3: RH/Administrativo, "Cargo | Empresa Data" numa linha só, 2 formações ---
RH_ADMIN = """CARLOS EDUARDO MENDES
ASSISTENTE DE RECURSOS HUMANOS / ADMINISTRATIVO
Local: Curitiba, PR
Tel: (41) 97777-2222
E-mail: carlos.mendes@email.com
LinkedIn: linkedin.com/in/carlosmendes
OBJETIVO PROFISSIONAL
Atuar como Assistente de Recursos Humanos, aplicando sólida experiência em rotinas administrativas, gestão de
documentos e atendimento ao cliente para otimizar os processos de Departamento Pessoal e Recrutamento e
Seleção.
EXPERIÊNCIA PROFISSIONAL
Assistente Administrativo Pleno | Logística Express Junho de 2020 – Atual
Responsável pelo controle de folha de ponto de 50 colaboradores e envio de informações estruturadas para a
contabilidade terceirizada.
Realizou o onboarding administrativo de novos funcionários, organizando contratos, gestão de benefícios e
exames admissionais.
Gerenciou o fluxo de caixa do setor e o atendimento/negociação com fornecedores terceiros.
Auxiliar de Escritório | Clínica Médica Saúde Total Janeiro de 2018 – Maio de 2020
Atendimento ao público presencial e telefônico, atuando diretamente na resolução de conflitos e
agendamento de consultas.
Organização e arquivamento de prontuários e documentos fiscais, garantindo conformidade com regras de
auditoria interna.
FORMAÇÃO ACADÊMICA
Tecnólogo em Gestão de Recursos Humanos
Centro Universitário Curitiba
Em andamento (Previsão: 12/2027)
Ensino Médio Completo
Colégio Estadual do Paraná • Concluído em 2016
CURSOS COMPLEMENTARES
Recrutamento e Seleção na Prática (20h)
Escola de Negócios • 2025
Cálculos Trabalhistas e Rotinas de DP (40h)
Portal EAD • 2024
COMPETÊNCIAS & HABILIDADES
Ferramentas & Conhecimentos Técnicos:
Pacote Office (Word, Excel intermediário), Organização de Arquivos, Atendimento ao Cliente, Facilidade com sistemas
ERP, Rotinas de Departamento Pessoal (DP).
Habilidades Comportamentais (Soft Skills):
Boa comunicação interpessoal, mediação de conflitos, proatividade, organização, foco na experiência do colaborador.
"""

# --- Fixture 4: Comercial/Vendas, nome em 3 linhas (1 palavra cada), experiência em 3 linhas
# (Cargo / Empresa / Período cada um na sua própria linha) ---
VENDAS = """MARIANA
COSTA
RODRIGUES
GERENTE DE VENDAS
CONTATO
LOCALIZAÇÃO
Belo Horizonte, MG
TELEFONE
(31) 98888-1111
E-MAIL
mariana.costa@email.com
LINKEDIN
linkedin.com/in/marianacosta
FORMAÇÃO ACADÊMICA
MBA em Gestão Comercial e
Inteligência de Mercado
FGV • 2022
Bacharelado em Administração de
Empresas
UFMG • 2017
COMPETÊNCIAS
Gestão de Equipes
Prospecção B2B
Negociação Complexa
Planejamento Estratégico
CRM Salesforce & Hubspot
Excel Avançado & Power BI
IDIOMAS
INGLÊS:
Fluente
ESPANHOL:
Básico
RESUMO PROFISSIONAL
Gerente de Vendas com mais de 8 anos de experiência no setor de varejo e B2B. Histórico
comprovado de superação de metas comerciais, expansão de carteira de clientes e
liderança de equipes de alta performance. Especialista em CRM Salesforce, técnicas de
negociação complexas e análise de indicadores de performance (KPIs).
EXPERIÊNCIA PROFISSIONAL
Gerente Comercial Regional
Distribuidora Alfa S.A.
Mar/2021 – Atual
Gerenciei uma equipe de 12 consultores de vendas, superando a meta anual em 115% de
forma consecutiva nos últimos dois anos.
Desenvolvi um novo modelo de prospecção B2B que aumentou a carteira de clientes ativos
em 35%.
Reduzi o ciclo médio de vendas em 10 dias através da implementação de treinamentos
focados na metodologia SPIN Selling.
Executiva de Contas Sênior
Mercado Sul Alimentos
Fev/2018 – Fev/2021
Responsável pela negociação e fechamento de contratos de grande porte, gerando um
faturamento anual de R$ 2,5 milhões.
Utilizei o CRM Salesforce para mapear oportunidades, gerenciar o pipeline e prever
receitas com 95% de precisão.
Recebi o prêmio de "Melhor Vendedora do Ano" em 2019.
"""

# --- Fixture 5: TI, "Cargo | Empresa Data" numa linha só + skills "Rótulo: item1 item2..." ---
TI_ADMIN = """BRUNO SILVA ALMEIDA
DESENVOLVEDOR FRONT-END
São Paulo, SP (11) 99999-0000 bruno.silva@email.com linkedin.com/in/brunosilva
RESUMO PROFISSIONAL
Desenvolvedor Front-End com 3 anos de experiência em desenvolvimento de aplicações web responsivas e dinâmicas.
Especialista em ecossistemas JavaScript, com foco em React.js e TypeScript. Experiência em integração de APIs
RESTful e metodologias ágeis (Scrum). Busco oportunidade para otimizar a experiência do usuário e contribuir para
arquiteturas de código limpo.
EXPERIÊNCIA PROFISSIONAL
Desenvolvedor Front-End | TechSoluções Inovadoras Janeiro de 2024 – Atual
Liderou a migração de uma plataforma legada para React.js, resultando em um aumento de 40% na velocidade de
carregamento das páginas.
Implementou design responsivo utilizando Tailwind CSS, reduzindo a taxa de rejeição móvel em 15%.
Colaborou com a equipe de UX/UI para criar componentes de interface reutilizáveis utilizando Storybook.
Desenvolvedor Web Júnior | WebStart Agência Digital Agosto de 2022 – Dezembro de 2023
Desenvolveu e manteve mais de 15 sites institucionais utilizando HTML5, CSS3 e JavaScript (ES6).
Garantiu a compatibilidade cross-browser e a acessibilidade na web seguindo as diretrizes WCAG.
Realizou manutenção de bancos de dados relacionais utilizando MySQL.
FORMAÇÃO ACADÊMICA
Bacharelado em Ciência da Computação Concluído em 2023
Universidade Cidade de São Paulo
COMPETÊNCIAS
Linguagens: JavaScript TypeScript HTML5 CSS3 SQL
Frameworks & Libs: React.js Next.js Tailwind CSS Node.js Storybook
Ferramentas & Outros: Git GitHub Docker Jira Figma Scrum
Idiomas: Português (Nativo) Inglês (Intermediário)
"""

print("=" * 60)
print("REGRESSÃO DO PARSER DE CURRÍCULO (tests/test_importer.py)")
print("=" * 60)

# --- Direito ---
d = heuristic_parse_curriculum(DIREITO)
check("direito.nome", d["personal_info"].get("name") == "Maria Souza Advogada", d["personal_info"].get("name"))
check("direito.skills>=4", len(d["skills"]) >= 4, str(d["skills"]))
check("direito.2_experiencias", len(d["experiences"]) == 2, str(len(d["experiences"])))
if len(d["experiences"]) == 2:
    e1, e2 = d["experiences"]
    check("direito.exp1.empresa", "Souza" in e1["company"], e1["company"])
    check("direito.exp1.cargo", "Advogada" in e1["position"], e1["position"])
    check("direito.exp2.empresa", e2["company"] == "Costa Advocacia", e2["company"])
check("direito.formacao", len(d["education"]) == 1 and "Direito" in d["education"][0]["degree"], str(d["education"]))

# --- TI formato pipe (regressão original) ---
d = heuristic_parse_curriculum(TI_PIPE)
check("ti_pipe.nome", d["personal_info"].get("name") == "João Silva", d["personal_info"].get("name"))
check("ti_pipe.skills", {"Python", "Django", "Docker", "React"} <= set(d["skills"]), str(d["skills"]))
check("ti_pipe.1_experiencia", len(d["experiences"]) == 1, str(len(d["experiences"])))
if d["experiences"]:
    check("ti_pipe.exp.empresa", d["experiences"][0]["company"] == "Autônomo", d["experiences"][0]["company"])
check("ti_pipe.formacao", len(d["education"]) == 1 and d["education"][0]["year"] == "2022", str(d["education"]))

# --- RH/Administrativo ---
d = heuristic_parse_curriculum(RH_ADMIN)
check("rh.nome", d["personal_info"].get("name") == "Carlos Eduardo Mendes", d["personal_info"].get("name"))
check("rh.2_experiencias", len(d["experiences"]) == 2, str(len(d["experiences"])))
if len(d["experiences"]) == 2:
    e1, e2 = d["experiences"]
    # empresa e período não podem vir colados/misturados (bug já corrigido uma vez)
    check("rh.exp1.empresa_sem_data", e1["company"] == "Logística Express", e1["company"])
    check("rh.exp1.periodo", "2020" in e1["period"] and "Atual" in e1["period"], e1["period"])
    check("rh.exp2.empresa_sem_data", e2["company"] == "Clínica Médica Saúde Total", e2["company"])
check("rh.2_formacoes", len(d["education"]) == 2, str(len(d["education"])))
check("rh.skills_sem_lixo", not any(s.strip().endswith(":") or "& Habilidades" in s for s in d["skills"]), str(d["skills"]))

# --- Comercial/Vendas ---
d = heuristic_parse_curriculum(VENDAS)
check("vendas.nome_em_3_linhas", d["personal_info"].get("name") == "Mariana Costa Rodrigues", d["personal_info"].get("name"))
check("vendas.6_skills", len(d["skills"]) == 6, str(d["skills"]))
check("vendas.2_experiencias", len(d["experiences"]) == 2, str(len(d["experiences"])))
if len(d["experiences"]) == 2:
    e1, e2 = d["experiences"]
    check("vendas.exp1.completa", e1["position"] == "Gerente Comercial Regional" and e1["company"] == "Distribuidora Alfa S.A.", str(e1))
    check("vendas.exp2.completa", e2["position"] == "Executiva De Contas Sênior" and e2["company"] == "Mercado Sul Alimentos", str(e2))

# --- TI (2º modelo) ---
d = heuristic_parse_curriculum(TI_ADMIN)
check("ti2.nome", d["personal_info"].get("name") == "Bruno Silva Almeida", d["personal_info"].get("name"))
check("ti2.2_experiencias", len(d["experiences"]) == 2, str(len(d["experiences"])))
if len(d["experiences"]) == 2:
    e1, e2 = d["experiences"]
    check("ti2.exp1.empresa_sem_data", e1["company"] == "Techsoluções Inovadoras", e1["company"])
    check("ti2.exp2.empresa_sem_data", e2["company"] == "Webstart Agência Digital", e2["company"])
check("ti2.formacao_ano", len(d["education"]) == 1 and d["education"][0]["year"] == "2023", str(d["education"]))
check("ti2.skills_nao_vazio", len(d["skills"]) > 0, str(d["skills"]))

print("=" * 60)
total = len(results)
passed = sum(1 for v in results.values() if v)
print(f"RESULTADO: {passed}/{total} PASS")
print("=" * 60)
sys.exit(0 if passed == total else 1)
