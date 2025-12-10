# Third-Party Dependencies (Summary)

> Zbiorcze zestawienie nazw i wersji. Pełne teksty licencji generuj automatycznie w CI (bez ujawniania kodu źródłowego projektu).

## Python (`requirements.txt`)
- `fastapi==0.114.1`
- `uvicorn[standard]==0.30.3`
- `pydantic==2.9.2`
- `python-multipart==0.0.9`
- `sse-starlette==1.8.2`
- `httpx==0.27.2`
- `aiohttp==3.9.5`
- `requests==2.32.3`
- `beautifulsoup4==4.12.3`
- `readability-lxml==0.8.1`
- `lxml==5.2.2`
- `lxml_html_clean==0.1.1`
- `aiosqlite==0.20.0`
- `redis==5.2.0`
- `spacy==3.7.5`
- `sentence-transformers==3.0.1`
- `scikit-learn==1.5.2`
- `numpy>=1.19.0,<2.0.0`
- `openai==1.35.0`
- `PyPDF2==3.0.1`
- `Pillow==10.3.0`
- `pytesseract==0.3.10`
- `orjson>=3.10.0`
- `python-dotenv==1.0.0`
- `prometheus-client==0.20.0`
- `psutil==5.9.8`
- `matplotlib==3.8.4`
- `gunicorn==22.0.0`
- `pytest==8.2.2`
- `pytest-asyncio==0.23.7`
- `markdown==3.7`
- `SQLAlchemy==2.0.35`
- `alembic==1.13.3`
- `passlib[bcrypt]==1.7.4`
- `python-jose[cryptography]==3.3.0`
- `duckduckgo-search==6.3.5`
- `wikipedia==1.4.0`
- `arxiv==2.1.3`
- `Jinja2==3.1.4`
- `pyyaml==6.0.2`
- `colorama==0.4.6`

## Frontend (`package.json`)
**dependencies:**
- `@tanstack/react-query`: `^5.12.0`
- `axios`: `^1.6.2`
- `date-fns`: `^2.30.0`
- `dompurify`: `^3.0.6`
- `lucide-react`: `^0.294.0`
- `marked`: `^11.0.0`
- `react`: `^18.2.0`
- `react-dom`: `^18.2.0`
- `react-router-dom`: `^6.20.0`
- `terser`: `^5.44.0`
- `zustand`: `^4.4.7`

**devDependencies:**
- `@types/dompurify`: `^3.0.5`
- `@types/react`: `^18.2.42`
- `@types/react-dom`: `^18.2.17`
- `@vitejs/plugin-react`: `^4.2.1`
- `autoprefixer`: `^10.4.16`
- `postcss`: `^8.4.32`
- `tailwindcss`: `^3.3.6`
- `typescript`: `^5.3.3`
- `vite`: `^5.0.7`

---
### Automatyczne pozyskiwanie tekstów licencji (CI)
- **Python:** `pip-licenses --format=markdown --with-authors --with-urls > docs/THIRD_PARTY_LICENSES_PY.md`
- **Node:** `npx license-checker --production --json > docs/THIRD_PARTY_LICENSES_NODE.json`

> Wygenerowane pliki dodaj jako artefakty CI lub commituj w `docs/`.
