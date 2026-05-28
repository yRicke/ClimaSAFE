from django.urls import path

from .views import select_location_api

urlpatterns = [
    path("select/", select_location_api, name="api-location-select"),
]
