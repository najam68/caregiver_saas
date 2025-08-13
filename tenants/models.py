from django.db import models
from django_tenants.models import TenantMixin, DomainMixin


class Client(TenantMixin):
    """
    One tenant = one Postgres schema.
    """
    name = models.CharField(max_length=100)
    paid_until = models.DateField(null=True, blank=True)
    on_trial = models.BooleanField(default=True)
    created_on = models.DateField(auto_now_add=True)

    def __str__(self):
        return f"{self.schema_name} ({self.name})"


class Domain(DomainMixin):
    """
    Domain used to route requests to the right tenant.
    e.g. acme.localhost -> schema 'acme'
    """
    pass