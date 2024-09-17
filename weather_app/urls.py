from django.urls import path
from .views import get_weather_data, show_weather_data

urlpatterns = [
    path('', get_weather_data, name='get_weather_data'),
    path('weather/<str:city>/', show_weather_data, name='show_weather_data'),  # URL to handle city parameter
]
