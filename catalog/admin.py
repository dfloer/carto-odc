from django.contrib import admin
from catalog.models import *

admin.site.register(Catalog)
admin.site.register(FriendlyName)
admin.site.register(MultiPolygonStore)
admin.site.register(DataStore)
