# MinIO Fallback Configuration Guide

## Overview
The TrustMedAI backend now has a resilient storage configuration that automatically falls back to local file storage when MinIO is unavailable. This makes local development easier while supporting production deployments with object storage.

## Storage Backend Options

### 1. **auto** (Default, Recommended for Local Development)
- First attempts to store artifacts in MinIO
- If MinIO is unavailable (DNS error, timeout, connection refused), automatically falls back to local storage
- No configuration needed for local development
- Seamlessly works with both Docker (MinIO available) and local development (MinIO unavailable)

```bash
# In .env or default
ARTIFACT_STORAGE_BACKEND=auto
```

### 2. **local** (Pure Local Storage)
- Stores all artifacts in `./.artifacts` directory
- No external dependencies
- Best for: offline development, testing, lightweight deployments

```bash
ARTIFACT_STORAGE_BACKEND=local
```

### 3. **minio** (Production Object Storage)
- Requires MinIO to be available and accessible
- Fails immediately if MinIO connection cannot be established
- Best for: production deployments, large-scale deployments

```bash
ARTIFACT_STORAGE_BACKEND=minio
MINIO_ENDPOINT=minio:9000  # Docker
# or
MINIO_ENDPOINT=s3.example.com  # AWS S3 or other S3-compatible service
```

## Configuration by Environment

### Local Development (Recommended Setup)

```bash
# .env or environment variables
ARTIFACT_STORAGE_BACKEND=auto
MINIO_ENDPOINT=localhost:9000
# MinIO not running locally? No problem! Falls back to local storage automatically
```

**What happens:**
1. Backend starts up successfully
2. If MinIO is running on localhost:9000, it will use MinIO
3. If MinIO is not available, it automatically falls back to `./.artifacts` directory
4. No warnings or errors about MinIO in normal operation

### Docker Development (with docker-compose)

```bash
# docker-compose sets these automatically
ARTIFACT_STORAGE_BACKEND=auto
MINIO_ENDPOINT=minio:9000
```

**What happens:**
1. MinIO service is available at `minio:9000`
2. Backend connects to MinIO successfully
3. All artifacts stored in MinIO bucket

### Production Deployment

```bash
# Production settings
ARTIFACT_STORAGE_BACKEND=minio
MINIO_ENDPOINT=s3.region.amazonaws.com  # AWS S3 or S3-compatible
MINIO_ACCESS_KEY=your-access-key
MINIO_SECRET_KEY=your-secret-key
MINIO_SECURE=true
MINIO_BUCKET=trustmedai-artifacts-prod
```

## Error Handling

### Connection Errors (Automatically Handled)

When using `ARTIFACT_STORAGE_BACKEND=auto`, the following errors are gracefully handled:

- **NameResolutionError** - MinIO hostname not resolvable (e.g., 'minio' in local dev)
- **ConnectTimeoutError** - Connection to MinIO timed out
- **NewConnectionError** - Cannot establish connection to MinIO
- **MaxRetryError** - Connection retry attempts exhausted

**Behavior:**
- Log a debug message (not alarming)
- Fall back to local storage
- Continue operation normally

### Connection Errors with ARTIFACT_STORAGE_BACKEND=minio

When `minio` backend is explicitly required:
- Connection errors will raise an exception
- Application will fail fast
- Operator must resolve the MinIO availability issue

## Logging

### Local Development

Expected log output when MinIO is unavailable:

```
[INFO] Starting TrustMedAI backend and initializing runtime schema
[DEBUG] MinIO at localhost:9000 unavailable (NameResolutionError); falling back to local storage for reports/report_xxx.pdf
```

**This is normal and expected.** No action needed.

### Production

If MinIO errors appear in production with `ARTIFACT_STORAGE_BACKEND=minio`:

```
[ERROR] MinIO connection failed: Connection refused at minio:9000
```

**Action required:** Check MinIO service is running and accessible.

## Testing Different Backends

### Test Local Storage Mode
```bash
export ARTIFACT_STORAGE_BACKEND=local
python -m uvicorn app.main:app --reload
# All artifacts stored in ./.artifacts
```

