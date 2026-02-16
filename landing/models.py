from django.db import models
from django.contrib.auth.models import User

class Restroom(models.Model):
    STATUS_CHOICES = [
        ('Operational', 'Operational'),
        ('Maintenance', 'Maintenance'),
        ('Cleaning', 'Cleaning'),
        ('Inactive', 'Inactive'),
    ]

    restroom_id = models.CharField(max_length=50, unique=True, help_text="Unique Identifier for the restroom")
    name = models.CharField(max_length=100)
    latitude = models.FloatField(help_text="Latitude for map location")
    longitude = models.FloatField(help_text="Longitude for map location")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Operational')
    capacity = models.IntegerField(help_text="Maximum capacity of the restroom")
    last_cleaned = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    admin = models.ForeignKey(User, on_delete=models.CASCADE, related_name='restrooms')

    def __str__(self):
        return f"{self.name} ({self.restroom_id})"

class Sensor(models.Model):
    SENSOR_STATUS = [
        ('Active', 'Active'),
        ('Inactive', 'Inactive'),
        ('Calibration', 'Calibration'),
    ]

    sensor_id = models.CharField(max_length=50, unique=True, help_text="Unique Identifier for the sensor")
    restroom = models.ForeignKey(Restroom, on_delete=models.SET_NULL, null=True, blank=True, related_name='sensors')
    sensor_type = models.CharField(max_length=50, help_text="Type of sensor (e.g. Ammonia, Smoke,Footfall)")
    threshold_min = models.FloatField(null=True, blank=True, help_text="Minimum threshold value")
    threshold_max = models.FloatField(null=True, blank=True, help_text="Maximum threshold value")
    status = models.CharField(max_length=20, choices=SENSOR_STATUS, default='Active')
    installed_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        restroom_name = self.restroom.name if self.restroom else "Unassigned"
        return f"{self.sensor_type} ({self.sensor_id}) - {restroom_name}"

class SensorReading(models.Model):
    sensor = models.ForeignKey(Sensor, on_delete=models.CASCADE, related_name='readings')
    value = models.FloatField(help_text="Reading value")
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.sensor.sensor_id} - {self.value} at {self.timestamp}"

class Staff(models.Model):
    name = models.CharField(max_length=100)
    email = models.EmailField()
    phone = models.CharField(max_length=20)
    shift_start = models.TimeField()
    shift_end = models.TimeField()
    role = models.CharField(max_length=50)
    created_at = models.DateTimeField(auto_now_add=True)
    nfc_tag = models.CharField(max_length=100, unique=True, help_text="NFC Tag ID")
    restroom = models.ForeignKey(Restroom, on_delete=models.CASCADE, related_name='staff')

    def __str__(self):
        return f"{self.name} - {self.role} ({self.restroom.name if self.restroom else 'Unassigned'})"

class CleaningActivity(models.Model):
    STATUS_CHOICES = [
        ('Pending', 'Pending'),
        ('In Progress', 'In Progress'),
        ('Complete', 'Complete'),
    ]

    activity_type = models.CharField(max_length=100, help_text="Type of cleaning activity (e.g., Deep Clean)")
    start_time = models.DateTimeField(help_text="Scheduled start time")
    end_time = models.DateTimeField(null=True, blank=True, help_text="Actual completion time")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Pending')
    restroom = models.ForeignKey(Restroom, on_delete=models.CASCADE, related_name='cleaning_activities')
    staff = models.ForeignKey(Staff, on_delete=models.SET_NULL, null=True, blank=True, related_name='cleaning_activities')

    def __str__(self):
        return f"{self.activity_type} - {self.status} ({self.restroom.name})"
