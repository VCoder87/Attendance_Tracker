# 🎓 Student Attendance Tracker – Django Backend

A **robust, backend-only Student Attendance Management System** built with **Django** and **PostgreSQL**, featuring **token-based authentication**, **secure teacher isolation**, and **roll-number-based student management**.

> 🚫 No Django REST Framework  
> 🚫 No HTML / Frontend  
> ✅ Pure Django backend  
> ✅ Token Authentication  
> ✅ Production-style architecture  

---

## ✨ Key Features

### 🔐 Authentication
- Teacher registration
- Teacher login with **authentication token**
- Token-based authorization for all protected APIs
- Logout by invalidating token

### 👨‍🎓 Student Management
- Add students (unique roll number per teacher)
- Update student details
- Delete students
- List students for the authenticated teacher only

### 📝 Attendance Management
- Mark attendance (Present / Absent)
- Update attendance records
- View attendance by date
- View attendance history per student
- Calculate attendance percentage

### 🛡️ Security & Data Integrity
- Stateless token-based authentication
- Strict teacher-student data isolation
- Database-level uniqueness constraints
- Clean error handling for conflicts and invalid access

---

## 🛠️ Tech Stack

| Technology | Usage |
|-----------|------|
| Python 3.x | Backend language |
| Django | Web framework |
| PostgreSQL | Relational database |
| psycopg2 | PostgreSQL adapter |
| Postman | API testing |

## How to Run
```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python manage.py makemigrations
python manage.py migrate
python manage.py runserver