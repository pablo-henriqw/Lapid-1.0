# Lapid.ai — Etapa 1: Central de suporte e dashboard

Widget de suporte incorporável, API de reclamações com protocolo e painel administrativo.
Ainda **não** inclui monitoramento, IA, GitHub nem autocorreção (Etapas 2 a 9).

## Rodar (Codespaces/Linux/macOS)
```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env
python scripts/hash_password.py        # cole a linha ADMIN_PASSWORD_HASH no .env e ajuste ADMIN_EMAIL
flask --app backend.app run --debug
```
## Rodar (Windows PowerShell)
```powershell
py -m venv .venv; .\.venv\Scripts\Activate.ps1
pip install -r requirements-dev.txt
copy .env.example .env
python scripts\hash_password.py
flask --app backend.app run --debug
```
Abra `http://localhost:5000/admin`. No **Codespaces**, defina `PROXY_COUNT=1` no `.env` e use a URL encaminhada da porta 5000.

## Testar o widget
1. Entre no painel → **Sites** → conecte um site com o domínio `localhost` (no Codespaces, o host da URL encaminhada, ex.: `xxxx-5000.app.github.dev`).
2. Abra `/demo` (requer `ENABLE_DEMO=true`), clique em **Suporte** e envie um relato.
3. Veja o protocolo (`LPD-AAAAMMDD-0001`) e a reclamação em **Reclamações**.

Em sites reais, copie o código da página **Sites** e cole antes de `</body>`.

## Testes
```bash
pytest
```

## Segurança aplicada
- Segredos só via `.env`; senha do admin armazenada como hash.
- Login com limite de tentativas, sessão nova a cada login, CSRF em todo POST do painel.
- Rotas `/admin/*` protegidas, com CSP estrita e `no-store`.
- Widget autenticado por chave pública + verificação de origem (domínio/subdomínios do site) e rate limit.
- Validação de entrada, limite de 32 KB por requisição, saída escapada (anti-XSS).
- O widget envia apenas `origin + pathname` (sem query string, para não vazar tokens).

## Próximo passo
Etapa 2: monitoramento de erros (Sentry + captura de erros do frontend no widget).
