# AWS S3 Media Storage Setup Guide

This guide explains how to set up AWS S3 for storing media files (profile photos, documents, etc.) in production.

## Why Use S3?

- **Scalability**: No server disk space limits
- **Reliability**: 99.999999999% durability (11 9's)
- **Performance**: Global CDN distribution
- **Cost-effective**: Pay only for what you use (~$0.023/GB/month)
- **No server management**: Files automatically backed up and replicated

## Prerequisites

1. AWS Account (create at https://aws.amazon.com)
2. AWS CLI installed (optional but recommended)

## Step 1: Create an S3 Bucket

### Via AWS Console:

1. Go to [AWS S3 Console](https://s3.console.aws.amazon.com/s3/)
2. Click **"Create bucket"**
3. **Bucket name**: Choose a unique name (e.g., `haos-media-production`)
   - Must be globally unique
   - Lowercase only, no spaces
4. **Region**: Choose closest to your users (e.g., `us-east-1` for US, `eu-west-1` for Europe)
5. **Object Ownership**: Select "ACLs enabled" → "Bucket owner preferred"
6. **Block Public Access**:
   - ✅ Uncheck "Block all public access"
   - ⚠️ Acknowledge the warning (we need public read for profile photos)
7. **Bucket Versioning**: Enable (recommended for backup)
8. **Encryption**: Enable (Server-side encryption with Amazon S3 managed keys)
9. Click **"Create bucket"**

### Configure Bucket Policy:

After creating the bucket, set up public read access for media files:

1. Go to your bucket → **Permissions** tab
2. Scroll to **Bucket policy**
3. Click **Edit** and paste:

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "PublicReadGetObject",
            "Effect": "Allow",
            "Principal": "*",
            "Action": "s3:GetObject",
            "Resource": "arn:aws:s3:::haos-media-production/media/*"
        }
    ]
}
```

**Replace** `haos-media-production` with your actual bucket name.

This allows public read access only to files in the `media/` folder, keeping private files secure.

## Step 2: Create IAM User for Django

Django needs AWS credentials to upload files. Create a dedicated IAM user:

### Via AWS Console:

1. Go to [IAM Console](https://console.aws.amazon.com/iam/)
2. Click **Users** → **Add users**
3. **User name**: `django-s3-user`
4. **Access type**: ✅ Programmatic access (API, SDK access)
5. Click **Next: Permissions**
6. Click **Attach policies directly**
7. Click **Create policy** (opens new tab):
   - Click **JSON** tab
   - Paste this policy:

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "s3:PutObject",
                "s3:GetObject",
                "s3:DeleteObject",
                "s3:ListBucket"
            ],
            "Resource": [
                "arn:aws:s3:::haos-media-production",
                "arn:aws:s3:::haos-media-production/*"
            ]
        }
    ]
}
```

   - **Replace** `haos-media-production` with your bucket name
   - Click **Next: Tags** → **Next: Review**
   - **Name**: `DjangoS3Access`
   - Click **Create policy**

8. Go back to the user creation tab, refresh policies
9. Search for `DjangoS3Access` and ✅ check it
10. Click **Next: Tags** → **Next: Review** → **Create user**
11. **⚠️ IMPORTANT**: Copy the **Access Key ID** and **Secret Access Key**
    - You won't be able to see the secret key again!
    - Store them securely (password manager, env file)

## Step 3: Configure Django Settings

### Local Development (keep using local files):

Your `.env` file already has `USE_S3=False` by default. No changes needed for local dev.

### Production Server:

Add these environment variables to your production `.env` file:

```bash
# AWS S3 Configuration
USE_S3=True
AWS_ACCESS_KEY_ID=AKIAIOSFODNN7EXAMPLE
AWS_SECRET_ACCESS_KEY=wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY
AWS_STORAGE_BUCKET_NAME=haos-media-production
AWS_S3_REGION_NAME=us-east-1
```

**Replace** with your actual values from Step 2.

## Step 4: Upload Existing Photos to S3

After deploying your code to production:

