from django.shortcuts import render, redirect
from django.contrib.auth.models import User
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from .models import Restroom, Sensor, Staff, CleaningActivity
import uuid

def index(request):
   
    return render(request, 'landing/index.html')

@login_required
def activation(request, restroom_id=None):
    # Determine mode: Create or Update
    mode = 'create'
    restroom = None
    ammonia_sensor = None
    smoke_sensor = None
    footfall_sensor = None
    
    if restroom_id:
        try:
            restroom = request.user.restrooms.get(restroom_id=restroom_id)
            mode = 'update'
            # Fetch existing sensors for pre-filling
            ammonia_sensor = restroom.sensors.filter(sensor_type='Ammonia').first()
            smoke_sensor = restroom.sensors.filter(sensor_type='Smoke').first()
            footfall_sensor = restroom.sensors.filter(sensor_type='Footfall').first()
        except Restroom.DoesNotExist:
             return redirect('restroom_list')

    if request.method == 'POST':
        try:
            name = request.POST.get('restroom_name')
            latitude = request.POST.get('latitude')
            longitude = request.POST.get('longitude')
            capacity = request.POST.get('capacity')
            status = request.POST.get('status')
            
            if mode == 'create':
                 # Create Restroom
                restroom = Restroom.objects.create(
                    restroom_id=f"R-{str(uuid.uuid4())[:8]}", 
                    name=name,
                    latitude=float(latitude),
                    longitude=float(longitude),
                    capacity=int(capacity),
                    status=status,
                    admin=request.user
                )
            else:
                 # Update Restroom
                restroom.name = name
                restroom.latitude = float(latitude)
                restroom.longitude = float(longitude)
                restroom.capacity = int(capacity)
                restroom.status = status
                restroom.save()

            # Link/Update Sensors
            sensor_map = {
                'sensor_ammonia': 'Ammonia',
                'sensor_smoke': 'Smoke',
                'sensor_footfall': 'Footfall'
            }
            
            for field, type_name in sensor_map.items():
                sid = request.POST.get(field)
                if sid:
                    sensor, created = Sensor.objects.get_or_create(
                        sensor_id=sid,
                        defaults={
                            'sensor_type': type_name, 
                            'restroom': restroom
                        }
                    )
                    if not created:
                        sensor.restroom = restroom
                        sensor.sensor_type = type_name 
                        sensor.save()
            
            return redirect('restroom_list')

        except Exception as e:
             # helpful for debugging if something goes wrong
             print(f"Error in activation: {e}")
             return render(request, 'landing/activation.html', {
                 'error': f'Error processing request: {e}',
                 'mode': mode,
                 'restroom': restroom,
                 'ammonia_sensor': ammonia_sensor,
                 'smoke_sensor': smoke_sensor,
                 'footfall_sensor': footfall_sensor
             })

    return render(request, 'landing/activation.html', {
        'mode': mode,
        'restroom': restroom,
        'ammonia_sensor': ammonia_sensor,
        'smoke_sensor': smoke_sensor,
        'footfall_sensor': footfall_sensor
    })

from datetime import datetime, timedelta
from django.utils import timezone
from django.db.models import Avg, Count
from django.db.models.functions import TruncDay, TruncHour

