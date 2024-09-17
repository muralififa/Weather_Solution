import requests
from django.shortcuts import render, redirect
from django.core.management import call_command
from .models import HourlyWeatherData
from .forms import CityForm
from datetime import datetime
from dateutil.parser import parse  # Import for parsing datetime strings

def get_weather_data(request):
    if request.method == 'POST':
        form = CityForm(request.POST)
        if form.is_valid():
            # Get the city from the form
            city = form.cleaned_data['city']
            # Set a session variable to indicate that the form was submitted
            request.session['city_submitted'] = city
            # Redirect to another view with the city as a URL parameter
            return redirect('show_weather_data', city=city)  # Redirect to the new URL with city as parameter

    else:
        form = CityForm()

    return render(request, 'weather_app/weather_form.html', {'form': form})

def show_weather_data(request, city):
    # Check if the form was submitted correctly by checking the session variable
    if 'city_submitted' not in request.session or request.session['city_submitted'] != city:
        # If not set or doesn't match, redirect back to the form page
        return redirect('get_weather_data')

    try:
        # Automatically apply migrations to ensure the database is up-to-date
        call_command('makemigrations', 'weather_app')  # Create migrations for the app
        call_command('migrate')  # Apply all migrations
    except Exception as e:
        return render(request, 'weather_app/weather_form.html', {'error': f"Migration error: {e}"})

    # Fetch current date
    current_date = datetime.now().strftime('%Y-%m-%d')
    api_key = '3ab5d56dff6242b8b0862351241709'
    url = f'http://api.weatherapi.com/v1/history.json?key={api_key}&q={city}&dt={current_date}'

    response = requests.get(url)
    data = response.json()

    # Check if the API call was successful
    if 'error' in data:
        return render(request, 'weather_app/weather_form.html', {'error': data['error']['message']})

    # Extract location data
    location = data['location']

    # Find the current time and closest hour data
    current_time = datetime.now()
    closest_hour_data = min(
        data['forecast']['forecastday'][0]['hour'],
        key=lambda x: abs(parse(x['time']) - current_time)
    )

    # Truncate the table to remove existing data
    HourlyWeatherData.objects.all().delete()

    # Loop through hourly data and save each hour's data
    for hour_data in data['forecast']['forecastday'][0]['hour']:
        hourly_weather = HourlyWeatherData(
            location_name=location['name'],
            region=location['region'],
            country=location['country'],
            time_epoch=hour_data['time_epoch'],
            time=parse(hour_data['time']),  # Parsing time string to datetime object
            temp_c=hour_data['temp_c'],
            feelslike_c=hour_data['feelslike_c'],
            humidity=hour_data['humidity'],
            condition_text=hour_data['condition']['text'],
            chance_of_rain=hour_data.get('chance_of_rain', 0)  # Default to 0 if not available
        )
        hourly_weather.save()

    # Prepare the current weather data using the closest hour data
    current_weather = {
        'location_name': location['name'],
        'region': location['region'],
        'temp_c': closest_hour_data['temp_c'],
        'humidity': closest_hour_data['humidity'],
    }

    # Check for extreme weather conditions
    extreme_conditions = False
    alert_message = ""

    # Define conditions for what is considered 'extreme'
    if closest_hour_data['temp_c'] > 40:
        extreme_conditions = True
        alert_message += "High temperature alert! "

    if closest_hour_data['condition']['text'] in ["Thunderstorm", "Heavy rain", "Snow", "Hail"]:
        extreme_conditions = True
        alert_message += "Severe weather alert! "

    # Additional checks can be added here for other extreme conditions

    # Query the hourly data from the database
    hourly_data = HourlyWeatherData.objects.all()

    # Pass both current and hourly weather data to the template
    context = {
        'current_weather': current_weather,
        'hourly_data': hourly_data,
        'extreme_conditions': extreme_conditions,
        'alert_message': alert_message,
    }

    # Clear the session variable after showing the data
    del request.session['city_submitted']

    return render(request, 'weather_app/weather_trends.html', context)
