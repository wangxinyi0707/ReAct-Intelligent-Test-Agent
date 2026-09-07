from django.contrib import admin
from .models import TravelPlan, DailySchedule, PackingItem

admin.site.register(TravelPlan)
admin.site.register(DailySchedule)
admin.site.register(PackingItem)