@login_required
def dashboard(request, restroom_id=None):
    try:
        if restroom_id:
            restroom = request.user.restrooms.get(restroom_id=restroom_id)
        else:
            restroom = request.user.restrooms.first()
            
        if not restroom:
            return redirect('activation')
    except Restroom.DoesNotExist:
         # If specific ID not found, fallback to first or list
         return redirect('restroom_list')
    except Exception:
        return redirect('activation')

    # Date Filter
    date_str = request.GET.get('date')
    if date_str:
        selected_date = datetime.strptime(date_str, '%Y-%m-%d').date()
    else:
        selected_date = timezone.now().date()

    # Sensors
    ammonia_sensor = restroom.sensors.filter(sensor_type='Ammonia').first()
    footfall_sensor = restroom.sensors.filter(sensor_type='Footfall').first()
    
    # 1. Ammonia Data (Today/Selected Date)
    ammonia_labels = []
    ammonia_data = []
    current_ammonia = 0
    ammonia_status = 'Normal'

    if ammonia_sensor:
        readings = ammonia_sensor.readings.filter(timestamp__date=selected_date).order_by('timestamp')
        ammonia_labels = [r.timestamp.strftime('%H:%M') for r in readings]
        ammonia_data = [r.value for r in readings]
        if readings.exists():
            current_ammonia = round(sum(ammonia_data) / len(ammonia_data), 1)
            if current_ammonia > 25:
                ammonia_status = 'Critical'

    # 2. Footfall Data (Daily - Hourly)
    footfall_daily_labels = []
    footfall_daily_data = []
    total_footfall_today = 0

    if footfall_sensor:
        # Mock aggregation: grouping by hour. Since mock data is sparse, we might need to be careful.
        # Ideally using TruncHour, but for simple mock data, let's just show readings if they are 'per event' or sum them if 'per interval'.
        # Our mock `populate_mock_data` created random values. Let's assume they are "counts reported every X minutes".
        daily_readings = footfall_sensor.readings.filter(timestamp__date=selected_date)
        total_footfall_today = int(sum([r.value for r in daily_readings]))
        
        # Aggregate by hour
        hourly_data = daily_readings.annotate(hour=TruncHour('timestamp')).values('hour').annotate(count=Count('id')).order_by('hour')
        # Actually effectively needed sum of 'value' if value is count.
        # Let's simple plot the raw values for now as mock data is "count per interval"
        footfall_daily_labels = [r.timestamp.strftime('%H:%M') for r in daily_readings]
        footfall_daily_data = [int(r.value) for r in daily_readings]

    # 3. Footfall Data (Monthly)
    footfall_monthly_labels = []
    footfall_monthly_data = []
    
    if footfall_sensor:
        end_date = timezone.now().date()
        start_date = end_date - timedelta(days=30)
        monthly_readings = footfall_sensor.readings.filter(timestamp__date__range=[start_date, end_date])
        
        # Aggregate by day
        # Note: SQLite handling of dates can be tricky with Django aggregation sometimes, but works mostly.
        # If this fails with strict database backends, we might need specific DB functions.
        # For simple prototype, let's iterate.
        daily_counts = {}
        for r in monthly_readings:
            day_str = r.timestamp.strftime('%d %b')
            daily_counts[day_str] = daily_counts.get(day_str, 0) + int(r.value)
        
        footfall_monthly_labels = list(daily_counts.keys())
        footfall_monthly_data = list(daily_counts.values())

    return render(request, 'landing/dashboard.html', {
        'restroom': restroom,
        'selected_date': selected_date.strftime('%Y-%m-%d'),
        'current_ammonia': current_ammonia,
        'ammonia_status': ammonia_status,
        'ammonia_labels': ammonia_labels,
        'ammonia_data': ammonia_data,
        'total_footfall_today': total_footfall_today,
        'footfall_daily_labels': footfall_daily_labels,
        'footfall_daily_data': footfall_daily_data,
        'footfall_monthly_labels': footfall_monthly_labels,
        'footfall_monthly_data': footfall_monthly_data,
        'page': 'overview',
    })

@login_required
def restroom_list(request):
    restrooms = request.user.restrooms.all()
    if not restrooms.exists():
        return redirect('activation')
        
    return render(request, 'landing/restroom_list.html', {
        'restrooms': restrooms,
        'page': 'restrooms'
    })

@login_required
def settings_view(request):
    return render(request, 'landing/settings.html', {'page': 'settings'})

@login_required
def staff_list(request, restroom_id=None):
    try:
        if restroom_id:
            restroom = request.user.restrooms.get(restroom_id=restroom_id)
        else:
            restroom = request.user.restrooms.first()
            
        if not restroom:
            return redirect('activation')
    except Restroom.DoesNotExist:
         return redirect('restroom_list')

    # Fetch staff
    staff_members = restroom.staff.all().order_by('-created_at')
    
    # Calculate status (mock logic: if within shift hours, they are 'On Duty')
    now_time = timezone.now().time()
    for staff in staff_members:
        # Simple check: start <= now <= end. Does not handle overnight shifts perfectly but sufficient for MVP.
        if staff.shift_start <= now_time <= staff.shift_end:
            staff.status = 'On Duty'
            staff.status_class = 'status-duty'
        else:
            staff.status = 'Offline'
            staff.status_class = 'status-offline'
            
        # Infer Department
        if 'Tech' in staff.role or 'Engineer' in staff.role:
            staff.department = 'Engineering'
        elif 'Admin' in staff.role:
            staff.department = 'Operations'
        elif 'Cleaner' in staff.role or 'Janitor' in staff.role:
            staff.department = 'Services'
        else:
            staff.department = 'General'

    return render(request, 'landing/staff_list.html', {
        'restroom': restroom,
        'staff_members': staff_members,
        'page': 'staff'
    })