### Test MinIO with Docker
```bash
docker-compose up -d minio
export ARTIFACT_STORAGE_BACKEND=minio
export MINIO_ENDPOINT=localhost:9000
python -m uvicorn app.main:app --reload
# All artifacts stored in MinIO
```

### Test Auto Fallback
```bash
# Start backend without MinIO running
export ARTIFACT_STORAGE_BACKEND=auto
python -m uvicorn app.main:app --reload
# Will use local storage

# Later, start MinIO
docker run -p 9000:9000 minio/minio server /data
# New artifacts will use MinIO automatically
```

## Troubleshooting

### Q: Getting warnings about MinIO connection
**A:** This is normal in local development with `ARTIFACT_STORAGE_BACKEND=auto`. The backend is trying MinIO, timing out, then falling back to local storage. This is the expected behavior.

### Q: Want to suppress MinIO fallback warnings
**A:** The warnings are logged at DEBUG level when using `auto` mode. If you want to silence them:
```bash
export ARTIFACT_STORAGE_BACKEND=local  # Don't try MinIO at all
```

### Q: Artifacts stored in MinIO, can't read them locally
**A:** Objects have path prefixes indicating their storage backend:
- `minio:reports/report_xxx.pdf` - Stored in MinIO (requires MinIO to read)
- `local:reports/report_xxx.pdf` - Stored locally (readable anytime)

When switching from MinIO to local storage, existing MinIO-stored objects won't be accessible. Start fresh or migrate MinIO bucket data.

### Q: Running in Docker, MinIO container fails to start
**A:** With `ARTIFACT_STORAGE_BACKEND=auto`, the backend will work fine using local storage in the container. You only need MinIO if you want artifact persistence across container restarts.

To use MinIO in Docker:
1. Check docker-compose.yml has minio service
2. Ensure minio:9000 is resolvable from backend container
3. Check MINIO_ENDPOINT environment variable

## Storage Backend Decision Matrix

| Scenario | Recommended | Reason |
|----------|-------------|--------|
| Local development on Windows | `auto` | Works with or without MinIO |
| Local development on Linux/Mac | `auto` | Works with or without MinIO |
| Docker Compose development | `auto` or `minio` | MinIO in compose works automatically |
| Testing | `local` | No external dependencies |
| Production | `minio` | Explicit requirement, fail-fast |
| CI/CD testing | `local` | Fast, no setup |
| High-availability | `minio` + S3 | Use AWS S3 or S3-compatible |

## Environment Variables Reference

```
ARTIFACT_STORAGE_BACKEND     auto|minio|local         Default: auto
MINIO_ENDPOINT              hostname:port             Default: localhost:9000
MINIO_ACCESS_KEY            string                    Default: trustmedai
MINIO_SECRET_KEY            string                    Default: trustmedai123
MINIO_SECURE                true|false                Default: false
MINIO_BUCKET                string                    Default: trustmedai-artifacts
MINIO_TIMEOUT_SECONDS       integer                   Default: 5
LOCAL_ARTIFACT_DIR          file path                 Default: ./.artifacts
```

## Migration Guide

### From Local to MinIO
1. Set `ARTIFACT_STORAGE_BACKEND=auto`
2. Start MinIO: `docker run -p 9000:9000 minio/minio server /data`
3. New artifacts will use MinIO
4. Existing local artifacts remain accessible

### From MinIO to Local
1. Export MinIO bucket contents (if needed for recovery)
2. Set `ARTIFACT_STORAGE_BACKEND=local`
3. New artifacts stored locally
4. Old minio: prefixed paths won't work (migrate via backup)

### From Local to S3
1. Set `ARTIFACT_STORAGE_BACKEND=minio` (MinIO SDK supports S3 API)
2. Configure MINIO_ENDPOINT to S3: `s3.region.amazonaws.com`
3. Set MINIO_ACCESS_KEY and MINIO_SECRET_KEY to AWS credentials
4. Update bucket name in MINIO_BUCKET
5. Restart backend
6. Existing local artifacts won't be accessible (data migration needed)
