# Admin Dashboard Quick Start Guide

## 🚀 Getting Started

### Prerequisites
- Node.js 16+ (for frontend)
- Python 3.8+ (for backend)
- Access to backend API (`http://localhost:8000/api/v1`)
- Admin role (SUPER_ADMIN or HOSPITAL_ADMIN)

---

## 📋 Installation & Setup

### 1. Backend Setup

#### Install Dependencies
```bash
cd backend
pip install -r requirements.txt
```

#### Environment Configuration
Create `.env` file in backend root:
```env
DATABASE_URL=postgresql://user:pass@localhost/trustmedai
JWT_SECRET_KEY=your-long-random-secret-key
SUPER_ADMIN_EMAIL=admin@trustmedai.local
SUPER_ADMIN_PASSWORD=ChangeMe123!
ENVIRONMENT=local
```

#### Run Backend
```bash
cd backend
uvicorn app.main:app --reload --port 8000
```

### 2. Frontend Setup

#### Install Dependencies
```bash
cd frontend
npm install
```

#### Environment Configuration
Create `.env` file in frontend root:
```env
REACT_APP_API_URL=http://localhost:8000/api/v1
REACT_APP_WS_URL=ws://localhost:8000/ws
```

#### Run Frontend
```bash
cd frontend
npm run dev
```

---

## 🔐 Accessing Admin Dashboard

### Login
1. Navigate to `http://localhost:3000` (or your frontend URL)
2. Click "Admin Login"
3. Enter credentials:
   - **Email**: `admin@trustmedai.local`
   - **Password**: `ChangeMe123!` (or your configured password)
4. Confirm authentication

### Dashboard URL
```
http://localhost:3000/admin/dashboard
```

---

## 📊 Dashboard Features Overview

### 1. **Dashboard** (`/admin/dashboard`)
- View platform statistics
- Monitor active users
- Check diagnosis counts
- Review trust scores

**Key Metrics:**
- Total Users
- Active Users
- Total Diagnoses
- Average Trust Score
- Hospital Status

### 2. **User Management** (`/admin/users`)
- Search users by email or name
- Filter by role
- Edit user information
- Block/unblock accounts
- Reset passwords
- Delete users

**Quick Actions:**
```
Search → Filter by Role → Select User → Edit/Block/Delete
```

### 3. **Analytics** (`/admin/analytics`)
- View daily activity charts
- Track user growth trends
- Analyze diagnosis patterns
- Monthly statistics

**Charts Available:**
- Daily New Users (30 days)
- Daily New Diagnoses (30 days)
- Monthly User Growth (12 months)

### 4. **Records** (`/admin/records`)
- View all diagnosis records
- Search by patient name
- Filter by disease
- Export records (CSV/JSON)
- Delete records

**Common Tasks:**
```
Filter by Disease → Search Patient → Export/Delete
```

### 5. **Audit Logs** (`/admin/audit-logs`)
- Track all system activities
- Filter by actor (user)
- Filter by action type
- Export audit logs

**Available Actions:**
- User Created/Updated/Deleted
- Record Created/Deleted
- Hospital Verified
- Settings Changed

### 6. **Hospitals** (`/admin/hospitals`)
- View all hospitals
- Check verification status
- Monitor reputation scores
- Verify hospital credentials

**Verification Process:**
```
Select Unverified Hospital → Review Details → Click "Verify Hospital"
```

### 7. **Settings** (`/admin/settings`)
- View system configuration
- Check blockchain status
- Monitor MFA adoption
- Send announcements

**Configuration Items:**
- Project Name
- Environment
- JWT Settings
- Blockchain Status
- MFA Status

---

## 🔄 Common Workflows

### Onboard a New Doctor

```
1. Go to Users → Add User
2. Enter email and set role to "DOCTOR"
3. Set password
4. Assign to hospital (if required)
5. Verify email
6. Send welcome notification
```

### Manage Patient Records

```
1. Go to Records
2. Filter by disease type
3. Search patient name
4. Review diagnosis details
5. Download if needed
6. Delete if required (GDPR)
```

### Monitor System Health

```
1. Go to Dashboard
2. Check "Overview" section
3. Review daily statistics
4. Check hospital status
5. Monitor trust scores
```

### Audit User Activity

```
1. Go to Audit Logs
2. Search by actor/user ID
3. Filter by action type
4. Review timestamps
5. Export for compliance
```

### Verify Hospitals

```
1. Go to Hospitals
2. Filter "Pending Verification"
3. Review hospital details
4. Check reputation score
5. Click "Verify Hospital"
```

---

## 🛡️ Security Operations

### Change Admin Password
1. Go to Settings
2. Click "Security & MFA"
3. Update password in account settings
4. Force re-login for security

### Enable MFA
1. Go to Settings
2. Review "MFA Adoption Rate"
3. Encourage admins to enable MFA
4. Monitor adoption in MFA Status widget

