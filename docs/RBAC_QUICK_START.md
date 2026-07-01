# Quick RBAC Deployment Guide

## 5-Minute Setup

### Step 1: Backend Deployment

```bash
# Navigate to backend directory
cd backend

# Install dependencies (if needed)
pip install -r requirements.txt

# Run migrations (if any new schema changes)
# Database is PostgreSQL - ensure it's running

# Start backend
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**Expected Output**:
```
INFO:     Uvicorn running on http://0.0.0.0:8000
INFO:     Application startup complete
```

**Verify API is running**:
```bash
curl http://localhost:8000/docs
# Should open Swagger UI showing all endpoints including:
# - POST /api/v1/predictions (create diagnosis)
# - GET /api/v1/predictions (list with role filtering)
# - GET /api/v1/trust/history
# - GET /api/v1/blockchain/nodes
```

---

### Step 2: Database Setup

```bash
# Connect to PostgreSQL
psql -U your_db_user -d trust_medai

# Verify users table has role column
\d users;

# Check sample user exists
SELECT id, email, role FROM users LIMIT 5;

# Create test users if needed:
INSERT INTO users (id, email, full_name, role, password_hash, is_active, is_verified)
VALUES 
  ('admin-id', 'admin@trustmedai.local', 'System Admin', 'SUPER_ADMIN', 'hash', true, true),
  ('doctor-id', 'doctor@hospital.local', 'Dr. Jane Smith', 'DOCTOR', 'hash', true, true),
  ('patient-id', 'patient@example.local', 'John Doe', 'PATIENT', 'hash', true, true);
```

---

### Step 3: Frontend Deployment

```bash
# Navigate to frontend directory
cd frontend

# Install dependencies
npm install

# Set API base URL (create .env.local if needed)
echo "VITE_API_BASE_URL=http://localhost:8000/api/v1" > .env.local

# Start development server
npm run dev
```

**Expected Output**:
```
  VITE v6.0.7 running at:
  ➜  Local:   http://localhost:5173/
  ➜  press h to show help
```

---

### Step 4: Test RBAC Flow

#### Test 1: Patient Login & View Records

```
1. Open http://localhost:5173
2. Click "Login"
3. Use credentials:
   - Email: patient@example.local
   - Password: ChangeMe123! (or your patient password)
4. Click "Role Dashboard" button
5. Should see PatientDashboardPage
6. Verify: Only own records shown, not all records
```

#### Test 2: Doctor Login & Create Diagnosis

```
1. Logout and navigate to http://localhost:5173/login
2. Use credentials:
   - Email: doctor@hospital.local
   - Password: ChangeMe123! (or your doctor password)
3. Click "Role Dashboard" button
4. Should see DoctorDashboardPage with "New Diagnosis" form
5. Fill form:
   - Patient ID: <copy a patient's ID>
   - Disease: Heart Disease
   - Age: 58
   - Clinical score: 72
   - Biomarker: 64
6. Click "Submit Diagnosis"
7. Verify: Diagnosis created successfully with blockchain hash
```

#### Test 3: Admin View All Records

```
1. Logout and login with admin credentials
2. Click "Role Dashboard" button
3. Should see AdminDashboardPage
4. Verify: Can see all diagnosis records
5. Verify: Can see blockchain network nodes
6. Verify: Can see all trust history
```

#### Test 4: Unauthorized Access Test

```
1. As patient, try to access /role-dashboard while logged out
2. Should redirect to /login (✓ working)
3. Login as patient
4. Check browser console for role: localStorage.getItem('trustmedai_role')
5. Should show: "PATIENT" (✓ working)
```

---

## API Endpoints Quick Reference

### Authentication
```
POST /api/v1/auth/login
  Input: {email, password}
  Output: {access_token, refresh_token, role, user_id}

POST /api/v1/auth/refresh
  Input: {refresh_token}
  Output: {access_token, refresh_token, role, user_id}

POST /api/v1/auth/signup
  Input: {email, password, full_name, role}
  Output: {id, email, full_name, role, is_verified}
```

### Predictions (Role-Filtered)
```
GET /api/v1/predictions
  Headers: Authorization: Bearer {token}
  Response: [{diagnosis_id, disease_key, patient_id, doctor_id, ...}]
  
  Filtering by role:
  - PATIENT: Only own records (patient_id == user.id)
  - DOCTOR: Only own diagnoses (doctor_id == user.id)
  - ADMIN: All records

POST /api/v1/predictions
  Headers: Authorization: Bearer {doctor_token}
  Input: {disease_key, patient_id, features, doctor_notes}
  Output: {diagnosis_id, prediction, confidence, trust_score, blockchain_hash}
```

### Trust History
```
GET /api/v1/trust/history?disease_key=heart
  Headers: Authorization: Bearer {token}
  Response: [{disease_key, dtei, fidelity, robustness, blockchain_integrity}]
```

### Blockchain
```
GET /api/v1/blockchain/nodes
  Headers: Authorization: Bearer {admin_token}
  Response: {ethereum: [...], fabric: [...]}

