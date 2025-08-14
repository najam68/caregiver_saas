# Caregiver SaaS — Technical Manual & Development Guide

**Stack**: Django + PostgreSQL, `django-tenants` (schema-per-tenant), dotenv, venv.

---

## 1) Architecture

- **One PostgreSQL database**, **one schema per tenant** (`public`, `acme`, `abcore`, …).
- `django-tenants` switches the active schema based on the **hostname**.
- **Public schema** (control plane): Tenants (Clients/Domains), Controlpanel (Features/TenantFeature), root Django Admin.
- **Tenant schemas** (data plane): business data + tenant-only apps and each tenant’s own Django Admin.

**Admin separation**
- **Public admin**: `http://localhost:8000/admin` → manage Clients/Domains, Features/Tenant features.
- **Tenant admin**: `http://<tenant>.localhost:8000/admin` → manage only tenant data (Users/Groups + tenant apps).

---

## 2) Repository layout (expected)

```
caregiver_saas/
├─ manage.py
├─ caregiver/               # project settings/urls
│  ├─ settings.py
│  └─ urls.py
├─ tenants/                 # SHARED app: Client/Domain + public admin tools
│  ├─ models.py
│  ├─ forms.py
│  └─ admin.py              # public-only registration
├─ controlpanel/            # SHARED app: feature flags
│  ├─ models.py             # Feature (auto code), TenantFeature
│  ├─ admin.py              # public-only registration
│  ├─ utils.py              # feature_enabled/limit + decorators/mixin
│  └─ context_processors.py # exposes FEATURES dict
├─ organizations/           # TENANT app (optional baseline)
│  └─ models.py
├─ caregivers/              # TENANT app (example feature app)
│  ├─ models.py
│  └─ admin.py              # tenant-only registration
├─ templates/
│  ├─ admin/base_site.html  # branding + hide “Recent actions” on tenant sites
│  └─ admin/tenants/create_admin_user.html
├─ requirements.txt
└─ .env   (ignored)
```

---

## 3) Settings essentials

```python
# db engine aware of schemas
DATABASES = {
  "default": {
    "ENGINE": "django_tenants.postgresql_backend",
    "NAME": env("DB_NAME"),
    "USER": env("DB_USER"),
    "PASSWORD": env("DB_PASSWORD"),
    "HOST": env("DB_HOST", default="127.0.0.1"),
    "PORT": env("DB_PORT", default="5432"),
  }
}

PUBLIC_SCHEMA_NAME = "public"
TENANT_MODEL = "tenants.Client"
TENANT_DOMAIN_MODEL = "tenants.Domain"
DATABASE_ROUTERS = ["django_tenants.routers.TenantSyncRouter"]

SHARED_APPS = [
  "django_tenants",
  "tenants",
  "controlpanel",
  "django.contrib.contenttypes",
  "django.contrib.staticfiles",
  "django.contrib.messages",
  "django.contrib.sessions",
  "django.contrib.admin",
]
TENANT_APPS = [
  "django.contrib.contenttypes",
  "django.contrib.auth",
  "django.contrib.sessions",
  "django.contrib.messages",
  "django.contrib.staticfiles",
  # tenant feature apps go here, e.g. "caregivers"
]
INSTALLED_APPS = list(dict.fromkeys(SHARED_APPS + TENANT_APPS))

MIDDLEWARE = [
  "django_tenants.middleware.main.TenantMainMiddleware",
  "django.middleware.security.SecurityMiddleware",
  "django.contrib.sessions.middleware.SessionMiddleware",
  "django.middleware.common.CommonMiddleware",
  "django.middleware.csrf.CsrfViewMiddleware",
  "django.contrib.auth.middleware.AuthenticationMiddleware",
  "django.contrib.messages.MessageMiddleware",
  "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

SHOW_PUBLIC_IF_NO_TENANT_FOUND = True

# templates
TEMPLATES[0]["OPTIONS"]["context_processors"].append(
  "controlpanel.context_processors.feature_flags"
)
```

**.env example**
```
DEBUG=True
SECRET_KEY=replace-me
ALLOWED_HOSTS=127.0.0.1,localhost,acme.localhost,abcore.localhost
DB_NAME=caregiver_db
DB_USER=caregiver_user
DB_PASSWORD=your_password
DB_HOST=127.0.0.1
DB_PORT=5432
```

