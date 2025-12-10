# 🚀 Instalacja na OVH VPS - Mordzix AI

## 📋 Wymagania OVH VPS

**Zalecane:**
- VPS Starter (2 vCores, 4GB RAM, 40GB SSD) - ~20 PLN/miesiąc
- Ubuntu 22.04 LTS
- Python 3.10+

---

## 🔧 Instalacja Krok po Kroku

### 1️⃣ Połącz się z VPS

```bash
ssh ubuntu@your-vps-ip
# lub
ssh root@your-vps-ip
```

---

### 2️⃣ Zainstaluj Wymagane Pakiety

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Python & dependencies
sudo apt install -y python3 python3-pip python3-venv git curl wget

# Install optional tools
sudo apt install -y htop nano screen tmux

# Check Python version (min 3.10)
python3 --version
```

---

### 3️⃣ Utwórz Użytkownika (jeśli używasz root)

```bash
# Create user
sudo adduser mordzix
sudo usermod -aG sudo mordzix

# Switch to user
su - mordzix
```

---

### 4️⃣ Upload Aplikacji

**Method A: Git (zalecane)**
```bash
cd ~
git clone https://github.com/ahui69/aktywmrd.git
cd aktywmrd
# Folder mrd/ lub full/ - oba działają
```

**Method B: SCP (upload z lokalnej)**
```bash
# Z lokalnej maszyny:
scp -r /workspace/full/ ubuntu@your-vps-ip:/home/ubuntu/mordzix
```

**Method C: Tar.gz**
```bash
# Lokalnie:
cd /workspace
tar -czf mordzix.tar.gz full/

# Upload:
scp mordzix.tar.gz ubuntu@your-vps-ip:/home/ubuntu/

# Na VPS:
cd ~
tar -xzf mordzix.tar.gz
mv full mordzix
cd mordzix
```

---

### 5️⃣ Skonfiguruj Aplikację

```bash
cd ~/mordzix  # lub aktywmrd/mrd

# Skopiuj .env
cp .env.example .env
nano .env
```

**Wypełnij klucze API w .env:**
```bash
AUTH_TOKEN=jakis_silny_token_12345

# WYMAGANE:
LLM_API_KEY=twoj_klucz_deepinfra

# OPCJONALNE (ale zalecane):
SERPAPI_KEY=twoj_klucz_serpapi
FIRECRAWL_API_KEY=twoj_klucz_firecrawl
OTM_API_KEY=twoj_klucz_opentripmap
REPLICATE_API_KEY=twoj_klucz_replicate
```

**Zapisz i wyjdź:** `Ctrl+X`, `Y`, `Enter`

---

### 6️⃣ Uruchom Aplikację

```bash
cd ~/mordzix
./start.sh
```

**Co robi start.sh:**
- ✅ Sprawdza Python
- ✅ Instaluje brakujące pakiety
- ✅ Tworzy katalogi (uploads, logs)
- ✅ Zabija stare sesje
- ✅ Uruchamia serwer na porcie 8080

**Aplikacja działa na:**
```
http://your-vps-ip:8080
```

---

### 7️⃣ Uruchom w Tle (Screen/Tmux)

**Option A: Screen**
```bash
screen -S mordzix
cd ~/mordzix
./start.sh

# Odłącz: Ctrl+A, D
# Wróć: screen -r mordzix
# Kill: screen -X -S mordzix quit
```

**Option B: Tmux**
```bash
tmux new -s mordzix
cd ~/mordzix
./start.sh

# Odłącz: Ctrl+B, D
# Wróć: tmux attach -t mordzix
# Kill: tmux kill-session -t mordzix
```

---

### 8️⃣ Otwórz Port 8080 w Firewall

**UFW (Ubuntu Firewall):**
```bash
sudo ufw allow 8080/tcp
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw allow ssh
sudo ufw enable
sudo ufw status
```

**OVH Panel:**
- Idź do: VPS → Network → Firewall
- Dodaj regułę: TCP 8080, source: 0.0.0.0/0

---

### 9️⃣ Systemd Service (Auto-restart)

```bash
sudo nano /etc/systemd/system/mordzix.service
```

**Wklej:**
```ini
[Unit]
Description=Mordzix AI Assistant
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/mordzix
Environment="PATH=/usr/bin:/usr/local/bin"
ExecStart=/usr/bin/python3 -m uvicorn app:app --host 0.0.0.0 --port 8080 --log-level info
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
```

**Enable & Start:**
```bash
sudo systemctl daemon-reload
sudo systemctl enable mordzix
sudo systemctl start mordzix
sudo systemctl status mordzix

