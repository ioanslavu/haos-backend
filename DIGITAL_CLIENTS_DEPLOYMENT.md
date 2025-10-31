# Digital Clients - Production Deployment

## What was done locally:
- ✅ Imported 35 digital clients from CSV (31 new, 4 already existed)
- ✅ Created ContactPerson records with emails and phones
- ✅ Auto-fixed known data issues (swapped columns, etc.)
- ✅ Exported to fixture file: `digital_clients_fixture.json`

## Production Deployment Commands:

### 1. Upload fixture file to production server
```bash
# From your local machine
scp backend/digital_clients_fixture.json user@production:/path/to/backend/
```

### 2. On production server, run import
```bash
cd /path/to/backend
source venv/bin/activate

# Preview first (dry run)
python manage.py import_digital_clients_fixture --fixture digital_clients_fixture.json --dry-run

# Import for real
python manage.py import_digital_clients_fixture --fixture digital_clients_fixture.json
```

### 3. Optional: Update existing entities
```bash
# If entities already exist and you want to update them
python manage.py import_digital_clients_fixture --fixture digital_clients_fixture.json --update-existing
```

## What gets imported:
- 35 entities (kind='PJ', all companies)
- All get 'digital' role (primary, external)
- Some also get 'artist' or 'label' role (based on type)
- 31 ContactPerson records (role='partner')
- Contact emails and phones

## Notes:
- All entities are **external** (is_internal=False)
- All have 'digital' as **primary role**
- 4 entities already existed in DB (Zurli, National TV, Codu Penal, Litoo) - will be skipped unless --update-existing is used
- Phone numbers are cleaned to digits only
- Known data issues (row 6, row 18) were auto-fixed before export
