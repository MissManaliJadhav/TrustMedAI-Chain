# 🚀 MedAI Chatbot - Quick Deployment Guide

## System Requirements

- **Python**: 3.11+
- **Node.js**: 18+
- **PostgreSQL**: 13+
- **Docker**: Latest
- **Docker Compose**: Latest (optional, for orchestration)

---

## 🎯 Quick Start (5 minutes)

### 1️⃣ Start PostgreSQL

```bash
# Option A: Using Docker
docker run --name trustmedai-db \
  -e POSTGRES_USER=admin \
  -e POSTGRES_PASSWORD=admin123 \
  -e POSTGRES_DB=trustmedai \
  -p 5432:5432 \
  -d postgres:15

# Option B: Using local PostgreSQL
# Make sure PostgreSQL is running on port 5432
```

### 2️⃣ Start Backend

```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

✅ Backend ready at `http://localhost:8000`

### 3️⃣ Start Frontend

```bash
cd frontend

# Install dependencies
npm install

# Set environment variables
echo "VITE_API_URL=http://localhost:8000/api/v1" > .env.local

# Start development server
npm run dev
```

✅ Frontend ready at `http://localhost:3000`

### 4️⃣ Access the Application

1. Open `http://localhost:3000` in browser
2. Sign up for an account
3. Log in
4. Click **"MedAI Chat"** button in dashboard
5. Start a new chat session

---

## 🧪 Test the Chatbot

### Sample Conversation

```
User: "Hi, I'm John, 45 years old, male from USA"
Assistant: "Thank you for sharing that information. I've noted...
Now, what is your main health concern today?"

User: "I've been having chest pain for 3 days"
Assistant: "I understand you're experiencing chest pain...
When did this start? How severe is it on a scale of 1-10?"

User: "It's severe, 8/10, started after exercise"
Assistant: "Let me understand more...
Do you have any shortness of breath?"

User: "Yes, and I'm feeling dizzy"
Assistant: "[Complete Assessment]
**Risk Level:** HIGH
**Possible Conditions:**
1. Heart Disease (85% confidence)
2. Acute Coronary Syndrome (65% confidence)"
```

---

## 📚 Documentation

| Document | Purpose |
|----------|---------|
| **CHATBOT_DOCUMENTATION.md** | Complete technical reference |
| **CHATBOT_QUICKSTART.md** | Testing & implementation guide |
| **ARCHITECTURE.md** | System architecture & diagrams |
| **MEDAI_SUMMARY.md** | Project overview & summary |
| **IMPLEMENTATION_CHECKLIST.md** | Verification checklist |
| **FINAL_VERIFICATION.md** | Completion status |

---

## 🔧 API Endpoints

```bash
# Create chat session
curl -X POST http://localhost:8000/api/v1/chat/sessions \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"title": "New Chat"}'

# Send message
curl -X POST http://localhost:8000/api/v1/chat/messages \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"session_id": "...", "content": "Hello"}'

# Get assessment
curl -X GET http://localhost:8000/api/v1/chat/sessions/SESSION_ID/assessment \
  -H "Authorization: Bearer YOUR_TOKEN"

# Export assessment
curl -X POST http://localhost:8000/api/v1/chat/sessions/SESSION_ID/export \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"disease_key": "heart_disease"}'
```

---

## 🐳 Docker Deployment

### Using Docker Compose

```bash
# Build and start all services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

### Manual Docker Commands

```bash
# Build backend image
docker build -t trustmedai-backend:1.0 backend/
docker run -p 8000:8000 trustmedai-backend:1.0

# Build frontend image
docker build -t trustmedai-frontend:1.0 frontend/
docker run -p 3000:3000 trustmedai-frontend:1.0
```

---

## 🔍 Debugging

### Backend Issues

```bash
# Check if backend is running
curl http://localhost:8000/health

# View logs
tail -f backend.log

# Check database connection
psql -U admin -d trustmedai -h localhost
```

### Frontend Issues

```bash
# Clear cache
rm -rf node_modules package-lock.json
npm install

# Check browser console for errors
# Press F12 in browser

# Clear browser cache
Ctrl+Shift+Delete (Windows/Linux)
Cmd+Shift+Delete (Mac)
```

### Database Issues

```bash
# Check PostgreSQL status
psql -U admin -d trustmedai -h localhost -c "SELECT 1"

# View tables
psql -U admin -d trustmedai -h localhost -c "\dt"

# View chat sessions
psql -U admin -d trustmedai -h localhost -c "SELECT * FROM chat_sessions LIMIT 5"
```

---

## 📊 Monitoring

### Key Metrics

```bash
# Backend response time
time curl http://localhost:8000/api/v1/chat/sessions

# Frontend bundle size
ls -lh frontend/dist/

# Database size
psql -U admin -d trustmedai -c "SELECT pg_size_pretty(pg_database_size('trustmedai'))"

