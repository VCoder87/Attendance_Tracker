from django.urls import path
from .views import *

urlpatterns = [
    # Auth
    path('register/', RegisterTeacherView.as_view()),
    path('login/', LoginTeacherView.as_view()),
    path('logout/', LogoutTeacherView.as_view()),

    # Students
    path('students/add/', AddStudentView.as_view()),
    path('students/list/', ListStudentsView.as_view()),
    path('students/update/<str:roll_number>/', UpdateStudentView.as_view()),
    path('students/delete/<str:roll_number>/', DeleteStudentView.as_view()),


    # Attendance
    path('attendance/mark/<str:roll_number>/', MarkAttendanceView.as_view()),
    path('attendance/update/<str:roll_number>/', UpdateAttendanceView.as_view()),
    path('attendance/date/<str:date>/', AttendanceByDateView.as_view()),
    path('attendance/history/<str:roll_number>/', AttendanceHistoryView.as_view()),
    path('attendance/percentage/<str:roll_number>/', AttendancePercentageView.as_view()),
    path("token/refresh/", RefreshTokenView.as_view()),

]