# Logi:
sudo journalctl -u mordzix -f

# Restart:
sudo systemctl restart mordzix
```

---

## 🌐 Nginx + Domain (opcjonalnie)

### Zainstaluj Nginx

```bash
sudo apt install -y nginx
```

### Konfiguracja

```bash
sudo nano /etc/nginx/sites-available/mordzix
```

**Wklej:**
```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://127.0.0.1:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        
        # SSE for streaming
        proxy_buffering off;
        proxy_cache off;
        proxy_set_header Connection '';
        proxy_http_version 1.1;
        chunked_transfer_encoding off;
    }
}
```

**Enable:**
```bash
sudo ln -s /etc/nginx/sites-available/mordzix /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

### SSL (Let's Encrypt)

```bash
sudo apt install -y certbot python3-certbot-nginx
sudo certbot --nginx -d your-domain.com
```

---

## 🐳 Docker (alternatywa)

```bash
cd ~/mordzix

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER
newgrp docker

# Build & run
docker-compose up -d

# Logs
docker-compose logs -f

# Stop
docker-compose down
```

---

## 🧪 Testowanie

```bash
# Health check
curl http://localhost:8080/health

# Test API
curl -X POST http://localhost:8080/api/chat/assistant \
  -H "Content-Type: application/json" \
  -d '{"message": "Cześć!", "conversation_id": "test"}'

# Test frontend
curl http://localhost:8080/ | head -20
```

---

## 📊 Monitoring

### Logi aplikacji
```bash
tail -f ~/mordzix/logs/mordzix.log
```

### System resources
```bash
htop
df -h
free -h
```

### Port check
```bash
sudo lsof -i :8080
ss -tlnp | grep 8080
```

---

## 🔄 Update Aplikacji

```bash
cd ~/mordzix
git pull origin main  # jeśli git
sudo systemctl restart mordzix
```

---

## 🆘 Troubleshooting

### Port zajęty
```bash
sudo lsof -i :8080
sudo kill -9 <PID>
```

### Brak permisji
```bash
chmod +x start.sh
sudo chown -R $USER:$USER ~/mordzix
```

### Python packages
```bash
pip3 install -r requirements.txt --user
```

### Baza danych locked
```bash
rm mem.db
# Utworzy się nowa pusta
```

### Out of memory
```bash
# Dodaj SWAP
sudo fallocate -l 2G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
```

---

## ✅ Checklist Deployment OVH

- [ ] VPS kupiony i skonfigurowany
- [ ] SSH działa
- [ ] Python 3.10+ zainstalowany
- [ ] Aplikacja uploadowana
- [ ] .env wypełniony (API keys)
- [ ] Port 8080 otwarty w firewall
- [ ] Aplikacja uruchomiona (screen/systemd)
- [ ] Health check działa (`/health`)
- [ ] Frontend dostępny w przeglądarce
- [ ] (Opcjonalnie) Nginx skonfigurowany
- [ ] (Opcjonalnie) SSL certyfikat (Let's Encrypt)
- [ ] (Opcjonalnie) Domain podpięty

---

## 💰 Koszty

**VPS OVH:**
- Starter: ~20 PLN/miesiąc (2 vCores, 4GB RAM)
- Essential: ~40 PLN/miesiąc (2 vCores, 8GB RAM)
- Comfort: ~80 PLN/miesiąc (4 vCores, 16GB RAM)

**API Keys:**
- DeepInfra: Free tier (~$5 po wykorzystaniu)
- SERPAPI: $50/miesiąc (5000 searches)
- Firecrawl: $29/miesiąc
- OpenTripMap: Free

**Domain (opcjonalnie):**
- ~30-50 PLN/rok (.com, .pl)

---

## 🔗 Przydatne Linki

- OVH Panel: https://www.ovh.pl/manager/
- DeepInfra: https://deepinfra.com
- Let's Encrypt: https://letsencrypt.org
- GitHub Repo: https://github.com/ahui69/aktywmrd

---

**🔥 Gotowe! Aplikacja działa na OVH!**