# API calls per minute
grep -c "POST /api/v1/chat" backend.log
```

---

## 🚀 Production Deployment

### Pre-deployment Checklist

- [ ] Environment variables configured
- [ ] Database backup created
- [ ] SSL certificates ready
- [ ] CORS whitelist updated
- [ ] API rate limiting configured
- [ ] Monitoring setup
- [ ] Logging configured
- [ ] Backup strategy defined

### Deployment Steps

```bash
# 1. Build production images
docker build -t trustmedai-backend:prod backend/
docker build -t trustmedai-frontend:prod frontend/

# 2. Push to registry (optional)
docker push registry.example.com/trustmedai-backend:prod
docker push registry.example.com/trustmedai-frontend:prod

# 3. Deploy with Kubernetes
kubectl apply -f k8s/

# 4. Verify deployment
kubectl get pods -n trustmedai
kubectl logs -f -n trustmedai deployment/backend
```

---

## 🔐 Security Configuration

### Environment Variables

Create `.env.local` in frontend:
```
VITE_API_URL=https://api.yourdomain.com/api/v1
VITE_API_BASE_URL=https://api.yourdomain.com
```

Create `.env` in backend:
```
DATABASE_URL=postgresql://user:pass@localhost/trustmedai
SECRET_KEY=your-secret-key-here
JWT_ALGORITHM=HS256
CORS_ORIGINS=["https://yourdomain.com"]
```

### HTTPS Setup

```bash
# Generate SSL certificate
openssl req -x509 -newkey rsa:4096 -keyout key.pem -out cert.pem -days 365

# Use with Uvicorn
uvicorn app.main:app --ssl-keyfile=key.pem --ssl-certfile=cert.pem
```

---

## 📈 Scaling

### Horizontal Scaling

```bash
# Scale backend replicas
kubectl scale deployment backend --replicas=3

# Scale frontend replicas
kubectl scale deployment frontend --replicas=3

# Use load balancer
kubectl apply -f k8s/ingress.yaml
```

### Database Optimization

```sql
-- Create indexes
CREATE INDEX idx_chat_sessions_user_id ON chat_sessions(user_id);
CREATE INDEX idx_chat_messages_session_id ON chat_messages(session_id);
CREATE INDEX idx_chat_sessions_created_at ON chat_sessions(created_at);

-- Archive old sessions
DELETE FROM chat_messages WHERE session_id IN (
  SELECT id FROM chat_sessions WHERE created_at < NOW() - INTERVAL '90 days'
);
DELETE FROM chat_sessions WHERE created_at < NOW() - INTERVAL '90 days';
```

---

## 🔄 Backup & Recovery

### Backup Strategy

```bash
# Daily database backup
pg_dump -U admin trustmedai > backup-$(date +%Y%m%d).sql

# Backup to S3
aws s3 cp backup-$(date +%Y%m%d).sql s3://your-bucket/

# Backup frontend files
tar -czf frontend-backup-$(date +%Y%m%d).tar.gz frontend/
```

### Recovery

```bash
# Restore database
psql -U admin trustmedai < backup-20240115.sql

# Restore frontend
tar -xzf frontend-backup-20240115.tar.gz
```

---

## 📞 Support

### Common Issues

**Q: Port already in use**
```bash
# Kill process on port 8000
lsof -ti:8000 | xargs kill -9

# Use different port
uvicorn app.main:app --port 8001
```

**Q: Database connection refused**
```bash
# Check PostgreSQL is running
pg_isready

# Verify credentials
psql -U admin -h localhost
```

**Q: Frontend not connecting to API**
```bash
# Check .env.local file
cat frontend/.env.local

# Check CORS headers
curl -H "Origin: http://localhost:3000" http://localhost:8000/health -v
```

**Q: Chat messages not saving**
```bash
# Check database tables exist
psql -U admin -d trustmedai -c "\dt chat_*"

# Check database logs
psql -U admin -d trustmedai -c "SELECT * FROM chat_sessions LIMIT 1"
```

---

## 📚 Additional Resources

- **Swagger API Docs**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **GitHub Issues**: Check project issues
- **Documentation**: See `CHATBOT_DOCUMENTATION.md`

---

## ✅ Health Check

```bash
# Quick health check
echo "Checking backend..."
curl -s http://localhost:8000/health | jq .

echo "Checking database..."
psql -U admin -d trustmedai -c "SELECT 1" && echo "✓ Database OK"

echo "Checking frontend..."
curl -s http://localhost:3000 | head -1 && echo "✓ Frontend OK"
```

---

## 🎯 Next Steps

1. ✅ Deploy to staging
2. ✅ Run QA tests
3. ✅ Get user feedback
4. ✅ Deploy to production
5. ✅ Monitor performance
6. ✅ Plan enhancements

---

## 📞 Contact

For issues or questions:
1. Check the documentation files
2. Review error logs
3. Check database integrity
4. Contact development team

---

**Version**: 1.0.0  
**Last Updated**: January 15, 2024  
**Status**: Ready for Production