@login_required
def add_staff(request, staff_id=None, restroom_id=None):
    
    # 1. Setup Defaults
    mode = 'create'
    staff = None
    restrooms = request.user.restrooms.all()
    selected_restroom_id = None

    # 2. Determine Mode: Edit vs Create
    if staff_id:
        # EDIT MODE: We are editing an existing employee
        mode = 'update'
        try:
            staff = Staff.objects.get(id=staff_id)
            selected_restroom_id = staff.restroom.restroom_id
        except Staff.DoesNotExist:
            return redirect('staff_list')
            
    elif restroom_id:
        # CREATE MODE (Pre-selected): We are adding new staff specifically for this restroom
        selected_restroom_id = restroom_id
    
    # (Optional fallback) Check GET parameters if not passed in URL
    if not selected_restroom_id:
        selected_restroom_id = request.GET.get('restroom_id')

    # 3. Handle Form Submission
    if request.method == 'POST':
        try:
            name = request.POST.get('name')
            email = request.POST.get('email')
            phone = request.POST.get('phone')
            role = request.POST.get('role')
            target_restroom_id = request.POST.get('restroom')
            shift_start = request.POST.get('shift_start')
            shift_end = request.POST.get('shift_end')
            
            # Get the assigned restroom object
            assigned_restroom = restrooms.get(restroom_id=target_restroom_id)

            if mode == 'create':
                # --- CREATE NEW STAFF ---
                nfc_placeholder = f"NFC-{uuid.uuid4().hex[:8].upper()}"
                Staff.objects.create(
                    name=name,
                    email=email,
                    phone=phone,
                    role=role,
                    restroom=assigned_restroom,
                    shift_start=shift_start,
                    shift_end=shift_end,
                    nfc_tag=nfc_placeholder
                )
            else:
                # --- UPDATE EXISTING STAFF ---
                staff.name = name
                staff.email = email
                staff.phone = phone
                staff.role = role
                staff.restroom = assigned_restroom
                staff.shift_start = shift_start
                staff.shift_end = shift_end
                staff.save()
            
            # Redirect to list
            return redirect('staff_list_with_id', restroom_id=assigned_restroom.restroom_id)

        except Exception as e:
            print(f"Error processing staff: {e}")
            return render(request, 'landing/add_staff.html', {
                'mode': mode,
                'staff': staff,
                'restrooms': restrooms,
                'selected_restroom_id': selected_restroom_id,
                'error': f"Error: {e}"
            })

    # 4. Render the Page (GET Request)
    return render(request, 'landing/add_staff.html', {
        'mode': mode,
        'staff': staff,
        'restrooms': restrooms,
        'selected_restroom_id': selected_restroom_id
    })



@login_required
def delete_staff(request, staff_id):
    if request.method == 'POST':
        try:
            staff = Staff.objects.get(id=staff_id)
            # Ensure the staff belongs to a restroom owned by the user
            if staff.restroom.admin == request.user:
                staff.delete()
        except Staff.DoesNotExist:
            pass
    
    # Redirect back to the previous page to maintain context (e.g., filters)
    referer = request.META.get('HTTP_REFERER')
    if referer:
        return redirect(referer)
    return redirect('staff_list')

@login_required
def delete_restroom(request, restroom_id):
    if request.method == 'POST':
        try:
            restroom = request.user.restrooms.get(restroom_id=restroom_id)
            restroom.delete()
        except Restroom.DoesNotExist:
            pass
    return redirect('restroom_list')

def admin_register(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email')
        password = request.POST.get('password')
        confirm_password = request.POST.get('confirm_password')

        if password != confirm_password:
            return render(request, 'landing/admin_register.html', {'error': 'Passwords do not match'})

        if User.objects.filter(username=username).exists():
            return render(request, 'landing/admin_register.html', {'error': 'Username already exists'})

        if User.objects.filter(email=email).exists():
            return render(request, 'landing/admin_register.html', {'error': 'Email already exists'})

        try:
            user = User.objects.create_user(username=username, email=email, password=password)
            user.is_staff = True
            user.save()
            # Redirect to login
            return redirect('login') 
        except Exception as e:
             return render(request, 'landing/admin_register.html', {'error': f'Error creating account: {e}'})

    return render(request, 'landing/admin_register.html')

from django.contrib.auth import authenticate, login
from django.contrib.auth.forms import AuthenticationForm

def login_view(request):
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            return redirect('dashboard')
    else:
        form = AuthenticationForm()
    
    return render(request, 'landing/login.html', {'form': form})

@login_required
def staff_logs(request, staff_id):
    try:
        staff = Staff.objects.get(id=staff_id)
        # Ensure user is admin of the restroom this staff belongs to
        if staff.restroom.admin != request.user:
             return redirect('staff_list')
    except Staff.DoesNotExist:
        return redirect('staff_list')

    # Calculate status
    now_time = timezone.now().time()
    # Simple check: start <= now <= end.
    if staff.shift_start <= now_time <= staff.shift_end:
        staff.status = 'On Duty'
    else:
        staff.status = 'Off Duty'

    # Date Filter
    date_str = request.GET.get('date')
    if date_str:
        selected_date = datetime.strptime(date_str, '%Y-%m-%d').date()
    else:
        # Default to today or None? Dashboard defaults to today, but logs might be better to default to all or today?
        # User said "work similar to dashboard", so default to today might be best, OR "Recent logs" implies all recent.
        # However, to filter by date usually implies showing a specific day.
        # Let's default to today to match Dashboard behavior exactly as requested.
        selected_date = timezone.now().date()

    # Fetch logs
    logs = CleaningActivity.objects.filter(staff=staff, start_time__date=selected_date).order_by('-start_time')
    
    # Calculate duration for display
    for log in logs:
        if log.end_time:
            duration = log.end_time - log.start_time
            log.duration_minutes = int(duration.total_seconds() / 60)
        else:
            log.duration_minutes = None

    return render(request, 'landing/staff_logs.html', {
        'staff': staff,
        'logs': logs,
        'selected_date': selected_date.strftime('%Y-%m-%d')
    })
