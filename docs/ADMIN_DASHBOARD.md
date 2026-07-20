# Admin Dashboard Documentation

## Overview

The Admin Dashboard is a comprehensive centralized control panel for administrators to manage the TrustMedAI platform. It provides monitoring, management, and control capabilities for users, data, and system operations.

## Table of Contents

1. [Features](#features)
2. [Architecture](#architecture)
3. [User Management](#user-management)
4. [Analytics & Monitoring](#analytics--monitoring)
5. [Data Management](#data-management)
6. [Security & Audit](#security--audit)
7. [System Settings](#system-settings)
8. [API Reference](#api-reference)
9. [Troubleshooting](#troubleshooting)

---

## Features

### 1. Dashboard Overview
- **Real-time Statistics**: View total users, active users, diagnoses, and trust scores
- **Role Distribution**: See breakdown of users by role (Super Admin, Hospital Admin, Doctor, Patient, Researcher)
- **Hospital Status**: Monitor verified and unverified hospitals
- **Quick Metrics**: Access to key performance indicators

### 2. User Management
- **View All Users**: List all users with filtering and search
- **User Details**: View comprehensive user information including activity history
- **Edit Users**: Update user information (name, role, verification status)
- **Block/Unblock**: Disable or enable user accounts
- **Reset Passwords**: Securely reset user passwords
- **Delete Users**: Soft-delete users (deactivate)
- **Role Assignment**: Assign roles to users (SUPER_ADMIN, HOSPITAL_ADMIN, DOCTOR, PATIENT, RESEARCHER)

### 3. Analytics & Charts
- **Daily Activity**: View new users and diagnoses over 30 days
- **User Growth**: Track monthly user growth trends
- **Disease Metrics**: Analyze diagnoses by disease type
- **Trust Score Analytics**: Monitor average trust scores
- **Custom Date Ranges**: Filter data by date range (1-365 days)

### 4. Records Management
- **View Records**: Browse all diagnosis records with pagination
- **Search & Filter**: Find records by patient name, email, or disease
- **Export Data**: Download records in CSV or JSON format
- **Delete Records**: Remove individual records (GDPR compliance)
- **Record Details**: View confidence, trust score, and blockchain hash

### 5. Audit Logging
- **Activity Tracking**: Complete audit trail of all platform activities
- **User Actions**: Track who did what, when, and on which resource
- **Filtering**: Filter logs by actor, action, resource type
- **Export Audit Logs**: Download audit logs for compliance
- **Date Range Filtering**: View logs from specific time periods

### 6. Security Management
- **MFA Adoption**: Monitor two-factor authentication usage
- **Login History**: Track user login activities
- **Blockchain Status**: View Ethereum and Fabric blockchain integration status
- **API Security**: Configure JWT and token settings
- **Permission Management**: Role-based access control (RBAC)

### 7. System Settings
- **Configuration Management**: View system settings (read-only from UI)
- **Blockchain Configuration**: Check Ethereum and Hyperledger Fabric status
- **MFA Status**: Monitor MFA adoption rate among users
- **System Announcements**: Send broadcast messages to all users
- **API Documentation**: Access to Swagger/OpenAPI docs

### 8. Hospital Management
- **Hospital Registry**: View all registered hospitals
- **Verification**: Verify hospital credentials and status
- **Reputation Scoring**: Monitor hospital reputation scores
- **User Count**: See number of users per hospital
- **Region Tracking**: Filter hospitals by region

---

## Architecture

### Backend Structure

```
backend/app/api/v1/
├── admin.py                 # Admin API endpoints
├── router.py               # API router configuration
└── ...

backend/app/
├── db/models.py            # Database models
├── core/rbac.py            # Role-based access control
├── core/config.py          # Configuration management
├── schemas_admin.py        # Pydantic schemas
└── ...
```

### Frontend Structure

```
frontend/src/pages/
├── AdminLayout.tsx         # Main admin layout with sidebar
├── AdminDashboard.tsx      # Dashboard overview
├── AdminUsers.tsx          # User management
├── AdminAnalytics.tsx      # Analytics and charts
├── AdminRecords.tsx        # Records management
├── AdminAuditLogs.tsx      # Audit logs viewer
├── AdminSettings.tsx       # System settings
└── AdminHospitals.tsx      # Hospital management
```

### Database Models

#### User Model
```python
class User(Base):
    id: str                  # UUID
    email: str              # Unique email
    full_name: str
    role: str               # SUPER_ADMIN, HOSPITAL_ADMIN, DOCTOR, PATIENT, RESEARCHER
    password_hash: str
    is_active: bool
    is_verified: bool
    hospital_id: str        # Foreign key to Hospital
    created_at: datetime
```

#### AuditEvent Model
```python
class AuditEvent(Base):
    id: int
    actor_id: str           # User who performed action
    action: str             # Description of action
    resource_type: str      # Type of resource affected
    resource_id: str        # ID of resource affected
    payload_hash: str       # Hash of action payload
    metadata_json: dict
    created_at: datetime
```

---

## User Management

### Access Control

Users can manage other users only if they have the `users:manage` permission. The following roles can access user management:

- **SUPER_ADMIN**: Full access to all users
- **HOSPITAL_ADMIN**: Can manage users in their hospital

### User Operations

#### Get All Users
```bash
GET /api/v1/admin/users
?skip=0&limit=10&role=DOCTOR&is_active=true&search=john
```

**Parameters:**
- `skip`: Number of records to skip (pagination)
- `limit`: Number of records to return (1-100)
- `role`: Filter by role (optional)
- `is_active`: Filter by active status (optional)
- `search`: Search by email or name (optional)

**Response:**
```json
{
  "total": 150,
  "skip": 0,
  "limit": 10,
  "users": [
    {
      "id": "uuid",
      "email": "doctor@hospital.com",
      "full_name": "Dr. John Doe",
      "role": "DOCTOR",
      "is_verified": true
    }
  ]
}
```

#### Get User Details
```bash
GET /api/v1/admin/users/{user_id}
```

**Response:**
```json
{
  "user": { ... },
  "hospital": { "id": "uuid", "name": "Hospital Name" },
  "recent_diagnoses": 5,
  "total_activity_events": 42,
  "last_activity": "2024-01-15T10:30:00",
  "account_created": "2023-06-01T14:22:00"
}
```

#### Update User
```bash
PUT /api/v1/admin/users/{user_id}
Content-Type: application/json

{
  "full_name": "Dr. Jane Smith",
  "role": "HOSPITAL_ADMIN",
  "is_active": true,
  "is_verified": true
}
```

#### Delete User (Soft Delete)
```bash
DELETE /api/v1/admin/users/{user_id}
```

#### Reset User Password
```bash
POST /api/v1/admin/users/{user_id}/reset-password
Content-Type: application/json

{
  "new_password": "NewSecurePassword123!"
}
```

#### Toggle User Block Status
```bash
POST /api/v1/admin/users/{user_id}/toggle-block
```

---

## Analytics & Monitoring

### Overview Analytics
```bash
GET /api/v1/admin/analytics/overview
?days=30
```

**Parameters:**
- `days`: Number of days to analyze (1-365)

**Response:**
```json
{
  "users": {
    "total": 1250,
    "active": 950,
    "verified": 1100,
    "new_in_period": 45,
    "role_distribution": {
      "SUPER_ADMIN": 1,
      "HOSPITAL_ADMIN": 5,
      "DOCTOR": 150,
      "PATIENT": 1050,
      "RESEARCHER": 44
    }
  },
  "diagnoses": {
    "total": 5420,
    "in_period": 320,
    "average_trust_score": 0.852
  },
  "hospitals": {
    "total": 12,
    "verified": 10
  },
  "period_days": 30
}
```

### Daily Statistics
```bash
GET /api/v1/admin/analytics/daily-stats
?days=30
```

**Response:**
```json
{
  "statistics": [
    {
      "date": "2024-01-01",
      "new_users": 5,
      "new_diagnoses": 12
    },
    ...
  ]
}
```

### User Growth
```bash
GET /api/v1/admin/analytics/user-growth
```

**Response:**
```json
{
  "monthly_growth": [
    {
      "month": "2023-01",
      "new_users": 45
    },
    ...
  ]
}
```

---

## Data Management

### View Records
```bash
GET /api/v1/admin/data/records
?skip=0&limit=20&disease_key=diabetes&search=patient_name
```

**Parameters:**
- `skip`: Pagination offset
- `limit`: Records per page (1-100)
- `disease_key`: Filter by disease (optional)
- `search`: Search by patient name/email (optional)

### Delete Record
```bash
DELETE /api/v1/admin/data/records/{record_id}
```

### Export Data
```bash
GET /api/v1/admin/data/export
?record_type=all&format=csv
```

**Parameters:**
- `record_type`: `all`, `users`, `records`, `hospitals`
- `format`: `json` or `csv`

---

## Security & Audit

### Audit Logs
```bash
GET /api/v1/admin/audit/logs
?skip=0&limit=50&actor_id=user_id&action=Updated&days=30
```

**Parameters:**
- `skip`: Pagination offset
- `limit`: Records per page (1-200)
- `actor_id`: Filter by user who performed action (optional)
- `action`: Filter by action type (optional)
- `days`: Time range (1-365)

### User Activity
```bash
GET /api/v1/admin/audit/user-activity/{user_id}
?days=30
```

---

## System Settings

### Get System Settings
```bash
GET /api/v1/admin/settings/system
```

**Response:**
```json
{
  "project_name": "TrustMedAI-Chain",
  "environment": "production",
  "api_port": 8000,
  "jwt_algorithm": "HS256",
  "access_token_expire_minutes": 30,
  "refresh_token_expire_days": 7,
  "blockchain": {
    "ethereum_enabled": true,
    "fabric_enabled": true
  }
}
```

### Get MFA Status
```bash
GET /api/v1/admin/settings/mfa-status
```

### Send Announcement
```bash
POST /api/v1/admin/settings/send-announcement
Content-Type: application/json

{
  "title": "System Maintenance",
  "message": "System will be under maintenance on Saturday.",
  "target_role": "DOCTOR"
}
```

---

## API Reference

### Authentication

All admin endpoints require authentication with a valid JWT token that includes admin permissions.

**Headers:**
```
Authorization: Bearer {access_token}
```

### Permissions Required

| Endpoint | Required Permission |
|----------|-------------------|
| `/admin/users` | `users:manage` |
| `/admin/analytics/*` | `platform:manage` |
| `/admin/data/*` | `platform:manage` |
| `/admin/audit/*` | `audit:view` |
| `/admin/hospitals` | `hospitals:manage` |
| `/admin/settings/*` | `platform:manage` |

### Error Responses

#### 401 Unauthorized
```json
{
  "detail": "Not authenticated"
}
```

#### 403 Forbidden
```json
{
  "detail": "Permission denied. Required: users:manage"
}
```

#### 404 Not Found
```json
{
  "detail": "User not found"
}
```

---

## Role-Based Access Control (RBAC)

### Permission Matrix

| Role | Users | Analytics | Data | Audit | Hospitals | Settings |
|------|-------|-----------|------|-------|-----------|----------|
| SUPER_ADMIN | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| HOSPITAL_ADMIN | ✓ | ✗ | ✗ | ✓ | ✗ | ✗ |
| DOCTOR | ✗ | ✗ | ✗ | ✓ | ✗ | ✗ |
| PATIENT | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ |
| RESEARCHER | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ |

---

## Troubleshooting

### Common Issues

#### 1. Unable to Access Admin Dashboard

**Problem:** User doesn't have admin permissions

**Solution:** 
- Ensure user has `SUPER_ADMIN` or `HOSPITAL_ADMIN` role
- Check JWT token validity and permissions

#### 2. Analytics Not Loading

**Problem:** Analytics endpoint returns empty data

**Solution:**
- Ensure data exists in the specified date range
- Check database connectivity
- Verify user has `platform:manage` permission

#### 3. Audit Logs Not Showing

**Problem:** No audit logs appear

**Solution:**
- Verify `audit:view` permission
- Check date range filter
- Ensure events have been logged (actions performed after audit implementation)

#### 4. User Deletion Fails

**Problem:** Cannot delete admin's own account

**Solution:**
- Use another admin account to delete user
- Admins cannot delete their own accounts for security

### Debug Mode

Enable debug logging by setting environment variable:
```bash
export LOG_LEVEL=DEBUG
```

Check logs:
```bash
tail -f logs/admin.log
```

---

## Security Best Practices

1. **Strong Passwords**: Require admin users to use strong passwords
2. **MFA**: Enable two-factor authentication for all admin accounts
3. **Audit Logging**: Regularly review audit logs for suspicious activity
4. **Access Control**: Follow principle of least privilege
5. **Token Rotation**: Refresh tokens regularly
6. **Backup**: Regularly backup admin audit logs
7. **Rate Limiting**: Implement rate limiting on sensitive endpoints

---

## Performance Optimization

### Database Indexing

Ensure indexes are created on frequently queried columns:
```sql
CREATE INDEX idx_user_email ON users(email);
CREATE INDEX idx_user_role ON users(role);
CREATE INDEX idx_audit_actor ON audit_events(actor_id);
CREATE INDEX idx_audit_created ON audit_events(created_at);
```

### Pagination

Always use pagination for large datasets:
- Default: 10-20 records per page
- Maximum: 100 records per page

### Caching

Cache analytics data with 5-minute TTL to reduce database queries.

---

## Support & Feedback

For issues or feature requests, contact the development team or open an issue in the repository.

**Last Updated:** January 2024
**Version:** 1.0.0