GET /api/v1/blockchain/explorer
  Headers: Authorization: Bearer {admin_token}
  Response: {anchored_records, trust_anchors, verification_status}
```

---

## Environment Configuration

### Backend `.env` File
```env
# Database
DATABASE_URL=postgresql://user:password@localhost:5432/trust_medai

# JWT
JWT_SECRET_KEY=your-super-secret-key-change-this
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# Blockchain - Ethereum
ETHEREUM_RPC_URL=http://localhost:8545
ETHEREUM_CONTRACT_ADDRESS=0x...
ETHEREUM_SENDER_ADDRESS=0x...
ETHEREUM_PRIVATE_KEY=0x...  # Optional

# Blockchain - Hyperledger Fabric
FABRIC_NETWORK_PROFILE=./fabric-config.json
FABRIC_USER=admin
FABRIC_CHANNEL=trustchannel
FABRIC_CHAINCODE=trustledger

# API
VITE_API_BASE_URL=http://localhost:8000/api/v1
```

### Frontend `.env.local`
```env
VITE_API_BASE_URL=http://localhost:8000/api/v1
VITE_JWT_STORAGE_KEY=trustmedai_access
```

---

## Docker Deployment (Optional)

```bash
# Build and run with docker-compose
docker-compose up -d

# Verify containers running
docker-compose ps

# Check backend logs
docker-compose logs backend

# Check frontend logs
docker-compose logs frontend
```

**Containers**:
- `backend`: FastAPI server on port 8000
- `frontend`: React dev server on port 5173
- `postgres`: PostgreSQL on port 5432
- `redis`: Cache on port 6379 (if using)

---

## Monitoring & Debugging

### Check User Roles in Database
```bash
psql -U your_db_user -d trust_medai -c "SELECT id, email, role FROM users;"
```

### View Backend Logs
```bash
# Real-time logs
tail -f backend/app.log

# Filter by role errors
grep -i "permission\|forbidden" backend/app.log
```

### Browser DevTools Checks

**Console**:
```javascript
// Check stored role
localStorage.getItem('trustmedai_role')  // Should output: "PATIENT"|"DOCTOR"|"SUPER_ADMIN"

// Check token
localStorage.getItem('trustmedai_access')  // Should output: JWT token

// Check Redux state
// Open Redux DevTools extension to inspect state
```

**Network Tab**:
```
Check outgoing requests include:
- Authorization: Bearer {token} header
- /predictions returns filtered results based on role
```

---

## Common Issues & Fixes

### Issue: "Invalid credentials" on login
**Fix**: 
```bash
# Verify user exists in database
psql -U your_db_user -d trust_medai -c \
  "SELECT * FROM users WHERE email='patient@example.local';"

# If missing, create test users:
INSERT INTO users (...) VALUES (...);
```

### Issue: GET /predictions returns 403 Forbidden
**Fix**: Check that user token includes valid role
```bash
# Decode JWT token at jwt.io and verify "role" claim is present
```

### Issue: RoleBasedDashboard shows blank page
**Fix**: Check browser console for React errors
```javascript
// In browser console
console.log(useAppSelector(state => state.auth.role))  // Should show role
```

### Issue: Blockchain transactions failing
**Fix**: Verify Ethereum/Fabric connection
```bash
# Check blockchain service logs
grep -i "ethereum\|fabric\|blockchain" backend/app.log

# Verify RPC endpoints configured
curl http://localhost:8545  # Ethereum
```

---

## Verification Checklist

### Backend
- [ ] FastAPI running on http://localhost:8000
- [ ] Database connected with users and diagnosis_records tables
- [ ] Swagger UI accessible at http://localhost:8000/docs
- [ ] GET /predictions returns role-filtered results
- [ ] POST /predictions creates records with doctor_id
- [ ] JWT tokens include role claim

### Frontend
- [ ] React running on http://localhost:5173
- [ ] Login page functional
- [ ] Token stored in localStorage after login
- [ ] RoleBasedDashboard component renders correctly
- [ ] Patient dashboard shows only own records
- [ ] Doctor dashboard shows only own diagnoses
- [ ] Admin dashboard shows all records
- [ ] Role navigation working (redirects based on role)

### Database
- [ ] All users have valid role values
- [ ] diagnosis_records have doctor_id and patient_id
- [ ] Hospital_id set for multi-hospital scenarios
- [ ] Foreign key constraints in place

### Blockchain
- [ ] Ethereum transactions being anchored
- [ ] Fabric transactions being recorded
- [ ] Hashes verified in database
- [ ] Transaction receipts stored

---

## Support Contacts

- **Backend Issues**: Check backend logs, review `RBAC_INTEGRATION_REPORT.md`
- **Frontend Issues**: Check browser console, verify localStorage
- **Database Issues**: Run SQL verification queries above
- **Blockchain Issues**: Check RPC endpoint connectivity

**Report Generated**: 2024
**Version**: 1.0.0-rbac
