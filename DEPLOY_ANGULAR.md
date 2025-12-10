# ═══════════════════════════════════════════════════════════════════
# MORDZIX AI - ANGULAR FRONTEND DEPLOYMENT
# Kompletna instrukcja krok-po-kroku dla Windows i Linux
# ═══════════════════════════════════════════════════════════════════

## 📋 SPIS TREŚCI
1. [Wymagania wstępne](#wymagania)
2. [Instalacja na Windows](#windows)
3. [Instalacja na Linux (OVH)](#linux)
4. [Build i deploy](#build)
5. [Troubleshooting](#troubleshooting)

---

## 🔧 WYMAGANIA WSTĘPNE {#wymagania}

### Node.js i npm
- **Node.js 18+ LTS** (https://nodejs.org/)
- npm 9+ (instaluje się z Node.js)

### Sprawdź wersje:
```bash
node --version   # Powinno pokazać v18.x.x lub wyżej
npm --version    # Powinno pokazać 9.x.x lub wyżej
```

---

## 💻 INSTALACJA NA WINDOWS {#windows}

### KROK 1: Zainstaluj Node.js
```powershell
# Pobierz z: https://nodejs.org/en/download/
# Wybierz: Windows Installer (.msi) 64-bit
# Uruchom instalator, zaznacz "Add to PATH"
# Zrestartuj PowerShell po instalacji

# Sprawdź:
node --version
npm --version
```

### KROK 2: Przejdź do katalogu frontend
```powershell
cd C:\Users\48501\Desktop\mrd\frontend
```

### KROK 3: Zainstaluj zależności Angular
```powershell
npm install
```

**Oczekiwany output:**
```
added 234 packages, and audited 235 packages in 45s
found 0 vulnerabilities
```

### KROK 4: Build development (dev test)
```powershell
npm start
```

**Co się stanie:**
- Uruchomi się dev server na `http://localhost:4200`
- Otwórz przeglądarkę i sprawdź czy działa
- **UWAGA:** Dev server łączy się z backendem na `http://localhost:8080`
- Najpierw uruchom backend: `cd .. ; python app.py`

### KROK 5: Build production
```powershell
npm run build:prod
```

**Co się stanie:**
- Angular zbuduje zoptymalizowaną wersję w `frontend/dist/mordzix-ai/`
- Pliki będą zminifikowane i gotowe do produkcji
- Backend (`app.py`) automatycznie ich użyje

### KROK 6: Uruchom backend
```powershell
cd ..
python app.py
```

**Sprawdź w przeglądarce:**
- `http://localhost:8080` - Powinien załadować się Angular frontend
- `http://localhost:8080/docs` - API dokumentacja (FastAPI)
- `http://localhost:8080/health` - Status backendu

---

## 🐧 INSTALACJA NA LINUX (OVH SERVER) {#linux}

### KROK 1: Połącz się z serwerem
```bash
ssh -i C:\Users\48501\.ssh\id_ed25519_ovh ubuntu@162.19.220.29
```

### KROK 2: Zainstaluj Node.js 18 LTS (Ubuntu 24.04)
```bash
# Aktualizuj system
sudo apt-get update

# Zainstaluj Node.js z NodeSource repo
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
sudo apt-get install -y nodejs

# Sprawdź wersje
node --version   # v18.x.x
npm --version    # 9.x.x
```

### KROK 3: Przejdź do katalogu projektu
```bash
cd /root/mordzix-ai/frontend
```

### KROK 4: Zainstaluj zależności
```bash
npm install
```

**Jeśli wystąpią błędy z uprawnieniami:**
```bash
sudo chown -R $USER:$USER /root/mordzix-ai
npm install
```

### KROK 5: Build production
```bash
npm run build:prod
```

**Output:**
```
✔ Browser application bundle generation complete.
✔ Copying assets complete.
✔ Index html generation complete.

Initial Chunk Files               | Names         |  Raw Size
main.a1b2c3d4.js                  | main          | 250.45 kB | 
polyfills.e5f6g7h8.js             | polyfills     |  90.21 kB |
styles.i9j0k1l2.css               | styles        |  15.33 kB |

Build at: 2025-10-16T10:30:45.123Z - Hash: a1b2c3d4e5f6g7h8 - Time: 12345ms

✔ Built successfully
```

### KROK 6: Sprawdź build
```bash
ls -lh dist/mordzix-ai/
```

**Powinno pokazać:**
```
-rw-r--r-- 1 ubuntu ubuntu  15K index.html
-rw-r--r-- 1 ubuntu ubuntu 250K main.a1b2c3d4.js
-rw-r--r-- 1 ubuntu ubuntu  90K polyfills.e5f6g7h8.js
-rw-r--r-- 1 ubuntu ubuntu  15K styles.i9j0k1l2.css
drwxr-xr-x 2 ubuntu ubuntu 4.0K assets/
```

### KROK 7: Uruchom backend (manual test)
```bash
cd /root/mordzix-ai
source .venv/bin/activate
python app.py
```

**W nowym terminalu sprawdź:**
```bash
curl http://localhost:8080/
curl http://localhost:8080/health
curl http://localhost:8080/api
```

### KROK 8: Deployment z Supervisor (auto-restart)
```bash
# Backend już powinien być skonfigurowany przez start_production.sh
sudo supervisorctl restart mordzix

# Sprawdź status
sudo supervisorctl status mordzix

# Logi
sudo supervisorctl tail -f mordzix
```

---

## 🚀 BUILD I DEPLOY - SZYBKI PRZEPŁYW {#build}

### WINDOWS → LINUX (pełny deploy)

**1. Na Windows (lokalny build):**
```powershell
cd C:\Users\48501\Desktop\mrd\frontend
npm run build:prod
```

**2. Prześlij build na serwer:**
```powershell
cd ..
scp -i C:\Users\48501\.ssh\id_ed25519_ovh -r frontend/dist/mordzix-ai ubuntu@162.19.220.29:/root/mordzix-ai/frontend/dist/
```

**3. Na serwerze (restart):**
```bash
ssh -i C:\Users\48501\.ssh\id_ed25519_ovh ubuntu@162.19.220.29
sudo supervisorctl restart mordzix
```

**4. Sprawdź w przeglądarce:**
```
https://mordxixai.xyz/
```

---

### LINUX (bezpośredni build na serwerze)

**1. SSH do serwera:**
```bash
ssh -i C:\Users\48501\.ssh\id_ed25519_ovh ubuntu@162.19.220.29
```

**2. Build:**
```bash
cd /root/mordzix-ai/frontend
npm run build:prod
```

**3. Restart backendu:**
```bash
sudo supervisorctl restart mordzix
```

**4. Sprawdź:**
```bash
curl -I https://mordxixai.xyz/
```

---

## 🔥 AUTOMATYCZNY DEPLOY (SKRYPT)

### PowerShell (Windows)

```powershell
# deploy_angular.ps1
cd C:\Users\48501\Desktop\mrd\frontend
npm run build:prod

if ($LASTEXITCODE -eq 0) {
    Write-Host "✓ Build success, uploading..." -ForegroundColor Green
    scp -i C:\Users\48501\.ssh\id_ed25519_ovh -r dist/mordzix-ai ubuntu@162.19.220.29:/root/mordzix-ai/frontend/dist/
    
    Write-Host "✓ Restarting server..." -ForegroundColor Green
    ssh -i C:\Users\48501\.ssh\id_ed25519_ovh ubuntu@162.19.220.29 "sudo supervisorctl restart mordzix"
    
    Write-Host "✓ Deploy complete!" -ForegroundColor Green
    Write-Host "Check: https://mordxixai.xyz/" -ForegroundColor Cyan
} else {
    Write-Host "✗ Build failed!" -ForegroundColor Red
}
```

### Bash (Linux)

```bash
#!/bin/bash
# deploy_angular.sh

cd /root/mordzix-ai/frontend
npm run build:prod

if [ $? -eq 0 ]; then
    echo "✓ Build success, restarting..."
    sudo supervisorctl restart mordzix
    echo "✓ Deploy complete!"
    echo "Check: https://mordxixai.xyz/"
else
    echo "✗ Build failed!"
    exit 1
fi
```

---

## 🛠️ TROUBLESHOOTING {#troubleshooting}

### Problem: `npm install` fails with EACCES

**Błąd:**
```
npm ERR! code EACCES
npm ERR! syscall mkdir
npm ERR! path /usr/local/lib/node_modules
```

**Rozwiązanie (Linux):**
```bash
# NIE używaj sudo npm install!
# Zamiast tego:
mkdir ~/.npm-global
npm config set prefix '~/.npm-global'
echo 'export PATH=~/.npm-global/bin:$PATH' >> ~/.bashrc
source ~/.bashrc
```

---

### Problem: `ng build` not found

**Błąd:**
```
'ng' is not recognized as an internal or external command
```

**Rozwiązanie:**
```bash
# Angular CLI nie został zainstalowany globalnie
# Używaj npm scripts zamiast:
npm run build:prod
# Zamiast: ng build --configuration production
```

---

### Problem: Backend nie serwuje frontendu

**Objawy:**
- `http://localhost:8080/` pokazuje 404
- `http://localhost:8080/docs` działa

**Rozwiązanie:**
```bash
# Sprawdź czy dist/ istnieje:
ls -la frontend/dist/mordzix-ai/

# Jeśli nie ma, zbuduj:
cd frontend
npm run build:prod

# Sprawdź logi backendu:
# Na Windows:
python app.py
# Na Linux:
sudo supervisorctl tail -f mordzix
```

---

### Problem: CORS errors w przeglądarce

**Błąd w Console:**
```
Access to XMLHttpRequest at 'http://localhost:8080/api/chat/assistant' 
from origin 'http://localhost:4200' has been blocked by CORS policy
```

**Rozwiązanie:**
Backend (`app.py`) już ma CORS włączony:
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Development: allow all
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

Jeśli nadal występuje problem:
1. Sprawdź czy backend działa: `curl http://localhost:8080/health`
2. Sprawdź environment.ts - czy apiUrl jest poprawny?

---

### Problem: Frontend załadowany ale nie łączy się z API

**Objawy:**
- Frontend działa
- Wiadomości nie wysyłają się
- Console pokazuje 401/403

**Rozwiązanie:**
```typescript
// Sprawdź: frontend/src/environments/environment.prod.ts
export const environment = {
  production: true,
  apiUrl: '',  // Pusty = ten sam host (dobre dla production)
  authToken: 'ssjjMijaja6969'  // MUSI się zgadzać z backendem!
};
```

Backend auth token jest w `.env`:
```bash
AUTH_TOKEN=ssjjMijaja6969
```

---

### Problem: Build działa lokalnie, ale nie na serwerze

**Błąd:**
```
FATAL ERROR: Ineffective mark-compacts near heap limit
Allocation failed - JavaScript heap out of memory
```

**Rozwiązanie (zwiększ pamięć Node.js):**
```bash
# Build z większą pamięcią:
NODE_OPTIONS="--max-old-space-size=4096" npm run build:prod
```

---

## 📊 WERYFIKACJA DEPLOYMENTU

### Checklist po deploy:

```bash
# 1. Health check
curl https://mordxixai.xyz/health
# Oczekiwane: {"status":"healthy"}

# 2. API docs
curl -I https://mordxixai.xyz/docs
# Oczekiwane: HTTP/1.1 200 OK

# 3. Frontend
curl -I https://mordxixai.xyz/
# Oczekiwane: HTTP/1.1 200 OK + HTML content

# 4. Chat test (przez API)
curl -X POST https://mordxixai.xyz/api/chat/assistant \
  -H "Authorization: Bearer ssjjMijaja6969" \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [{"role":"user","content":"test"}],
    "user_id": "curl_test",
    "use_memory": false
  }'
# Oczekiwane: {"response":"..."}
```

### Manual test w przeglądarce:

1. Otwórz: `https://mordxixai.xyz/`
2. Powinieneś zobaczyć: Czarny interfejs z nagłówkiem "🚀 Mordzix AI"
3. Wpisz wiadomość: "Cześć!"
4. Kliknij "Wyślij" lub naciśnij Enter
5. Powinieneś zobaczyć animację ładowania (3 kropki)
6. Po ~2-5s powinna pojawić się odpowiedź asystenta

---

## 🎯 QUICK REFERENCE

### Najważniejsze komendy:

```bash
# DEVELOPMENT (localhost)
npm start                 # Dev server z hot-reload
npm run build             # Build development
npm run build:prod        # Build production

# DEPLOY (production)
npm run build:prod        # Na Windows lub Linux
scp -r dist/* server:/path/  # Upload do serwera
sudo supervisorctl restart mordzix  # Restart backendu

# TROUBLESHOOTING
npm install               # Reinstall dependencies
rm -rf node_modules       # Cleanup
npm cache clean --force   # Clear cache
ls -la dist/mordzix-ai/   # Check build output
```

---

## 📞 SUPPORT

Jeśli nic nie działa:

1. Sprawdź logi backendu: `sudo supervisorctl tail -f mordzix`
2. Sprawdź logi Nginx: `tail -f /root/mordzix-ai/logs/nginx_error.log`
3. Sprawdź Console w przeglądarce (F12)
4. Sprawdź czy build istnieje: `ls -la frontend/dist/mordzix-ai/`

---

**Autor:** Mordzix AI Team  
**Wersja:** 5.0.0  
**Data:** 16.10.2025
