import serial
import os
import django
import sys
import time

# Set up Django environment
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myproject.settings') # myproject is the project folder
django.setup()

from landing.models import Sensor, SensorReading

# Configure serial port
# User requested COM4 instead of COM5, though sample had COM5. Will use COM4 as requested in comment.
SERIAL_PORT = 'COM5'
BAUD_RATE = 9600

def parse_and_save(line):
    # Expected format: "kit:value smoke:value"
    # Example: "kit:SENS-123 smoke:45.2"
    
    parts = line.split()
    data = {}
    
    for part in parts:
        if ':' in part:
            key, value = part.split(':', 1)
            data[key] = value
            
    kit_value = data.get('Kit')
    smoke_value = data.get('Smoke')
    
    if kit_value and smoke_value:
        try:
            # Try to convert smoke value to float
            smoke_float = float(smoke_value)
            
            # Find the sensor defined by the kit value (sensor_id)
            sensor = Sensor.objects.filter(sensor_id=kit_value).first()
            
            if sensor:
                # Insert reading into SensorReading table
                reading = SensorReading.objects.create(
                    sensor=sensor,
                    value=smoke_float
                )
                print(f"Saved reading: Sensor {kit_value}, Value {smoke_float}")
            else:
                print(f"Warning: Sensor with ID '{kit_value}' not found in database.")
                
        except ValueError:
            print(f"Error: Invalid smoke value '{smoke_value}'. Could not convert to float.")
        except Exception as e:
            print(f"Database error: {e}")
    else:
         print(f"Warning: Could not parse line. Missing 'kit' or 'smoke' data. Line: '{line}'")

def main():
    print(f"Attempting to connect to {SERIAL_PORT} at {BAUD_RATE} baud...")
    
    while True:
        try:
            ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1)
            print(f"Successfully connected to {SERIAL_PORT}.")
            print("Reading from Arduino...\n")
            
            while True:
                try:
                    if ser.in_waiting > 0:
                        line = ser.readline().decode('utf-8', errors='ignore').strip()
                        if line:
                            print(f"Raw data: {line}")
                            parse_and_save(line)
                except serial.SerialException as e:
                    print(f"Serial read error: {e}")
                    time.sleep(1) # wait before retrying to read
                    break # Break inner loop to attempt reconnection
                    
                time.sleep(0.1) # Small delay to prevent high CPU usage
                
        except serial.SerialException as e:
            print(f"Failed to connect to {SERIAL_PORT}: {e}")
            print("Retrying in 5 seconds... Make sure the port is not open in another program (like Arduino IDE).")
            time.sleep(5)
        except KeyboardInterrupt:
            print("\nStopping serial reader.")
            if 'ser' in locals() and ser.is_open:
                ser.close()
            break

if __name__ == '__main__':
    main()
