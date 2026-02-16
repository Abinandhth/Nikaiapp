import random
from datetime import timedelta
from django.core.management.base import BaseCommand
from django.utils import timezone
from landing.models import Sensor, SensorReading

class Command(BaseCommand):
    help = 'Populates the database with mock sensor data'

    def handle(self, *args, **kwargs):
        self.stdout.write('Populating mock data...')

        # Sensors
        sensors_data = [
            {'sensor_id': 'S-001', 'sensor_type': 'Ammonia', 'threshold_min': 0, 'threshold_max': 25},
            {'sensor_id': 'S-002', 'sensor_type': 'Smoke', 'threshold_min': 0, 'threshold_max': 0.5},
            {'sensor_id': 'S-003', 'sensor_type': 'Footfall', 'threshold_min': 0, 'threshold_max': 1000},
        ]

        created_sensors = []
        for s_data in sensors_data:
            sensor, created = Sensor.objects.get_or_create(
                sensor_id=s_data['sensor_id'],
                defaults={
                    'sensor_type': s_data['sensor_type'],
                    'threshold_min': s_data['threshold_min'],
                    'threshold_max': s_data['threshold_max'],
                    'status': 'Active',
                    'restroom': None # Explicitly set to None as per request
                }
            )
            if created:
                self.stdout.write(f"Created Sensor: {sensor}")
            else:
                 self.stdout.write(f"Sensor already exists: {sensor}")
            created_sensors.append(sensor)

        # Readings
        for sensor in created_sensors:
            # Generate 5-10 readings
            num_readings = random.randint(5, 10)
            self.stdout.write(f"Generating {num_readings} readings for {sensor.sensor_id}...")
            
            for _ in range(num_readings):
                timestamp = timezone.now() - timedelta(minutes=random.randint(0, 60))
                value = 0.0

                if sensor.sensor_type == 'Ammonia':
                    value = random.uniform(0, 50) # 0-50 ppm
                elif sensor.sensor_type == 'Smoke':
                     value = random.choice([0.0, 1.0]) # 0 (No Smoke), 1 (Smoke)
                elif sensor.sensor_type == 'Footfall':
                    value = float(random.randint(0, 50)) # Count per interval
                
                SensorReading.objects.create(
                    sensor=sensor,
                    value=round(value, 2),
                    # timestamp auto-adds now, avoiding complexity with manual overrides for this simple mock
                )
                
        self.stdout.write(self.style.SUCCESS('Successfully populated mock data.'))
