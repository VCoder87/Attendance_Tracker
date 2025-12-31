import json
import jwt
from datetime import datetime, timedelta

from django.views import View
from django.http import JsonResponse
from django.contrib.auth.models import User, Permission
from django.contrib.auth import authenticate
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator

from .models import Student, Attendance


# ================= JWT HELPERS =================

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
            algorithms=["HS256"]
        )

        if payload.get("type") != "access":
            return None

        user = User.objects.get(id=payload["user_id"])

        # 🔴 HARD REVOKE CHECK (GLOBAL)
        try:
            student = Student.objects.get(user=user)
            if not student.can_login:
                return None
        except Student.DoesNotExist:
            pass  # not a student

        return user

    except (jwt.ExpiredSignatureError, jwt.DecodeError, User.DoesNotExist):
        return None



# ================= AUTH =================

@method_decorator(csrf_exempt, name="dispatch")
class RegisterTeacherView(View):
    def post(self, request):
        admin = get_authenticated_user(request)
        if not admin or not admin.is_superuser:
            return JsonResponse({"error": "Admin access required"}, status=403)

        data = json.loads(request.body)

        user = User.objects.create_user(
            username=data["username"],
            password=data["password"]
        )

        permission_codenames = [
            "add_student",
            "change_student",
            "view_student",
            "mark_attendance",
            "update_attendance",
            "view_attendance",
            "view_attendance_report",
        ]

        permissions = Permission.objects.filter(codename__in=permission_codenames)
        user.user_permissions.set(permissions)

        return JsonResponse({"message": "Teacher registered successfully"})


@method_decorator(csrf_exempt, name="dispatch")
class LoginTeacherView(View):
    def post(self, request):
        data = json.loads(request.body)
        user = authenticate(username=data["username"], password=data["password"])

        if not user:
            return JsonResponse({"error": "Invalid credentials"}, status=401)

        return JsonResponse({
            "access_token": generate_access_token(user),
            "refresh_token": generate_refresh_token(user),
        })


@method_decorator(csrf_exempt, name="dispatch")
class RegisterStudentView(View):
    def post(self, request):
        admin = get_authenticated_user(request)
        if not admin or not admin.is_superuser:
            return JsonResponse({"error": "Admin access required"}, status=403)

        data = json.loads(request.body)

        teacher = User.objects.get(username=data["teacher_username"])
        user = User.objects.create_user(
            username=data["username"],
            password=data["password"]
        )

        Student.objects.create(
            user=user,
            teacher=teacher,
            name=data["name"],
            roll_number=data["roll_number"]
        )

        return JsonResponse({"message": "Student registered successfully"})


@method_decorator(csrf_exempt, name="dispatch")
class LoginStudentView(View):
    def post(self, request):
        data = json.loads(request.body)
        user = authenticate(
            username=data["username"],
            password=data["password"]
        )

        if not user:
            return JsonResponse(
                {"error": "Invalid credentials"},
                status=401
            )

        try:
            student = Student.objects.get(user=user)
        except Student.DoesNotExist:
            return JsonResponse(
                {"error": "Student profile not found"},
                status=403
            )

        # 🔴 HARD REVOKE CHECK
        if not student.can_login:
            return JsonResponse(
                {"error": "Permission denied"},
                status=403
            )

        return JsonResponse({
            "access_token": generate_access_token(user),
            "refresh_token": generate_refresh_token(user),
        })



@method_decorator(csrf_exempt, name="dispatch")
class LogoutTeacherView(View):
    def post(self, request):
        return JsonResponse({"message": "Logout successful. Delete token on client."})


# ================= STUDENTS =================

@method_decorator(csrf_exempt, name="dispatch")
class AddStudentView(View):
    def post(self, request):
        user = get_authenticated_user(request)
        if not user:
            return JsonResponse({"error": "Unauthorized"}, status=401)

        if not user.is_superuser:
            return JsonResponse({"error": "Admin only"}, status=403)

        data = json.loads(request.body)

        Student.objects.create(
            teacher=User.objects.get(username=data["teacher_username"]),
            name=data["name"],
            roll_number=data["roll_number"]
        )

        return JsonResponse({"message": "Student added"})


class ListStudentsView(View):
    def get(self, request):
        user = get_authenticated_user(request)
        if not user:
            return JsonResponse({"error": "Unauthorized"}, status=401)

        if user.is_superuser:
            students = Student.objects.all()
        else:
            students = Student.objects.filter(teacher=user)

        return JsonResponse(
            list(students.values("name", "roll_number")),
            safe=False
        )


