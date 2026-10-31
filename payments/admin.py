from django.contrib import admin
from .models import DailyMetricSnapshot, Payment

admin.site.register(Payment)
admin.site.register(DailyMetricSnapshot)
