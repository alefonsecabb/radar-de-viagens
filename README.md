
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
  
  
  1. A ideia central

  O projeto é um robô de vigilância de preços de viagens. Todo dia de madrugada ele:
  1. Visita mais de 14 sites e APIs de viagem
  2. Coleta as ofertas disponíveis
  3. Compara com o histórico de preços dos últimos 90 dias
  4. Classifica as melhores oportunidades
  5. Manda um e-mail com o resumo
  6. Publica os dados em um dashboard público

  Tudo isso acontece automaticamente, sem custo de servidor, usando o GitHub como
  infraestrutura.

  ---
  2. O disparo automático — GitHub Actions

  O arquivo .github/workflows/daily_monitor.yml é o "despertador" do sistema:

  on:
    schedule:
      - cron: '0 6 * * *'   # 06:00 UTC = 03:00 BRT, todo dia

  O GitHub lê esse arquivo e, todo dia às 03h da manhã (horário de Brasília), aluga uma
  máquina virtual temporária no servidor deles, instala Python, instala as dependências, e
  executa python main.py. Quando termina, a máquina some. Você não paga nada por isso.

  As senhas e chaves de API ficam armazenadas como Secrets no GitHub (nunca no código), e são
   injetadas como variáveis de ambiente:

  GMAIL_USER:         ${{ secrets.GMAIL_USER }}
  GMAIL_APP_PASSWORD: ${{ secrets.GMAIL_APP_PASSWORD }}
  RECIPIENT_EMAIL:    alefonsecabb@gmail.com,melissafabiane@gmail.com

  ---
  3. O ponto de entrada — main.py

  O main.py é o maestro que coordena tudo. Ele segue 6 etapas em sequência:

  1. Coleta paralela de dados (scraping)
  2. Atualiza histórico de preços
  3. Calcula scores dos cruzeiros de reposicionamento
  4. Calcula scores das demais ofertas
  5. Gera JSONs e publica no dashboard
  6. Envia o e-mail

  O passo 1 usa paralelismo (ThreadPoolExecutor com 4 workers) — ou seja, até 4 scrapers
  rodam simultaneamente, economizando tempo. Se um scraper falhar, os outros continuam
  normalmente.

  ---
  4. A estrutura de dados — Deal

  Toda oferta coletada é representada por um objeto Deal (definido em
  src/scrapers/base_scraper.py). É como uma ficha padronizada:

  @dataclass
  class Deal:
      type: str           # "flight", "hotel", "cruise_repositioning", "package"
      title: str
      price_brl: float    # preço por pessoa
      total_3pax_brl: float  # total para 3 passageiros
      source: str         # "PassagensPromo", "Kiwi", etc.
      booking_url: str
      origin: str
      destination: str
      outbound_date: str
      return_date: str
      score: float        # calculado depois
      label: str          # "HOT", "GOOD", "FAIR", "SKIP"
      discount_pct: float
      # ... e mais campos específicos por tipo

  Todos os scrapers produzem esse mesmo formato — é um contrato entre os coletores e o
  restante do sistema.

  ---
  5. Os coletores — Scrapers

  Há dois tipos de scraper:

  a) Scrapers de HTML (BeautifulSoup) — para sites estáticos:
  - Baixam a página HTML, procuram elementos pelo seletor CSS
  - Ex: PassagensPromo, VaiDePromo

  b) Scrapers de API REST — para sites com API:
  - Fazem chamada HTTP com parâmetros, recebem JSON
  - Ex: KiwiFlights — busca voos com origem em VCP/GRU/CGH para "qualquer lugar", 3
  passageiros, até 180 dias

  c) Scrapers com Playwright — para sites que precisam de JavaScript:
  - Abrem um navegador real (Chromium headless) e esperam a página carregar
  - Ex: CostaCruises — detecta cruzeiros de reposicionamento por palavras-chave

  Todos herdam de BaseScraper, que fornece gratuitamente:
  - Retry automático: se falhar, tenta mais 3 vezes (espera 2s, 4s, 8s)
  - Rate limiting: token bucket — cada fonte tem um limite diário de requisições

  ---
  6. O histórico de preços — price_history.py

  Esse é o "cérebro" da comparação. Para cada rota/hotel/navio, o sistema mantém um arquivo
  JSON em data/history/ com até 90 entradas (uma por dia):

  "VCP-MIA": {
    "entries": [
      {"date": "2026-06-01", "price_brl": 1250.00},
      {"date": "2026-06-02", "price_brl": 1245.00},
      {"date": "2026-06-03", "price_brl": 1280.00}
    ],
    "moving_avg_brl": 1258.33,
    "sample_count": 3
  }

  A cada execução, o preço de hoje é adicionado e a média móvel é recalculada. Com no mínimo
  3 amostras, o sistema já consegue identificar se o preço está abaixo da média.

  ---
  7. O sistema de pontuação — Scoring

  Há dois scorers com lógicas diferentes:

  a) Cruzeiros de reposicionamento (repositioning_scorer.py):
  - Pontuação começa em 50 (base alta, são raros e valiosos)
  - Ganha bônus: +20 se sai em menos de 60 dias, +15 se tem 14+ noites, +10 por porto de
  embarque nacional, +10 por mês de alta temporada
  - Rótulo: HOT se ≥ 60, GOOD abaixo disso

  b) Demais ofertas (deal_scorer.py):
  Se tem histórico (≥ 3 amostras):
    desconto % = (média_histórica - preço_atual) / média_histórica × 100
    score = desconto %

  Se não tem histórico (modo bootstrap):
    Usa tabela de referência por tipo:
      Voo HOT < R$400/pax, GOOD < R$900/pax ...

  Depois, filtra tudo com score abaixo de -20% (armadilha de preço) e ordena do maior para o
  menor.

  ---
  8. O e-mail — email_sender.py

  Usa SMTP direto com Gmail (porta 465, SSL). O HTML do e-mail é gerado pelo Jinja2 — um
  sistema de templates onde você escreve HTML com variáveis:

  {% for deal in deals %}
    <div style="border-left: 4px solid {{ deal.label_color }}">
      <strong>{{ deal.title }}</strong>
      R$ {{ deal.price_brl | format_currency }}
      {{ deal.label }}  <!-- HOT / GOOD / FAIR -->
    </div>
  {% endfor %}

  O template fica em templates/email_daily.html. O sistema renderiza esse template com os top
   10 deals e envia para todos os e-mails da lista RECIPIENT_EMAILS.

  ---
  9. O dashboard público — json_builder.py + GitHub Pages

  Após o scoring, o sistema gera arquivos JSON em docs/data/:

  docs/data/top_deals.json         ← top 10 geral
  docs/data/flights_latest.json    ← só voos
  docs/data/hotels_latest.json     ← só hotéis
  docs/data/cruises_latest.json    ← só cruzeiros
  docs/data/packages_latest.json   ← só pacotes

  O GitHub Pages serve a pasta docs/ como site estático. O frontend JavaScript do dashboard
  faz fetch("data/top_deals.json") e exibe as ofertas. Quando o robô commita os JSONs
  atualizados, o dashboard se atualiza automaticamente.

  ---
  10. O fluxo completo em uma linha do tempo

  03:00 BRT  →  GitHub Actions acorda
  03:01      →  14 scrapers rodam em paralelo (4 por vez)
  03:10      →  Histórico de preços atualizado
  03:11      →  Scores calculados, top 10 selecionado
  03:12      →  JSONs gerados, commit feito, push para GitHub
  03:13      →  E-mail enviado para alefonsecabb e melissafabiane
  03:14      →  Dashboard público atualizado
  03:15      →  Máquina virtual do GitHub é destruída

  ---
  Resumo da arquitetura

  ┌──────────────┬──────────────────────────────────┬─────────────────────────────────────┐
  │    Camada    │            Tecnologia            │               Arquivo               │
  ├──────────────┼──────────────────────────────────┼─────────────────────────────────────┤
  │ Agendamento  │ GitHub Actions (cron)            │ .github/workflows/daily_monitor.yml │
  ├──────────────┼──────────────────────────────────┼─────────────────────────────────────┤
  │ Orquestração │ Python (ThreadPoolExecutor)      │ main.py                             │
  ├──────────────┼──────────────────────────────────┼─────────────────────────────────────┤
  │ Coleta       │ Requests + BeautifulSoup +       │ src/scrapers/*.py                   │
  │              │ Playwright                       │                                     │
  ├──────────────┼──────────────────────────────────┼─────────────────────────────────────┤
  │ Histórico    │ JSON + média móvel               │ src/scoring/price_history.py        │
  ├──────────────┼──────────────────────────────────┼─────────────────────────────────────┤
  │ Pontuação    │ Algoritmo de desconto %          │ src/scoring/deal_scorer.py          │
  ├──────────────┼──────────────────────────────────┼─────────────────────────────────────┤
  │ Notificação  │ Gmail SMTP + Jinja2              │ src/notifiers/email_sender.py       │
  ├──────────────┼──────────────────────────────────┼─────────────────────────────────────┤
  │ Dashboard    │ GitHub Pages + JSON              │ docs/data/*.json                    │
  ├──────────────┼──────────────────────────────────┼─────────────────────────────────────┤
  │ Configuração │ Variáveis de ambiente + .env     │ src/utils/config.py                 │
  └──────────────┴──────────────────────────────────┴─────────────────────────────────────┘

  O ponto mais elegante do projeto é que ele usa o próprio Git como banco de dados — o
  histórico de preços, os dados do dashboard e os logs de execução ficam todos versionados no
   repositório, sem nenhum custo de infraestrutura.

  ---
  Tem alguma parte específica que quer aprofundar?

─────────────────────────────────────────────────────────────────────────────────────────────
 Ready to code?

 Here is Claude's plan:
╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌
 Tarefa: Explicação técnica do projeto Radar de Viagens

 Contexto

 O usuário quer entender como o projeto funciona tecnicamente, como se fosse uma aula.
 Esta é uma tarefa de explicação/educação — nenhuma alteração de código é necessária.

 Resultado

 Explicação completa fornecida diretamente na conversa, cobrindo:
 - Arquitetura geral e fluxo de dados
 - Camadas do sistema (scraping, scoring, e-mail, dashboard)
 - Automação via GitHub Actions
 - Exemplos de código dos módulos principais
╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌

   repositório, sem nenhum custo de infraestrutura.

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
