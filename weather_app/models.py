from django.db import models

class HourlyWeatherData(models.Model):
    location_name = models.CharField(max_length=255)
    region = models.CharField(max_length=255)
    country = models.CharField(max_length=255)
    time_epoch = models.BigIntegerField()
    time = models.DateTimeField()
    temp_c = models.FloatField()
    feelslike_c = models.FloatField()
    humidity = models.IntegerField()
    condition_text = models.CharField(max_length=255)
    chance_of_rain = models.IntegerField()

    def __str__(self):
        return f"{self.location_name} - {self.time}"
