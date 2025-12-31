from django.urls import path
from .views import *

urlpatterns = [
    # Auth
    path("register/", RegisterTeacherView.as_view()),
    path("login/", LoginTeacherView.as_view()),
    path("logout/", LogoutTeacherView.as_view()),
    path("token/refresh/", RefreshTokenView.as_view()),

    # Student Auth
    path("student/register/", RegisterStudentView.as_view()),
    path("student/login/", LoginStudentView.as_view()),

    # Students
    path("students/add/", AddStudentView.as_view()),
    path("students/list/", ListStudentsView.as_view()),
    path("students/delete/<str:username>/", DeleteStudentView.as_view()),
    path("students/update/<str:username>/", UpdateStudentView.as_view()),


    # Attendance
    path("attendance/mark/<str:roll_number>/", MarkAttendanceView.as_view()),
    path("attendance/update/<str:roll_number>/", UpdateAttendanceView.as_view()),
    path("attendance/date/<str:date>/", AttendanceByDateView.as_view()),
    path("attendance/history/", AttendanceHistoryView.as_view()),
    path("attendance/percentage/", AttendancePercentageView.as_view()),
    path(
    "students/login-access/",
    StudentLoginAccessView.as_view()
),

]
