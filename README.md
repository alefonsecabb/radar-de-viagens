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

## Como funciona

### 1. Disparo automático — GitHub Actions

O arquivo `.github/workflows/daily_monitor.yml` agenda a execução todo dia às 03:00 BRT (06:00 UTC). O GitHub aluga uma máquina virtual temporária, instala as dependências, executa `python main.py` e descarta a máquina ao final — custo zero.

As credenciais (Gmail, API keys) ficam em **Secrets** do repositório e são injetadas como variáveis de ambiente em tempo de execução.

### 2. Orquestrador — `main.py`

Coordena o pipeline em 6 etapas sequenciais:

```
1. Coleta paralela (ThreadPoolExecutor, 4 workers simultâneos)
2. Atualização do histórico de preços
3. Scoring de cruzeiros de reposicionamento
4. Scoring das demais ofertas
5. Geração dos JSONs + publicação no dashboard
6. Envio do e-mail
```

Se um scraper falhar, os outros continuam. O e-mail é enviado mesmo com 0 ofertas.

### 3. Estrutura de dados — `Deal`

Toda oferta coletada é normalizada para o mesmo dataclass `Deal` (`src/scrapers/base_scraper.py`). Campos principais:

| Campo | Descrição |
|---|---|
| `type` | `flight`, `hotel`, `cruise_repositioning`, `package` |
| `price_brl` | Preço por pessoa (R$) |
| `total_3pax_brl` | Total para 3 passageiros |
| `score` | Calculado pelo engine de scoring |
| `label` | `HOT`, `GOOD`, `FAIR` ou `SKIP` |
| `discount_pct` | % de desconto em relação à média histórica |

### 4. Coletores — Scrapers

Três tecnologias de coleta, dependendo do site:

| Tipo | Biblioteca | Quando usar |
|---|---|---|
| HTML estático | BeautifulSoup | Sites sem JavaScript |
| API REST | requests | Sites com API pública |
| JavaScript | Playwright (Chromium) | Sites renderizados no browser |

Todos herdam de `BaseScraper`, que fornece retry automático (3 tentativas com backoff exponencial) e rate limiting por token bucket — cada fonte tem limite diário de requisições para evitar bloqueios.

### 5. Histórico de preços — `src/scoring/price_history.py`

Para cada rota/hotel/navio, o sistema mantém um JSON em `data/history/` com até **90 entradas** (uma por dia de execução):

```json
"VCP-MIA": {
  "entries": [
    {"date": "2026-06-01", "price_brl": 1250.00},
    {"date": "2026-06-02", "price_brl": 1245.00}
  ],
  "moving_avg_brl": 1247.50,
  "sample_count": 2
}
```

Com ≥ 3 amostras, a média móvel é usada como referência de preço justo. O próprio repositório Git funciona como banco de dados — sem infraestrutura externa.

### 6. Engine de scoring — `src/scoring/`

**Cruzeiros de reposicionamento** (`repositioning_scorer.py`):
- Base: 50 pontos (raros e valiosos por natureza)
- Bônus: +20 se sai em < 60 dias, +15 se ≥ 14 noites, +10 por porto brasileiro, +10 por mês de alta temporada
- HOT ≥ 60 pontos, GOOD abaixo disso

**Demais ofertas** (`deal_scorer.py`):

```
Com histórico (≥ 3 amostras):
  score = (média_histórica - preço_atual) / média_histórica × 100

Sem histórico (modo bootstrap):
  Score por faixa de preço absoluta (ex: voo HOT < R$ 400/pax)

Rótulos: HOT ≥ 40% · GOOD ≥ 20% · FAIR ≥ 5% · SKIP < 5%
Filtro:  descarta score < −20% (armadilhas de preço)
```

### 7. E-mail — `src/notifiers/email_sender.py`

Usa Gmail SMTP (porta 465, SSL). O HTML é gerado pelo **Jinja2** a partir do template `templates/email_daily.html`, com os top 10 deals pontuados. Destinatários configurados via variável de ambiente `RECIPIENT_EMAIL` (múltiplos separados por vírgula).

### 8. Dashboard — `src/dashboard/`

Após o scoring, JSONs são gerados em `data/latest/` e copiados para `docs/data/` (pasta servida pelo GitHub Pages). O frontend estático em `docs/` faz `fetch()` desses arquivos e exibe as ofertas com filtros por categoria.

O bot commita e dá push dos JSONs atualizados automaticamente a cada execução (`[skip ci]` na mensagem para não disparar novo workflow).

### 9. Fluxo completo

```
03:00 BRT  →  GitHub Actions inicia a VM
03:01      →  14 scrapers rodam em paralelo (4 por vez)
03:10      →  Histórico de preços atualizado
03:11      →  Scoring calculado, top 10 selecionado
03:12      →  JSONs gerados, commit + push para o repositório
03:13      →  E-mail enviado para os destinatários
03:14      →  Dashboard público atualizado via GitHub Pages
03:15      →  VM destruída
```

## Autor

Alexandre da Fonseca — projeto pessoal de aposentadoria
