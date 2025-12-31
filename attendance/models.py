from django.db import models
from django.contrib.auth.models import User


class Student(models.Model):
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="student_profile",
        null=True,
        blank=True
    )
    teacher = models.ForeignKey(User, on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    roll_number = models.CharField(max_length=20)

    # 🔴 NEW FIELD (IMPORTANT)
    can_login = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)


    class Meta:
        unique_together = ("teacher", "roll_number")

    def __str__(self):
        return self.name


class Attendance(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    date = models.DateField()
    status = models.BooleanField()  # True = Present, False = Absent

    class Meta:
        unique_together = ("student", "date")
        permissions = [
            ("mark_attendance", "Can mark attendance"),
            ("update_attendance", "Can update attendance"),
            ("view_attendance_report", "Can view attendance reports"),
        ]