@method_decorator(csrf_exempt, name="dispatch")
class DeleteStudentView(View):
    def delete(self, request, username):
        admin = get_authenticated_user(request)
        if not admin or not admin.is_superuser:
            return JsonResponse(
                {"error": "Admin access required"},
                status=403
            )

        try:
            user = User.objects.get(username=username)
            student = Student.objects.get(user=user)
        except User.DoesNotExist:
            return JsonResponse(
                {"error": "User not found"},
                status=404
            )
        except Student.DoesNotExist:
            return JsonResponse(
                {"error": "Student profile not found"},
                status=404
            )

        student.delete()
        user.delete()  # optional but recommended for cleanup

        return JsonResponse({
            "message": "Student deleted successfully"
        })


# ================= ATTENDANCE =================

@method_decorator(csrf_exempt, name="dispatch")
class MarkAttendanceView(View):
    def post(self, request, roll_number):
        user = get_authenticated_user(request)
        if not user:
            return JsonResponse({"error": "Unauthorized"}, status=401)

        if not user.is_superuser and not user.has_perm("attendance.mark_attendance"):
            return JsonResponse({"error": "Forbidden"}, status=403)
        # 🔴 BLOCK ATTENDANCE IF STUDENT REVOKED
        

        

        student = (
            Student.objects.get(roll_number=roll_number)
            if user.is_superuser
            else Student.objects.get(teacher=user, roll_number=roll_number)
        )
        if not student.can_login:
            return JsonResponse(
        {
            "error": "Student login access revoked. Attendance not allowed."
        },
        status=403
    )

        data = json.loads(request.body)

        Attendance.objects.create(
            student=student,
            date=data["date"],
            status=data["status"]
        )

        return JsonResponse({"message": "Attendance marked"})


class AttendanceByDateView(View):
    def get(self, request, date):
        user = get_authenticated_user(request)
        if not user:
            return JsonResponse({"error": "Unauthorized"}, status=401)

        if user.is_superuser:
            records = Attendance.objects.filter(date=date)
        elif hasattr(user, "student_profile"):
            records = Attendance.objects.filter(
                student=user.student_profile,
                date=date
            )
        else:
            records = Attendance.objects.filter(
                student__teacher=user,
                date=date
            )

        return JsonResponse([
            {
                "student": r.student.name,
                "roll_number": r.student.roll_number,
                "status": "Present" if r.status else "Absent"
            } for r in records
        ], safe=False)


class AttendanceHistoryView(View):
    def get(self, request):
        user = get_authenticated_user(request)
        if not user:
            return JsonResponse({"error": "Unauthorized"}, status=401)

        if user.is_superuser:
            records = Attendance.objects.all()
        elif hasattr(user, "student_profile"):
            records = Attendance.objects.filter(student=user.student_profile)
        else:
            records = Attendance.objects.filter(student__teacher=user)

        return JsonResponse([
            {
                "student": r.student.name,
                "roll_number": r.student.roll_number,
                "date": r.date,
                "status": r.status
            } for r in records
        ], safe=False)


class AttendancePercentageView(View):
    def get(self, request):
        user = get_authenticated_user(request)
        if not user:
            return JsonResponse({"error": "Unauthorized"}, status=401)

        # ADMIN
        if user.is_superuser:
            students = Student.objects.all()

            result = []
            for s in students:
                records = Attendance.objects.filter(student=s)
                total = records.count()
                present = records.filter(status=True).count()
                percentage = (present / total) * 100 if total else 0

                result.append({
                    "student_name": s.name,
                    "roll_number": s.roll_number,
                    "attendance_percentage": round(percentage, 2)
                })

            return JsonResponse(result, safe=False)

        # STUDENT (EXPLICIT DB CHECK)
        student_qs = Student.objects.filter(user=user)
        if student_qs.exists():
            student = student_qs.first()

            records = Attendance.objects.filter(student=student)
            total = records.count()
            present = records.filter(status=True).count()
            percentage = (present / total) * 100 if total else 0

            return JsonResponse({
                "student_name": student.name,
                "roll_number": student.roll_number,
                "attendance_percentage": round(percentage, 2)
            })

        # TEACHER
        students = Student.objects.filter(teacher=user)

        result = []
        for s in students:
            records = Attendance.objects.filter(student=s)
            total = records.count()
            present = records.filter(status=True).count()
            percentage = (present / total) * 100 if total else 0

            result.append({
                "student_name": s.name,
                "roll_number": s.roll_number,
                "attendance_percentage": round(percentage, 2)
            })

        return JsonResponse(result, safe=False)

