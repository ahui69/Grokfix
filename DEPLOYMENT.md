# 🚀 Deployment Guide - Mordzix AI

## 📋 Przygotowanie do Produkcji

### 1️⃣ Wymagania Serwera

**Minimalne:**
- CPU: 2 cores
- RAM: 4GB
- Disk: 20GB SSD
- OS: Ubuntu 20.04+ / Debian 11+
- Python: 3.10+
- Docker: 20.10+ (optional)

**Zalecane:**
- CPU: 4+ cores
- RAM: 8GB+
- Disk: 50GB+ SSD
- OS: Ubuntu 22.04 LTS

---

## 🔧 Deployment Methods

### Method 1: Docker (Zalecane)

```bash
# 1. Clone repo
git clone https://github.com/ahui69/aktywmrd.git
cd aktywmrd/mrd

# 2. Configure .env
cp .env.example .env
nano .env  # Fill in your API keys

# 3. Build & run
docker-compose up -d

# 4. Check logs
docker-compose logs -f

# 5. Test
curl http://localhost:8080/health
```

**Auto-restart:**
```yaml
# docker-compose.yml already has:
restart: unless-stopped
```

---

### Method 2: Systemd Service (Linux)

```bash
# 1. Clone repo
git clone https://github.com/ahui69/aktywmrd.git
cd aktywmrd/mrd

# 2. Install dependencies
pip install -r requirements.txt

# 3. Configure .env
cp .env.example .env
nano .env

# 4. Create systemd service
sudo nano /etc/systemd/system/mordzix.service
```

**mordzix.service:**
```ini
[Unit]
Description=Mordzix AI Assistant
After=network.target

[Service]
Type=simple
User=www-data
WorkingDirectory=/opt/mordzix
Environment="PATH=/opt/mordzix/venv/bin"
ExecStart=/opt/mordzix/venv/bin/python -m uvicorn app:app --host 0.0.0.0 --port 8080
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
```

```bash
# 5. Enable & start
sudo systemctl daemon-reload
sudo systemctl enable mordzix
sudo systemctl start mordzix

# 6. Check status
sudo systemctl status mordzix

# 7. View logs
sudo journalctl -u mordzix -f
```

---

### Method 3: PM2 (Node.js Process Manager)

```bash
# 1. Install PM2
npm install -g pm2

# 2. Start app
pm2 start ./start.sh --name mordzix

# 3. Save config
pm2 save
pm2 startup

# 4. Monitor
pm2 status
pm2 logs mordzix
pm2 monit
```

---

## 🌐 Reverse Proxy (Nginx)

### Nginx Configuration

```bash
sudo nano /etc/nginx/sites-available/mordzix
```

```nginx
server {
    listen 80;
    server_name yourdomain.com;

    # Redirect HTTP to HTTPS
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name yourdomain.com;

    # SSL Certificate (Let's Encrypt)
    ssl_certificate /etc/letsencrypt/live/yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/yourdomain.com/privkey.pem;

    # SSL Configuration
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;

    # Timeouts for streaming
    proxy_connect_timeout 600s;
    proxy_send_timeout 600s;
    proxy_read_timeout 600s;

    # Proxy to FastAPI
    location / {
        proxy_pass http://127.0.0.1:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # SSE (Server-Sent Events) for streaming
        proxy_buffering off;
        proxy_cache off;
        proxy_set_header Connection '';
        proxy_http_version 1.1;
        chunked_transfer_encoding off;
    }

    # Static files (if needed)
    location /static/ {
        alias /opt/mordzix/static/;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }

    # Security headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;

    # Logging
    access_log /var/log/nginx/mordzix_access.log;
    error_log /var/log/nginx/mordzix_error.log;
}
```

```bash
# Enable site
sudo ln -s /etc/nginx/sites-available/mordzix /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

### SSL Certificate (Let's Encrypt)

```bash
# Install certbot
sudo apt install certbot python3-certbot-nginx

# Get certificate
sudo certbot --nginx -d yourdomain.com

# Auto-renewal (already configured)
sudo certbot renew --dry-run
```

---

## 🔒 Security Checklist

### 1. Environment Variables
```bash
# NEVER commit .env to git!
echo ".env" >> .gitignore

