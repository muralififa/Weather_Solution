import requests
import os
from django.shortcuts import render, redirect
from django.core.management import call_command
from .models import HourlyWeatherData
from .forms import CityForm
from datetime import datetime
from dateutil.parser import parse  

def get_weather_data(request):
    if request.method == 'POST':
        form = CityForm(request.POST)
        if form.is_valid():
            city = form.cleaned_data['city']
            request.session['city_submitted'] = city
            return redirect('show_weather_data', city=city)
    else:
        form = CityForm()

    return render(request, 'weather_app/weather_form.html', {'form': form})

def show_weather_data(request, city):
    if 'city_submitted' not in request.session or request.session['city_submitted'] != city:
        return redirect('get_weather_data')

    try:
        call_command('makemigrations', 'weather_app')  # Create migrations for the app
        call_command('migrate')  # Apply all migrations
    except Exception as e:
        return render(request, 'weather_app/weather_form.html', {'error': f"Migration error: {e}"})

    current_date = datetime.now().strftime('%Y-%m-%d')
    api_key = os.getenv('WEATHER_API_KEY')
    url = f'http://api.weatherapi.com/v1/history.json?key={api_key}&q={city}&dt={current_date}'

    response = requests.get(url)
    data = response.json()

    if 'error' in data:
        # If the API returns an error, redirect to the form with an error message
        return render(request, 'weather_app/weather_form.html', {
            'form': CityForm(),
            'error_message': "Please enter a valid city name."
        })

    location = data['location']

    current_time = datetime.now()
    closest_hour_data = min(
        data['forecast']['forecastday'][0]['hour'],
        key=lambda x: abs(parse(x['time']) - current_time)
    )

    # Clear previous weather data
    HourlyWeatherData.objects.all().delete()

    # Save new weather data to the database
    for hour_data in data['forecast']['forecastday'][0]['hour']:
        hourly_weather = HourlyWeatherData(
            location_name=location['name'],
            region=location['region'],
            country=location['country'],
            time_epoch=hour_data['time_epoch'],
            time=parse(hour_data['time']),
            temp_c=hour_data['temp_c'],
            feelslike_c=hour_data['feelslike_c'],
            humidity=hour_data['humidity'],
            condition_text=hour_data['condition']['text'],
            chance_of_rain=hour_data.get('chance_of_rain', 0)
        )
        hourly_weather.save()

    current_weather = {
        'location_name': location['name'],
        'region': location['region'],
        'temp_c': closest_hour_data['temp_c'],
        'humidity': closest_hour_data['humidity'],
    }

    extreme_conditions = False
    alert_message = ""
    if closest_hour_data['temp_c'] > 40:
        extreme_conditions = True
        alert_message += "High temperature alert! "

    if closest_hour_data['condition']['text'] in ["Thunderstorm", "Heavy rain", "Snow", "Hail"]:
        extreme_conditions = True
        alert_message += "Severe weather alert! "

    hourly_data = HourlyWeatherData.objects.all()

    context = {
        'current_weather': current_weather,
        'hourly_data': hourly_data,
        'extreme_conditions': extreme_conditions,
        'alert_message': alert_message,
    }

    # Clear session after using the city value
    del request.session['city_submitted']

    return render(request, 'weather_app/weather_trends.html', context)