@method_decorator(csrf_exempt, name="dispatch")
class RefreshTokenView(View):
    def post(self, request):
        data = json.loads(request.body)
        payload = jwt.decode(
            data["refresh_token"],
            settings.JWT_SECRET_KEY,
            algorithms=["HS256"]
        )

        user = User.objects.get(id=payload["user_id"])
        return JsonResponse({
            "access_token": generate_access_token(user)
        })
@method_decorator(csrf_exempt, name="dispatch")
class UpdateStudentView(View):
    def put(self, request, username):
        admin = get_authenticated_user(request)
        if not admin or not admin.is_superuser:
            return JsonResponse(
                {"error": "Admin access required"},
                status=403
            )

        try:
            user = User.objects.get(username=username)
            student = Student.objects.get(user=user)
        except User.DoesNotExist:
            return JsonResponse(
                {"error": "User not found"},
                status=404
            )
        except Student.DoesNotExist:
            return JsonResponse(
                {"error": "Student profile not found"},
                status=404
            )

        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse(
                {"error": "Invalid JSON"},
                status=400
            )

        # Allowed updates
        if "name" in data:
            student.name = data["name"]

        if "roll_number" in data:
            student.roll_number = data["roll_number"]

        if "teacher_username" in data:
            try:
                teacher = User.objects.get(
                    username=data["teacher_username"]
                )
                student.teacher = teacher
            except User.DoesNotExist:
                return JsonResponse(
                    {"error": "Teacher not found"},
                    status=404
                )

        # ❌ username is intentionally NOT editable

        student.save()

        return JsonResponse({
            "message": "Student details updated successfully"
        })
@method_decorator(csrf_exempt, name="dispatch")
class UpdateAttendanceView(View):
    def put(self, request, roll_number):
        user = get_authenticated_user(request)
        if not user:
            return JsonResponse({"error": "Unauthorized"}, status=401)

        # ❌ Students are NOT allowed
        if hasattr(user, "student_profile"):
            return JsonResponse(
                {"error": "Students cannot update attendance"},
                status=403
            )

        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse(
                {"error": "Invalid JSON"},
                status=400
            )

        if "date" not in data or "status" not in data:
            return JsonResponse(
                {"error": "date and status are required"},
                status=400
            )

        # ================= ADMIN =================
        if user.is_superuser:
            try:
                attendance = Attendance.objects.get(
                    student__roll_number=roll_number,
                    date=data["date"]
                )
            except Attendance.DoesNotExist:
                return JsonResponse(
                    {"error": "Attendance not found"},
                    status=404
                )

        # ================= TEACHER =================
        else:
            try:
                attendance = Attendance.objects.get(
                    student__teacher=user,
                    student__roll_number=roll_number,
                    date=data["date"]
                )
            except Attendance.DoesNotExist:
                return JsonResponse(
                    {"error": "Attendance not found or forbidden"},
                    status=404
                )

        attendance.status = data["status"]
        attendance.save()

        return JsonResponse({
            "message": "Attendance updated successfully"
        })



@method_decorator(csrf_exempt, name="dispatch")
class StudentLoginAccessView(View):
    def post(self, request):
        admin = get_authenticated_user(request)
        if not admin or not admin.is_superuser:
            return JsonResponse(
                {"error": "Admin access required"},
                status=403
            )

        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse(
                {"error": "Invalid JSON"},
                status=400
            )

        username = data.get("student_username")
        action = data.get("action")  # grant / revoke

        if not username or action not in ["grant", "revoke"]:
            return JsonResponse(
                {"error": "student_username and valid action required"},
                status=400
            )

        try:
            user = User.objects.get(username=username)
            student = Student.objects.get(user=user)
        except (User.DoesNotExist, Student.DoesNotExist):
            return JsonResponse(
                {"error": "Student not found"},
                status=404
            )

        if action == "grant":
            student.can_login = True
            message = "Student login access granted"
        else:
            student.can_login = False
            message = "Student login access revoked"

        student.save()

        return JsonResponse({"message": message})
