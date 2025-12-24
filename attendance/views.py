import json
import jwt
from datetime import datetime, timedelta

from django.views import View
from django.http import JsonResponse
from django.contrib.auth.models import User
from django.contrib.auth import authenticate
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator

from .models import Student, Attendance

def generate_access_token(user):
    payload = {
        "user_id": user.id,
        "username": user.username,
        "type": "access",
        "iat": datetime.utcnow(),
        "exp": datetime.utcnow() + timedelta(hours=1),
    }
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm="HS256")


def generate_refresh_token(user):
    payload = {
        "user_id": user.id,
        "type": "refresh",
        "iat": datetime.utcnow(),
        "exp": datetime.utcnow() + timedelta(days=7),
    }
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm="HS256")


def get_authenticated_user(request):
    auth_header = request.headers.get("Authorization")

    if not auth_header or not auth_header.startswith("Bearer "):
        return None

    token = auth_header.split(" ")[1]

    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=["HS256"],
        )

        if payload.get("type") != "access":
            return None

        return User.objects.get(id=payload["user_id"])

    except (jwt.ExpiredSignatureError, jwt.DecodeError, User.DoesNotExist):
        return None

@method_decorator(csrf_exempt, name="dispatch")
class RegisterTeacherView(View):
    def post(self, request):
        data = json.loads(request.body)

        User.objects.create_user(
            username=data["username"],
            password=data["password"],
        )

        return JsonResponse({"message": "Teacher registered successfully"})

@method_decorator(csrf_exempt, name="dispatch")
class LoginTeacherView(View):
    def post(self, request):
        data = json.loads(request.body)

        user = authenticate(
            username=data["username"],
            password=data["password"],
        )

        if not user:
            return JsonResponse({"error": "Invalid credentials"}, status=401)

        return JsonResponse({
            "access_token": generate_access_token(user),
            "refresh_token": generate_refresh_token(user),
        })


@method_decorator(csrf_exempt, name="dispatch")
class RefreshTokenView(View):
    def post(self, request):
        data = json.loads(request.body)
        refresh_token = data.get("refresh_token")

        try:
            payload = jwt.decode(
                refresh_token,
                settings.JWT_SECRET_KEY,
                algorithms=["HS256"],
            )

            if payload.get("type") != "refresh":
                return JsonResponse({"error": "Invalid token"}, status=401)

            user = User.objects.get(id=payload["user_id"])

            return JsonResponse({
                "access_token": generate_access_token(user)
            })

        except (jwt.ExpiredSignatureError, jwt.DecodeError, User.DoesNotExist):
            return JsonResponse(
                {"error": "Invalid or expired refresh token"},
                status=401,
            )

@method_decorator(csrf_exempt, name="dispatch")
class LogoutTeacherView(View):
    def post(self, request):
        return JsonResponse({
            "message": "Logout successful. Delete token on client."
        })

@method_decorator(csrf_exempt, name="dispatch")
class AddStudentView(View):
    def post(self, request):
        user = get_authenticated_user(request)
        if not user:
            return JsonResponse({"error": "Unauthorized"}, status=401)

        data = json.loads(request.body)

        Student.objects.create(
            teacher=user,
            name=data["name"],
            roll_number=data["roll_number"],
        )

        return JsonResponse({"message": "Student added"})

class ListStudentsView(View):
    def get(self, request):
        user = get_authenticated_user(request)
        if not user:
            return JsonResponse({"error": "Unauthorized"}, status=401)

        students = Student.objects.filter(teacher=user)
        return JsonResponse(
            list(students.values("name", "roll_number")),
            safe=False,
        )




@method_decorator(csrf_exempt, name="dispatch")
class UpdateStudentView(View):
    def put(self, request, roll_number):
        user = get_authenticated_user(request)
        if not user:
            return JsonResponse({"error": "Unauthorized"}, status=401)

        data = json.loads(request.body)

        try:
            student = Student.objects.get(
                teacher=user,
                roll_number=roll_number,
            )
        except Student.DoesNotExist:
            return JsonResponse({"error": "Student not found"}, status=404)

        student.name = data["name"]
        student.save()

        return JsonResponse({"message": "Student updated"})

@method_decorator(csrf_exempt, name="dispatch")
class DeleteStudentView(View):
    def delete(self, request, roll_number):
        user = get_authenticated_user(request)
        if not user:
            return JsonResponse({"error": "Unauthorized"}, status=401)

        try:
            student = Student.objects.get(
                teacher=user,
                roll_number=roll_number,
            )
        except Student.DoesNotExist:
            return JsonResponse({"error": "Student not found"}, status=404)

        student.delete()
        return JsonResponse({"message": "Student deleted"})


@method_decorator(csrf_exempt, name='dispatch')
class MarkAttendanceView(View):
    def post(self, request, roll_number):
        user = get_authenticated_user(request)
        if not user:
            return JsonResponse({"error": "Unauthorized"}, status=401)

        data = json.loads(request.body)

        try:
            student = Student.objects.get(
                teacher=user,
                roll_number=roll_number
            )
        except Student.DoesNotExist:
            return JsonResponse({"error": "Student not found"}, status=404)

        Attendance.objects.create(
            student=student,
            date=data['date'],
            status=data['status']
        )

        return JsonResponse({"message": "Attendance marked"})


@method_decorator(csrf_exempt, name='dispatch')
class UpdateAttendanceView(View):
    def put(self, request, roll_number):
        user = get_authenticated_user(request)
        if not user:
            return JsonResponse({"error": "Unauthorized"}, status=401)

        data = json.loads(request.body)

        try:
            attendance = Attendance.objects.get(
                student__teacher=user,
                student__roll_number=roll_number,
                date=data['date']
            )
        except Attendance.DoesNotExist:
            return JsonResponse({"error": "Attendance not found"}, status=404)

        attendance.status = data['status']
        attendance.save()

        return JsonResponse({"message": "Attendance updated"})


class AttendanceByDateView(View):
    def get(self, request, date):
        user = get_authenticated_user(request)
        if not user:
            return JsonResponse({"error": "Unauthorized"}, status=401)

        records = Attendance.objects.filter(
            student__teacher=user,
            date=date
        )

        data = [
            {
                "student": r.student.name,
                "roll_number": r.student.roll_number,
                "status": "Present" if r.status else "Absent"
            }
            for r in records
        ]

        return JsonResponse(data, safe=False)


class AttendanceHistoryView(View):
    def get(self, request, roll_number):
        user = get_authenticated_user(request)
        if not user:
            return JsonResponse({"error": "Unauthorized"}, status=401)

        records = Attendance.objects.filter(
            student__teacher=user,
            student__roll_number=roll_number
        )

        return JsonResponse(
            [{"date": r.date, "status": r.status} for r in records],
            safe=False
        )


class AttendancePercentageView(View):
    def get(self, request, roll_number):
        user = get_authenticated_user(request)
        if not user:
            return JsonResponse({"error": "Unauthorized"}, status=401)

        records = Attendance.objects.filter(
            student__teacher=user,
            student__roll_number=roll_number
        )

        total = records.count()
        present = records.filter(status=True).count()

        percentage = (present / total) * 100 if total else 0

        return JsonResponse({
            "roll_number": roll_number,
            "attendance_percentage": percentage
        })