### Review Audit Logs
```
Dashboard → Audit Logs → Search by Date Range → Export
```

### User Account Security
- Monitor failed login attempts
- Check last activity timestamps
- Deactivate inactive accounts
- Reset suspicious account passwords

---

## 📈 Analytics Dashboard Guide

### Metrics Explained

| Metric | Definition | Target |
|--------|-----------|--------|
| **Active Users** | Users who logged in within 30 days | > 80% |
| **Trust Score** | Average confidence in AI predictions | > 0.85 |
| **Verified Users** | Users with verified email | > 95% |
| **New Users** | New registrations in period | Trending up |
| **Diagnoses** | Total diagnosis records | Increases with usage |

### Using Charts

#### Daily Activity Chart
- **X-axis**: Date (last 30 days)
- **Y-axis**: Count (new users/diagnoses)
- **Use Case**: Identify usage patterns and anomalies

#### Monthly Growth Chart
- **X-axis**: Month
- **Y-axis**: New users count
- **Use Case**: Track platform growth trends

#### Role Distribution
- **Use Case**: Ensure proper role balance
- **Action**: Add more doctors if patient:doctor ratio is high

---

## 🐛 Troubleshooting

### Issue: "Permission Denied" Error

**Cause:** User lacks admin permissions

**Solution:**
```bash
# In backend, verify user role:
SELECT email, role FROM users WHERE email='your_email';

# Update role if needed:
UPDATE users SET role='SUPER_ADMIN' WHERE email='your_email';
```

### Issue: Analytics Not Loading

**Cause:** Database connectivity issue

**Solution:**
```bash
# Check database connection:
python -c "from app.db.session import engine; engine.execute('SELECT 1')"

# Verify data exists:
SELECT COUNT(*) FROM diagnosis_records WHERE created_at > NOW() - INTERVAL '30 days';
```

### Issue: Slow Dashboard Performance

**Cause:** Large dataset without pagination

**Solution:**
- Always use pagination (limit: 10-20 records)
- Use date filters to limit data range
- Ensure database indexes are created

### Issue: Records Export Failing

**Cause:** Insufficient permissions or corrupted data

**Solution:**
- Verify `platform:manage` permission
- Try exporting smaller date range
- Check database for data integrity

---

## 📱 API Endpoints Reference

### Dashboard Endpoints

| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET | `/admin/analytics/overview` | Get dashboard overview |
| GET | `/admin/analytics/daily-stats` | Get daily statistics |
| GET | `/admin/users` | List all users |
| GET | `/admin/data/records` | List diagnosis records |
| GET | `/admin/audit/logs` | Get audit logs |
| GET | `/admin/hospitals` | List hospitals |
| GET | `/admin/settings/system` | Get system settings |

### Common Query Parameters

```
?skip=0              # Pagination offset
&limit=10            # Records per page
&days=30             # Date range in days
&search=value        # Search query
&filter=type         # Filter by type
```

---

## 🔗 Related Documentation

- [Admin Dashboard Full Documentation](./ADMIN_DASHBOARD.md)
- [API Documentation](./API.md)
- [RBAC Implementation](./RBAC_DOCUMENTATION_INDEX.md)
- [Architecture Guide](./ARCHITECTURE.md)

---

## 💡 Tips & Best Practices

1. **Regular Audits**: Review audit logs weekly
2. **Backup Data**: Regularly backup diagnosis records
3. **Monitor Growth**: Track user and diagnosis trends
4. **Security Updates**: Keep MFA adoption high
5. **Hospital Verification**: Verify new hospitals promptly
6. **Password Policy**: Enforce strong password requirements
7. **Activity Monitoring**: Check user activity patterns

---

## 🆘 Getting Help

### Support Resources
- **API Docs**: `http://localhost:8000/docs`
- **Health Check**: `http://localhost:8000/health`
- **Logs**: Check `logs/admin.log`

### Reporting Issues
1. Check logs for error messages
2. Verify permissions and authentication
3. Test API endpoint directly with curl
4. Document issue with:
   - Error message
   - Steps to reproduce
   - Expected vs actual behavior
   - User role and permissions

---

## 📝 Changelog

### Version 1.0.0 (January 2024)
- Initial Admin Dashboard release
- Core features: Users, Analytics, Records, Audit Logs, Hospitals, Settings
- Comprehensive API endpoints
- Full RBAC implementation

---

## ⚠️ Important Notes

- **SUPER_ADMIN** can access all features
- **HOSPITAL_ADMIN** can only manage their hospital's users
- Audit logs are immutable for compliance
- User deletion is soft-delete (data preserved)
- All timestamps are in UTC
- Session timeout: 30 minutes (configurable)

---

**Last Updated**: January 2024  
**Status**: Production Ready  
**Support**: Contact development team for issues
