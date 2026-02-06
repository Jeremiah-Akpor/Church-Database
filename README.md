# Church Management System - Django Project

## Project Overview
A comprehensive Church Management System built with Django and django-unfold admin interface.

## Features

### 1. Members App
- **Member Profiles**: Complete member management with personal info, contact details, and church information
- **Departments**: Organize members into church departments/groups
- **Families**: Track family units and relationships
- **Membership Status**: Active, Inactive, Visitor, New Convert tracking
- **Emergency Contacts**: Store emergency contact information

### 2. Events App
- **Event Management**: Create and manage church events (services, conferences, meetings, etc.)
- **Attendance Tracking**: Record event attendance for both members and visitors
- **Event Registration**: Handle event registrations with guest management
- **Recurring Events**: Support for weekly, monthly recurring events

### 3. Donations App
- **Donation Categories**: Organize donations (Tithes, Offerings, Special Projects)
- **Donation Records**: Track all donations with payment methods and receipts
- **Pledges**: Manage donation commitments and payment tracking
- **Tax Receipts**: Generate tax-deductible receipts
- **Anonymous Donations**: Support for anonymous giving

### 4. Sermons App
- **Sermon Library**: Archive sermons with audio/video support
- **Sermon Series**: Organize sermons into series
- **Scripture References**: Track scripture passages
- **Media Support**: Upload audio, video, presentations
- **Bible Study Materials**: Manage study resources

## Docker Deployment (Recommended)

### Quick Start with Docker

1. **Clone the repository and navigate to the project**
   ```bash
   cd church-management-system
   ```

2. **Create environment file**
   ```bash
   cp .env.example .env
   ```
   Edit `.env` and set secure values:
   ```bash
   SECRET_KEY=generate-a-random-64-character-secret-key
   DB_PASSWORD=use-a-strong-database-password
   DEBUG=False
   ALLOWED_HOSTS=your-domain.com,localhost
   SECURE_SSL_REDIRECT=True
   SESSION_COOKIE_SECURE=True
   CSRF_COOKIE_SECURE=True
   ```

3. **Build and start the containers**
   ```bash
   docker-compose up --build -d
   ```

4. **Access the application**
   - Admin Panel: http://localhost/admin/
   - No default admin account is created unless all `DJANGO_SUPERUSER_*` variables are set.

### Docker Services

The docker-compose setup includes:
- **web**: Django application (Gunicorn + Whitenoise)
- **db**: PostgreSQL 15 database
- **nginx**: Nginx reverse proxy with static file serving

### Docker Commands

```bash
# Build and start
docker-compose up --build -d

# View logs
docker-compose logs -f web

# Run management commands
docker-compose exec web python manage.py shell
docker-compose exec web python manage.py createsuperuser

# Stop containers
docker-compose down

# Stop and remove volumes (WARNING: deletes database)
docker-compose down -v

# Restart a service
docker-compose restart web
```

### Production Deployment

For production deployment:

1. **Set secure environment variables**
   ```bash
   # .env file
   DEBUG=False
   SECRET_KEY=your-256-bit-secret-key
   ALLOWED_HOSTS=church.yourdomain.com
   DB_PASSWORD=very-secure-password
   ```

2. **Use Docker Swarm or Kubernetes** for high availability

3. **Configure SSL/TLS** with Let's Encrypt:
   ```yaml
   # Add to docker-compose.yml
   certbot:
     image: certbot/certbot
     volumes:
       - ./certbot/conf:/etc/letsencrypt
       - ./certbot/www:/var/www/certbot
   ```

4. **Backup database regularly**
   ```bash
   docker-compose exec db pg_dump -U church_user church_db > backup.sql
   ```

## Local Development Setup (Alternative)

### Prerequisites
- Python 3.13+
- PostgreSQL (running in Docker)
- Pipenv

### Setup Steps

1. **Activate Virtual Environment**
   ```bash
   pipenv shell
   ```

2. **Install Dependencies**
   ```bash
   pipenv install
   pipenv run pip install psycopg2-binary Pillow
   ```

3. **Configure PostgreSQL**
   
   Set environment variables in your `.env` file or shell:
   ```bash
   export DB_NAME=church_db
   export DB_USER=church_user
   export DB_PASSWORD=your_password
   export DB_HOST=localhost
   export DB_PORT=5432
   export SECRET_KEY=your-secret-key-here
   export DEBUG=True
   ```

