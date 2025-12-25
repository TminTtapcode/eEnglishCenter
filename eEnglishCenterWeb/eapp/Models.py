# eapp/Models.py (Code chuẩn Dynamic)
from sqlalchemy.orm import relationship
from eapp import db
from sqlalchemy import Column, Integer, String, Boolean, Float, Enum, ForeignKey, DateTime, Date, Index, \
    UniqueConstraint
from flask_login import UserMixin
from enum import Enum as UserEnum
from datetime import datetime


class UserRole(UserEnum):
    USER = 1;
    ADMIN = 2;
    TEACHER = 3;
    STAFF = 4


class BaseModel(db.Model):
    __abstract__ = True
    id = Column(Integer, primary_key=True, autoincrement=True)
    active = Column(Boolean, default=True)


class User(BaseModel, UserMixin):
    name = Column(String(50))
    email = Column(String(100))
    phone = Column(String(20), nullable=True)
    dob = Column(DateTime, nullable=True)
    avatar = Column(String(200),
                    default='https://res.cloudinary.com/dxxwcby8l/image/upload/v1647248722/r8sjly3st7estapvj19u.jpg')
    username = Column(String(50), nullable=False, unique=True)
    password = Column(String(50), nullable=False)
    user_role = Column(Enum(UserRole), default=UserRole.USER)

    receipts = relationship('Receipt', backref='user', lazy=True)
    grades = relationship('Grade', backref='student', lazy=True)
    attendance_records = relationship('Attendance', backref='student', lazy=True)

    def __str__(self): return self.name


class Category(BaseModel):
    name = Column(String(50), nullable=False, unique=True)
    courses = relationship('Course', backref='category', lazy=True)

    def __str__(self): return self.name


class Course(BaseModel):
    name = Column(String(50), nullable=False)
    description = Column(String(255), nullable=True)
    price = Column(Float, default=0)
    image = Column(String(200), nullable=True,
                   default='https://res.cloudinary.com/dxxwcby8l/image/upload/v1647248722/r8sjly3st7estapvj19u.jpg')
    category_id = Column(Integer, ForeignKey(Category.id), nullable=False)
    classes = relationship('Class', backref='course', lazy=True)

    def __str__(self): return self.name

class TimeSlot(BaseModel):
    name = Column(String(50), nullable=False)  # VD: "Ca Tối 2-4-6"

    # Lưu tách biệt để dễ tính toán trùng lịch
    days = Column(String(20), nullable=False)  # VD: "2-4-6"
    start_time = Column(Integer, nullable=False)  # VD: 19 (19h)
    end_time = Column(Integer, nullable=False)  # VD: 21 (21h)

    # Quan hệ
    classes = relationship('Class', backref='time_slot', lazy=True)

    def __str__(self):
        return f"{self.name} ({self.start_time}h - {self.end_time}h)"

class Class(BaseModel):
    name = Column(String(50), nullable=False)
    schedule = Column(String(100))
    max_students = Column(Integer, default=25)
    course_id = Column(Integer, ForeignKey(Course.id), nullable=False)
    is_finished = Column(Boolean, default=False)
    teacher_id = Column(Integer, ForeignKey(User.id), nullable=True)
    teacher = relationship('User', foreign_keys=[teacher_id], backref='classes_teaching', lazy=True)
    start_date = Column(Date, nullable=True)
    end_date = Column(Date, nullable=True)
    time_slot_id = Column(Integer, ForeignKey(TimeSlot.id), nullable=False)
    grade_columns = relationship('GradeColumn', backref='study_class', lazy=True)
    receipt_details = relationship('ReceiptDetails', backref='study_class', lazy=True)
    grades = relationship('Grade', backref='study_class', lazy=True)
    attendances = relationship('Attendance', backref='study_class', lazy=True)

    @property
    def current_students(self):
        return db.session.query(ReceiptDetails).join(Receipt).filter(ReceiptDetails.class_id == self.id,
                                                                     Receipt.is_paid == True).count()

    def __str__(self): return self.name


# --- HỆ THỐNG ĐIỂM ĐỘNG ---
class Grade(BaseModel):
    student_id = Column(Integer, ForeignKey(User.id), nullable=False)
    class_id = Column(Integer, ForeignKey(Class.id), nullable=False)
    final_average = Column(Float, default=0.0)
    scores = relationship('GradeScore', backref='grade_summary', lazy=True, cascade="all, delete")
    __table_args__ = (UniqueConstraint('student_id', 'class_id', name='unique_student_grade'),)

    @property
    def result(self): return "Đạt" if self.final_average >= 5.0 else "Không đạt"


class GradeColumn(BaseModel):
    name = Column(String(50), nullable=False)
    weight = Column(Integer, default=10)
    class_id = Column(Integer, ForeignKey(Class.id), nullable=False)
    scores = relationship('GradeScore', backref='column_info', lazy=True, cascade="all, delete")

    def __str__(self): return f"{self.name} ({self.weight}%)"


class GradeScore(BaseModel):
    grade_id = Column(Integer, ForeignKey(Grade.id), nullable=False)
    grade_column_id = Column(Integer, ForeignKey(GradeColumn.id), nullable=False)
    value = Column(Float, default=0.0)
    __table_args__ = (UniqueConstraint('grade_id', 'grade_column_id', name='unique_score_detail'),)


class Receipt(BaseModel):
    user_id = Column(Integer, ForeignKey(User.id), nullable=False)
    created_date = Column(DateTime, default=datetime.now)
    is_paid = Column(Boolean, default=False)
    details = relationship('ReceiptDetails', backref='receipt', lazy=True)

    @property
    def total_amount(self):
        # Tính tổng tiền từ các chi tiết hóa đơn
        return sum([d.price * d.quantity for d in self.details]) if self.details else 0

class ReceiptDetails(BaseModel):
    class_id = Column(Integer, ForeignKey(Class.id), nullable=False)
    receipt_id = Column(Integer, ForeignKey(Receipt.id), nullable=False)
    quantity = Column(Integer, default=1)
    price = Column(Float, default=0)


class Attendance(BaseModel):
    date = Column(Date, default=datetime.now)
    student_id = Column(Integer, ForeignKey(User.id), nullable=False)
    class_id = Column(Integer, ForeignKey(Class.id), nullable=False)
    present = Column(Boolean, default=True)
    __table_args__ = (Index('idx_class_date', 'class_id', 'date'),
                      UniqueConstraint('student_id', 'class_id', 'date', name='unique_attendance_record'),)


