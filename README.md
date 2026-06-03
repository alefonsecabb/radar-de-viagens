# ✈ Radar de Viagens — Monitor Diário de Barganhas

Busca automaticamente as melhores ofertas de passagens, hotéis, cruzeiros e pacotes para **3 passageiros** partindo de **VCP · GRU · CGH**. Entrega um digest por e-mail todo dia às 03:00 BRT e publica um dashboard público no GitHub Pages.

## Funcionalidades

- 15 fontes monitoradas: Amadeus (API), Azul, LATAM, GOL, TAP, Swiss, Booking, Trivago, MSC, Costa, CruiseCritic, Decolar, Hurb, CVC
- Scoring automático: compara preço atual com média histórica → classifica como **HOT / GOOD / FAIR**
- Cruzeiros de reposicionamento: scoring especial com bônus por urgência, duração e porto brasileiro
- Dashboard web com filtros por categoria e ordenação por desconto/preço/data
- E-mail HTML diário com top 10 barganhas e links diretos para compra
- Histórico de preços em JSON (90 dias por rota) — sem banco de dados externo
- Custo zero: GitHub Actions (grátis) + GitHub Pages (grátis)

## Configuração

### 1. Fork / clone do repositório

```bash
git clone https://github.com/SEU_USUARIO/Projeto_viagens_Aposentadoria.git
cd Projeto_viagens_Aposentadoria
```

### 2. Instalar dependências localmente

```bash
pip install -r requirements.txt
playwright install chromium
```

### 3. Criar o arquivo `.env`

```bash
cp .env.example .env
# Edite o .env com suas credenciais
```

Credenciais necessárias:

| Variável | Como obter |
|---|---|
| `AMADEUS_CLIENT_ID` | [developers.amadeus.com](https://developers.amadeus.com) → criar conta grátis → "My Self-Service Workspace" |
| `AMADEUS_CLIENT_SECRET` | Mesmo local acima |
| `GMAIL_APP_PASSWORD` | Conta Google → Segurança → Verificação em 2 etapas → **Senhas de app** |

### 4. Configurar Secrets no GitHub

No repositório GitHub: **Settings → Secrets and variables → Actions → New repository secret**

Adicione os mesmos 4 secrets: `AMADEUS_CLIENT_ID`, `AMADEUS_CLIENT_SECRET`, `GMAIL_USER`, `GMAIL_APP_PASSWORD`

### 5. Ativar GitHub Pages

**Settings → Pages → Source**: `Deploy from a branch` → branch `main` → pasta `/docs`

A URL do dashboard será: `https://SEU_USUARIO.github.io/Projeto_viagens_Aposentadoria/`

## Rodar localmente

```bash
python main.py
```

Os JSONs serão gerados em `data/latest/`. Para visualizar o dashboard:

```bash
cd docs && python -m http.server 8080
# Abra http://localhost:8080 no browser
```

## Estrutura

```
├── src/
│   ├── scrapers/       # 14 scrapers (Playwright + requests/BS4)
│   ├── scoring/        # Engine de preços históricos e classificação
│   ├── notifiers/      # Envio de e-mail via Gmail SMTP
│   ├── dashboard/      # Geração de JSONs e git push
│   └── utils/          # Config, rate limiter, HTTP client
├── data/
│   ├── history/        # Histórico de preços (JSON, 90 dias/rota)
│   └── latest/         # Última coleta + top_deals.json
├── docs/               # Dashboard GitHub Pages (HTML/JS estático)
├── templates/          # Template Jinja2 do e-mail HTML
├── main.py             # Entry point
└── .github/workflows/  # Cron job diário (06:00 UTC)
```

## Cruzeiros de Reposicionamento

São os navios que precisam se mover entre regiões sazonais — de graça para a companhia, muito barato para você. O sistema monitora especialmente:

- **Março–Abril**: Américas → Europa (embarca em Santos, Rio ou Miami)
- **Outubro–Novembro**: Europa → Américas (retorno)

Score recebe +50 de bônus base + bônus adicionais por urgência, duração e porto de embarque.

## Autor

Alexandre da Fonseca — projeto pessoal de aposentadoria