# Use strong tokens
openssl rand -hex 32  # Generate random token
```

### 2. Firewall (UFW)
```bash
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow ssh
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw enable
```

### 3. Rate Limiting
```bash
# Already configured in config.py
RATE_LIMIT_PER_MINUTE=160
```

### 4. Database Permissions
```bash
chmod 600 mem.db
chown www-data:www-data mem.db
```

---

## 📊 Monitoring

### Health Check Endpoint
```bash
curl http://localhost:8080/health
```

**Expected response:**
```json
{
  "status": "healthy",
  "version": "3.3.0",
  "timestamp": "2025-10-11T12:00:00Z"
}
```

### Uptime Monitoring (Uptime Robot)
1. Go to [uptimerobot.com](https://uptimerobot.com)
2. Add new monitor:
   - Type: HTTP(s)
   - URL: https://yourdomain.com/health
   - Interval: 5 minutes

### Log Monitoring
```bash
# Real-time logs
tail -f logs/mordzix.log

# Error logs only
tail -f logs/mordzix.log | grep ERROR

# With systemd
sudo journalctl -u mordzix -f
```

---

## 🔄 Backup Strategy

### Database Backup
```bash
#!/bin/bash
# backup.sh
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/backups/mordzix"
mkdir -p $BACKUP_DIR

# Backup database
cp mem.db $BACKUP_DIR/mem_$DATE.db

# Backup uploads
tar -czf $BACKUP_DIR/uploads_$DATE.tar.gz uploads/

# Keep only last 7 days
find $BACKUP_DIR -name "mem_*.db" -mtime +7 -delete
find $BACKUP_DIR -name "uploads_*.tar.gz" -mtime +7 -delete
```

```bash
# Add to crontab
crontab -e
# Daily at 2 AM
0 2 * * * /opt/mordzix/backup.sh
```

---

## 🚀 CI/CD (GitHub Actions)

Create `.github/workflows/deploy.yml`:

```yaml
name: Deploy to Production

on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Deploy to server
        uses: appleboy/ssh-action@master
        with:
          host: ${{ secrets.SERVER_HOST }}
          username: ${{ secrets.SERVER_USER }}
          key: ${{ secrets.SSH_PRIVATE_KEY }}
          script: |
            cd /opt/mordzix
            git pull origin main
            docker-compose down
            docker-compose build
            docker-compose up -d
```

---

## 📈 Scaling

### Horizontal Scaling (Multiple Instances)

**docker-compose.yml:**
```yaml
version: '3.8'

services:
  mordzix:
    build: .
    deploy:
      replicas: 3  # 3 instances
    environment:
      - PORT=8080
    volumes:
      - ./mrd:/app
    networks:
      - mordzix-net

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
    depends_on:
      - mordzix
    networks:
      - mordzix-net

networks:
  mordzix-net:
```

---

## 🆘 Troubleshooting

### App won't start
```bash
# Check logs
docker-compose logs -f
# or
sudo journalctl -u mordzix -n 50

# Check port
sudo lsof -i :8080

# Check Python
python3 --version
python3 -c "import fastapi; print('OK')"
```

### Out of memory
```bash
# Check memory
free -h

# Restart app
sudo systemctl restart mordzix
# or
docker-compose restart
```

### Database locked
```bash
# Check processes
lsof mem.db

# Kill if needed
kill -9 <PID>
```

---

## ✅ Production Checklist

- [ ] `.env` configured with real API keys
- [ ] `AUTH_TOKEN` changed from default
- [ ] Database directory writable
- [ ] Firewall configured (UFW)
- [ ] SSL certificate installed (Let's Encrypt)
- [ ] Nginx reverse proxy configured
- [ ] Systemd service enabled (auto-start)
- [ ] Backup script configured (cron)
- [ ] Monitoring setup (Uptime Robot)
- [ ] Logs rotation configured
- [ ] Domain DNS configured
- [ ] Health check endpoint tested
- [ ] Rate limiting tested
- [ ] Load testing performed

---

**🔥 Ready for production!**