### Test Upload (Dry Run):

```bash
python manage.py upload_media_to_s3 --dry-run
```

This shows what will be uploaded without actually uploading.

### Upload Files:

```bash
python manage.py upload_media_to_s3
```

This will:
- Upload all 32 artist profile photos to S3
- Update database references to use S3 URLs
- Show progress and summary

Example output:
```
✅ Smiley: Uploaded entity_photos/smiley_qXk8ND6.jpg (42.7 KB)
✅ Feli: Uploaded entity_photos/feli_2pUMSbg.jpg (38.1 KB)
...
✅ Uploaded: 32 files
```

### Verify Upload:

1. Check S3 bucket: Go to AWS Console → S3 → Your bucket → `media/entity_photos/`
2. Open your app and check if photos display correctly
3. URLs should look like: `https://haos-media-production.s3.amazonaws.com/media/entity_photos/smiley_qXk8ND6.jpg`

## Step 5: Clean Up (Optional)

After confirming all photos work from S3:

```bash
# On production server only, NOT local dev
rm -rf /path/to/backend/media/entity_photos/
```

Keep the `media/` folder structure for future uploads.

## How It Works

### Local Development (USE_S3=False):
- Files stored in `backend/media/`
- URLs: `http://localhost:8000/media/entity_photos/photo.jpg`
- Fast, no AWS costs

### Production (USE_S3=True):
- Files uploaded to S3 automatically when saved
- URLs: `https://bucket-name.s3.amazonaws.com/media/entity_photos/photo.jpg`
- Globally accessible, highly available
- No server disk usage

## Cost Estimate

For 32 profile photos (~40 KB each):
- **Storage**: ~1.3 MB = **$0.00003/month** (negligible)
- **Requests**: Upload once = **$0.000016** (one-time)
- **Transfer**: 1000 views/month = **$0.00012/month**
- **Total**: Less than **$0.01/month** for current usage

## Troubleshooting

### Photos not displaying:

1. **Check bucket policy**: Ensure public read access is enabled for `media/*`
2. **Check CORS**: If frontend is on different domain, add CORS configuration:
   - S3 Console → Your bucket → Permissions → CORS
   - Add:
   ```json
   [
       {
           "AllowedHeaders": ["*"],
           "AllowedMethods": ["GET"],
           "AllowedOrigins": ["https://yourdomain.com"],
           "ExposeHeaders": []
       }
   ]
   ```

### Upload fails with "Access Denied":

1. **Check IAM policy**: Ensure `django-s3-user` has correct permissions
2. **Check credentials**: Verify `AWS_ACCESS_KEY_ID` and `AWS_SECRET_ACCESS_KEY` are correct
3. **Check bucket name**: Ensure `AWS_STORAGE_BUCKET_NAME` matches exactly

### Files uploaded but not public:

1. **Check bucket policy**: Must allow `s3:GetObject` for `media/*`
2. **Check ACL**: Bucket must have ACLs enabled
3. Run: `python manage.py upload_media_to_s3` again to re-upload with correct permissions

## Security Best Practices

✅ **DO**:
- Use separate buckets for different environments (dev, staging, prod)
- Enable bucket versioning for backups
- Use IAM user with minimal permissions
- Rotate access keys periodically
- Enable server-side encryption

❌ **DON'T**:
- Commit AWS credentials to git
- Use root AWS account credentials
- Make entire bucket public
- Share access keys

## Advanced: CloudFront CDN (Optional)

For even better performance, add CloudFront CDN in front of S3:

1. Create CloudFront distribution pointing to S3 bucket
2. Update Django settings:
   ```python
   AWS_S3_CUSTOM_DOMAIN = 'd123456abcdef.cloudfront.net'
   ```
3. Photos will be cached globally at edge locations
4. Even faster load times worldwide

## Support

For AWS-specific issues:
- AWS Support: https://console.aws.amazon.com/support/
- AWS S3 Documentation: https://docs.aws.amazon.com/s3/

For Django integration issues:
- django-storages docs: https://django-storages.readthedocs.io/
