# ═══════════════════════════════════════════════════════════════════
# MORDZIX AI - DEPLOY NA LINUX OVH (TYLKO LINUX!)
# ═══════════════════════════════════════════════════════════════════

## 🐧 LINUX ONLY - ŻADNEGO WINDOWSA!

### KROK 1: Połącz się z serwerem OVH

```bash
ssh -i ~/.ssh/id_ed25519_ovh ubuntu@162.19.220.29
```

---

## KROK 2: Zainstaluj Node.js 18 LTS (Ubuntu 24.04)

```bash
# Aktualizuj system
sudo apt-get update
sudo apt-get upgrade -y

# Zainstaluj Node.js z NodeSource
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
sudo apt-get install -y nodejs

# Sprawdź wersje
node --version   # v18.x.x
npm --version    # 9.x.x
```

---

## KROK 3: Prześlij pliki projektu (z Windows TYLKO UPLOAD)

**NA WINDOWS (tylko raz - upload plików):**
```powershell
# Utwórz katalog na serwerze
ssh -i C:\Users\48501\.ssh\id_ed25519_ovh ubuntu@162.19.220.29 "sudo mkdir -p /root/mordzix-ai && sudo chown -R ubuntu:ubuntu /workspace"

# Prześlij WSZYSTKIE pliki projektu
scp -i C:\Users\48501\.ssh\id_ed25519_ovh -r C:\Users\48501\Desktop\mrd\* ubuntu@162.19.220.29:/root/mordzix-ai/
```

**TO WSZYSTKO Z WINDOWSA - WIĘCEJ NIC!**

---

## KROK 4: Build Angular NA SERWERZE LINUX

```bash
# SSH do serwera
ssh -i ~/.ssh/id_ed25519_ovh ubuntu@162.19.220.29

# Przejdź do frontendu
cd /root/mordzix-ai/frontend

# Zainstaluj zależności
npm install

# Build production
npm run build:prod

# Sprawdź output
ls -lh dist/mordzix-ai/
```

**OCZEKIWANY OUTPUT:**
```
total 360K
-rw-r--r-- 1 ubuntu ubuntu  15K index.html
-rw-r--r-- 1 ubuntu ubuntu 250K main.a1b2c3d4.js
-rw-r--r-- 1 ubuntu ubuntu  90K polyfills.e5f6g7h8.js
-rw-r--r-- 1 ubuntu ubuntu  15K styles.i9j0k1l2.css
drwxr-xr-x 2 ubuntu ubuntu 4.0K assets/
```

---

## KROK 5: Uruchom deployment script

```bash
cd /root/mordzix-ai
chmod +x start_production.sh
sudo ./start_production.sh
```

**SKRYPT ZROBI:**
- ✅ Zainstaluje Python 3.12
- ✅ Utworzy venv
- ✅ Zainstaluje pip packages
- ✅ Utworzy bazę SQLite
- ✅ Skonfiguruje Nginx
- ✅ Ustawi SSL (Let's Encrypt)
- ✅ Skonfiguruje Supervisor
- ✅ Uruchomi backend

---

## KROK 6: Weryfikacja

```bash
# Health check
curl http://localhost:8080/health

# Frontend
curl -I http://localhost:8080/

# Status Supervisor
sudo supervisorctl status mordzix

# Logi
sudo supervisorctl tail -f mordzix
```

---

## KROK 7: Sprawdź w przeglądarce

```
https://mordxixai.xyz/
```

Powinieneś zobaczyć:
- Czarny interfejs
- Header: "🚀 Mordzix AI"
- Status: "✓ Online" (zielony)
- Pole do wpisywania wiadomości

---

## 🔄 UPDATE FRONTENDU (tylko Linux)

Gdy chcesz zaktualizować frontend:

```bash
# SSH
ssh -i ~/.ssh/id_ed25519_ovh ubuntu@162.19.220.29

# Rebuild
cd /root/mordzix-ai/frontend
npm run build:prod

# Restart backend
sudo supervisorctl restart mordzix

# Sprawdź
curl -I https://mordxixai.xyz/
```

---

## 🔥 AUTOMATYCZNY UPDATE (skrypt na serwerze)

Stwórz: `/root/mordzix-ai/update_frontend.sh`

```bash
#!/bin/bash
cd /root/mordzix-ai/frontend
echo "Building frontend..."
npm run build:prod

if [ $? -eq 0 ]; then
    echo "✓ Build success, restarting backend..."
    sudo supervisorctl restart mordzix
    echo "✓ Deploy complete!"
    echo "Check: https://mordxixai.xyz/"
else
    echo "✗ Build failed!"
    exit 1
fi
```

Nadaj uprawnienia:
```bash
chmod +x /root/mordzix-ai/update_frontend.sh
```

Uruchom:
```bash
/root/mordzix-ai/update_frontend.sh
```

---

## 📊 MONITORING

```bash
# Status wszystkich usług
sudo supervisorctl status

# Logi backend
sudo supervisorctl tail -f mordzix

# Logi Nginx
tail -f /root/mordzix-ai/logs/nginx_access.log
tail -f /root/mordzix-ai/logs/nginx_error.log

# Logi Gunicorn
tail -f /root/mordzix-ai/logs/gunicorn_error.log

# Wykorzystanie zasobów
htop
df -h
```

---

## 🚨 TROUBLESHOOTING

### Problem: npm install fails

```bash
# Fix permissions
sudo chown -R ubuntu:ubuntu /root/mordzix-ai

# Try again
cd /root/mordzix-ai/frontend
npm install
```

### Problem: Build out of memory

```bash
# Zwiększ pamięć Node.js
NODE_OPTIONS="--max-old-space-size=4096" npm run build:prod
```

### Problem: Backend nie serwuje frontendu

```bash
# Sprawdź czy dist istnieje
ls -la /root/mordzix-ai/frontend/dist/mordzix-ai/

# Jeśli nie ma - rebuild
cd /root/mordzix-ai/frontend
npm run build:prod

# Restart backend
sudo supervisorctl restart mordzix
```

---

## ⚡ SZYBKI DEPLOY (1 komenda)

```bash
ssh -i ~/.ssh/id_ed25519_ovh ubuntu@162.19.220.29 "cd /root/mordzix-ai/frontend && npm run build:prod && sudo supervisorctl restart mordzix"
```

---

## 🎯 PODSUMOWANIE

### Z WINDOWSA (tylko raz):
```powershell
# Upload plików
scp -i C:\Users\48501\.ssh\id_ed25519_ovh -r C:\Users\48501\Desktop\mrd\* ubuntu@162.19.220.29:/root/mordzix-ai/
```

### NA LINUXIE (wszystko inne):
```bash
# 1. SSH
ssh -i ~/.ssh/id_ed25519_ovh ubuntu@162.19.220.29

# 2. Zainstaluj Node.js
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
sudo apt-get install -y nodejs

# 3. Build frontend
cd /root/mordzix-ai/frontend
npm install
npm run build:prod

# 4. Deploy backend
cd /root/mordzix-ai
sudo ./start_production.sh

# 5. Sprawdź
curl https://mordxixai.xyz/
```

**KONIEC - WSZYSTKO NA LINUXIE!** 🐧