---

## 4) Public (control) apps

### tenants
- Models: `Client(TenantMixin)`, `Domain(DomainMixin)`
- Admin (public-only):
  - Domains inline
  - “Open Tenant Admin” link
  - “Create/Reset Tenant Admin User” (uses `tenant_context` to create/update superuser; optionally link to `organizations` owner)

### controlpanel (feature flags)
- Models (public schema):
  - `Feature{ code(auto), name, description, default_enabled, default_limit }`
  - `TenantFeature{ tenant, feature, enabled?, limit? }` (blank = inherit default)
- Utilities:
  - `feature_enabled(tenant, code)` → bool
  - `feature_limit(tenant, code)` → Optional[int]
  - `require_feature(code)` decorator & `FeatureRequiredMixin`
- Template context: `FEATURES` dict available to tenant templates.

**Admin visibility**: both models are **public-only**; tenants can’t see or edit them.

### Admin UX
- `templates/admin/base_site.html` brands header as **Caregiver Root Admin** (public) or **<Tenant> Admin** (tenant) and hides **Recent actions** on tenant sites.

---

## 5) Tenant (data) apps

**Example: caregivers**
```python
# caregivers/models.py
from django.db import models
class Caregiver(models.Model):
    full_name = models.CharField(max_length=120)
    phone = models.CharField(max_length=30, blank=True)
    email = models.EmailField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    def __str__(self): return self.full_name
```

```python
# caregivers/admin.py  (tenant-only + gated by feature)
from django.contrib import admin
from django.db import connection
from controlpanel.utils import feature_enabled
from .models import Caregiver

if getattr(connection, "schema_name", "public") != "public":
    @admin.register(Caregiver)
    class CaregiverAdmin(admin.ModelAdmin):
        list_display = ("full_name", "phone", "email", "created_at")
        def _enabled(self, request): 
            return feature_enabled(getattr(request, "tenant", None), "caregivers")
        def has_module_permission(self, request): return self._enabled(request)
        def has_view_permission(self, request, obj=None): return self._enabled(request)
        def has_add_permission(self, request): return self._enabled(request)
        def has_change_permission(self, request, obj=None): return self._enabled(request)
        def has_delete_permission(self, request, obj=None): return self._enabled(request)
```

**Views/URLs**: use `@require_feature("scheduling")` or `FeatureRequiredMixin` in tenant apps.

**Templates**: show menus conditionally with `FEATURES`:
```django
{% if FEATURES.scheduling %}<a href="{% url 'scheduling:dashboard' %}">Scheduling</a>{% endif %}
```

---

## 6) Provisioning & operations

**Create tenant (public admin)**
1) Tenants → Clients → Add (`schema_name`, `name`)
2) Tenants → Domains → Add (`acme.localhost`, primary ✓)
3) Migrate tenant apps into that schema (once):
   ```bash
   python manage.py migrate_schemas --tenant --schema=acme
   ```
4) In Client page → **Create/Reset Tenant Admin User**
5) Assign features via **Tenant features** inline

**Migrations**
- Shared: `python manage.py makemigrations tenants controlpanel && python manage.py migrate_schemas --shared`
- Tenant apps (all): `python manage.py makemigrations caregivers && python manage.py migrate_schemas --tenant`
- Single tenant: add `--schema=<name>`

**Common**
```
python manage.py check
python manage.py runserver
```

---

## 7) Troubleshooting

- **No tenant for hostname** → add Domain row & ALLOWED_HOSTS, restart.
- **DisallowedHost** → add hostname to ALLOWED_HOSTS.
- **403 on /admin/controlpanel/** (tenant host) → expected; public-only.
- **No Users/Groups in tenant admin** → run tenant migrations for that schema.
- **Tenants menu shows on tenant site** → ensure tenants’ ModelAdmin registers only on public schema.
- **Confusing recent actions on tenant admin** → template hides sidebar on tenant sites (we added this).

---

## 8) Progress log
- Postgres + django-tenants wired; schema-per-tenant working.
- Tenants admin tools restored to `tenants/admin.py` (public-only).
- Controlpanel (Features/TenantFeature) added; `Feature.code` auto-generated + unique.
- Feature gating utilities + template context hooked in settings.
- Tenant admin branding + hide recent actions implemented.
- Tenants `acme` and `abcore` provisioned; domains mapped.
