from django.urls import path
from . import views

urlpatterns = [
    path('es-census-2011/test1/<province>', views.province_density_test),
    path('es-census-2011/test2/<count>', views.province_university_test)
    ]