4. **Run Migrations**
   ```bash
   pipenv run python manage.py migrate
   ```

5. **Create Superuser**
   ```bash
   pipenv run python manage.py createsuperuser
   ```

6. **Run Development Server**
   ```bash
   pipenv run python manage.py runserver
   ```

7. **Access Admin**
   Navigate to: http://127.0.0.1:8000/admin/

## Database Models

### Members
- **Department**: Church departments and groups
- **Member**: Individual member profiles
- **Family**: Family units
- **FamilyMember**: Links members to families with relationships

### Events
- **Event**: Church events and programs
- **EventAttendance**: Attendance tracking
- **EventRegistration**: Event sign-ups

### Donations
- **DonationCategory**: Types of donations
- **Donation**: Individual donation records
- **Pledge**: Commitment tracking
- **PledgePayment**: Payments against pledges

### Sermons
- **SermonSeries**: Collections of related sermons
- **Sermon**: Individual sermon records
- **SermonNote**: Additional resources
- **BibleStudyMaterial**: Study guides and curricula

## Django Unfold Configuration

The admin interface is configured with:
- Custom sidebar navigation
- Church-themed color scheme
- Collapsible sections
- Inline editing for related models
- Autocomplete fields for better UX

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `SECRET_KEY` | Django secret key | (generate one) |
| `DEBUG` | Debug mode | False |
| `ALLOWED_HOSTS` | Allowed hosts | (required, comma-separated) |
| `DB_NAME` | PostgreSQL database name | church_db |
| `DB_USER` | PostgreSQL user | church_user |
| `DB_PASSWORD` | PostgreSQL password | (required in non-debug mode) |
| `DB_HOST` | PostgreSQL host | localhost |
| `DB_PORT` | PostgreSQL port | 5432 |

## Next Steps

1. **Set up PostgreSQL in Docker** as per your requirements
2. **Run migrations**: `pipenv run python manage.py migrate`
3. **Create superuser**: `pipenv run python manage.py createsuperuser`
4. **Start adding data** through the admin interface
5. **Customize** the models as needed for your church's specific requirements

## Docker Architecture

```
┌─────────────────┐
│     Nginx       │  ← Port 80, Reverse Proxy
│   (nginx:alpine)│
└────────┬────────┘
         │
┌────────▼────────┐
│     Django      │  ← Port 8000, Gunicorn WSGI
│   (Python 3.13) │
└────────┬────────┘
         │
┌────────▼────────┐
│   PostgreSQL    │  ← Port 5432, Database
│  (postgres:15)  │
└─────────────────┘
```

### Volumes
- `postgres_data`: Persistent database storage
- `staticfiles`: Django collected static files
- `media`: User-uploaded media files

### Security Features
- Non-root user in Django container (UID 1000)
- Secrets managed via environment variables
- Health checks for database connectivity
- Static files served by Nginx with caching headers
- Startup runs `python manage.py check --deploy --fail-level WARNING`
- Startup fails fast when insecure/missing production env values are detected

## Security Notes

### Production Checklist
- [ ] Change default SECRET_KEY (use 256-bit random key)
- [ ] Set DEBUG=False
- [ ] Configure ALLOWED_HOSTS with your domain
- [ ] Use strong database password
- [ ] Change default admin credentials immediately
- [ ] Enable HTTPS/SSL with valid certificate
- [ ] Set CSRF_COOKIE_SECURE=True
- [ ] Set SESSION_COOKIE_SECURE=True
- [ ] Run `pipenv run safety check` regularly
- [ ] Keep Docker images updated
- [ ] Never commit `.env` files to version control
- [ ] Configure firewall (only expose ports 80/443)

### Environment Security
Store sensitive data in `.env` file (not in Git):
```bash
# .env - DO NOT COMMIT THIS FILE
SECRET_KEY=your-256-bit-secret-key-here
DB_PASSWORD=complex-password-123!@#
DEBUG=False
ALLOWED_HOSTS=your-domain.com
```

## Support

For issues or questions, refer to:
- Django Documentation: https://docs.djangoproject.com/
- Django Unfold Documentation: https://github.com/unfoldadmin/django-unfold
