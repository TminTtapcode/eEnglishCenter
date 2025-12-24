import random
import hashlib
from datetime import datetime, timedelta
from sqlalchemy import create_engine, text
from eapp import app, db
# Import đầy đủ các Model
from eapp.Models import User, Category, Course, Class, UserRole, Grade, GradeColumn, GradeScore, Receipt, \
    ReceiptDetails, Attendance,TimeSlot

# 1. CẤU HÌNH
DB_URI = app.config["SQLALCHEMY_DATABASE_URI"]

# Danh sách ảnh đẹp cho khóa học
IMAGES = {
    'Beginner': [
        "https://images.unsplash.com/photo-1546410531-bb4caa6b424d?w=800",  # Sách vở
        "https://images.unsplash.com/photo-1456513080510-7bf3a84b82f8?w=800",  # Học tập
        "https://images.unsplash.com/photo-1503676260728-1c00da094a0b?w=800"  # Bút viết
    ],
    'Intermediate': [
        "https://images.unsplash.com/photo-1523240795612-9a054b0db644?w=800",  # Nhóm bạn
        "https://images.unsplash.com/photo-1524178232363-1fb2b075b655?w=800",  # Lớp học
        "https://images.unsplash.com/photo-1513258496098-882605922721?w=800"  # Bảng đen
    ],
    'Advanced': [
        "https://images.unsplash.com/photo-1522202176988-66273c2fd55f?w=800",  # Họp nhóm
        "https://images.unsplash.com/photo-1517048676732-d65bc937f952?w=800",  # Hội thảo
        "https://images.unsplash.com/photo-1552664730-d307ca884978?w=800"  # Teamwork
    ]
}

HO = ["Nguyễn", "Trần", "Lê", "Phạm", "Hoàng", "Huỳnh", "Phan", "Vũ", "Võ", "Đặng"]
TEN_LOT = ["Văn", "Thị", "Đức", "Minh", "Ngọc", "Thanh", "Quang", "Hữu", "Xuân"]
TEN = ["Hùng", "Lan", "Dũng", "Tâm", "Huệ", "Cường", "Trang", "Mai", "Phúc", "Linh", "Huy"]


def generate_name():
    return f"{random.choice(HO)} {random.choice(TEN_LOT)} {random.choice(TEN)}"


# 2. HÀM DỌN DẸP DB CŨ
def clean_database():
    print("🧹 Đang dọn dẹp database cũ...")
    engine = create_engine(DB_URI)
    with engine.connect() as conn:
        conn.execute(text("SET FOREIGN_KEY_CHECKS = 0"))
        conn.commit()
        # Xóa tất cả các bảng liên quan
        tables = ['grade_score', 'grade_column', 'grade_structure', 'grade',
                  'attendance', 'receipt_details', 'receipt',
                  'class', 'course', 'category', 'user']
        for t in tables:
            conn.execute(text(f"DROP TABLE IF EXISTS {t}"))

        conn.execute(text("SET FOREIGN_KEY_CHECKS = 1"))
        conn.commit()


# 3. HÀM TẠO DỮ LIỆU
def init_data():
    print("🚀 Đang khởi tạo dữ liệu mới...")
    with app.app_context():
        db.create_all()

        pw = hashlib.md5("123456".encode('utf-8')).hexdigest()

        # --- Tạo Staff ---
        admin = User(name='Super Admin', username='admin', password=pw, user_role=UserRole.ADMIN)
        teachers = [
            User(name='Ms. Lan Anh', username='teacher1', password=pw, user_role=UserRole.TEACHER),
            User(name='Mr. David M.', username='teacher2', password=pw, user_role=UserRole.TEACHER)
        ]
        db.session.add(admin)
        db.session.add_all(teachers)
        db.session.commit()
        slots = [
            TimeSlot(name="Sáng 2-4-6", days="2-4-6", start_time=8, end_time=10),
            TimeSlot(name="Tối 3-5-7", days="3-5-7", start_time=19, end_time=21),
            TimeSlot(name="Cuối Tuần", days="7-8", start_time=8, end_time=11)  # 8 là CN
        ]
        db.session.add_all(slots)
        db.session.commit()
        # --- Tạo 100 User ---
        users = []
        for i in range(1, 101):
            u = User(name=generate_name(), username=f'user{i}', password=pw,
                     email=f'user{i}@gmail.com', user_role=UserRole.USER)
            users.append(u)
        db.session.add_all(users)
        db.session.commit()
        print(f"   - Đã tạo 100 học viên.")

        # --- Tạo Danh mục & Khóa học & Lớp ---
        structure = {
            'Beginner': ['Tiếng Anh Mất Gốc', 'Phát Âm Cơ Bản', 'Từ Vựng Sơ Cấp'],
            'Intermediate': ['Giao Tiếp Phản Xạ', 'Ngữ Pháp Nâng Cao', 'Luyện Nghe Nói'],
            'Advanced': ['IELTS Master', 'Tiếng Anh Thương Mại', 'Biên Phiên Dịch']
        }

        all_classes = []

        for cat_name, courses in structure.items():
            cat = Category(name=cat_name)
            db.session.add(cat)
            db.session.commit()

            for idx, c_name in enumerate(courses):
                # Chọn ảnh
                img_url = IMAGES[cat_name][idx % 3]
                price = random.randint(10, 50) * 100000  # Giá từ 1tr - 5tr

                course = Course(name=c_name, price=price, category_id=cat.id, image=img_url,
                                description=f"Khóa học {c_name} chất lượng cao, cam kết đầu ra.")
                db.session.add(course)
                db.session.commit()

                # Tạo 1-2 lớp cho mỗi khóa
                for k in range(random.randint(1, 2)):
                    teacher = random.choice(teachers)
                    start_date = datetime.now().date() + timedelta(days=random.randint(-30, 30))

                    cls = Class(name=f"{c_name} - Lớp {k + 1}",
                                schedule=random.choice(['2-4-6 (19h-21h)', '3-5-7 (18h-20h)']),
                                max_students=20, course_id=course.id,
                                teacher_id=teacher.id, start_date=start_date,
                                time_slot_id=slots[0].id)
                    db.session.add(cls)
                    db.session.commit()
                    all_classes.append(cls)

                    # Tạo Cấu trúc điểm (Dynamic)
                    cols = [
                        GradeColumn(name='Chuyên cần', weight=10, class_id=cls.id),
                        GradeColumn(name='Giữa kỳ', weight=30, class_id=cls.id),
                        GradeColumn(name='Cuối kỳ', weight=60, class_id=cls.id)
                    ]
                    db.session.add_all(cols)

        db.session.commit()

        # --- Xử lý Lớp FULL chỗ ---
        # Lấy lớp đầu tiên làm lớp Full
        full_class = all_classes[0]
        full_class.name = f"{full_class.name} (FULL)"
        full_class.max_students = 10
        db.session.add(full_class)
        db.session.commit()

        print(f"   - Tạo lớp FULL: {full_class.name}")

        # Đăng ký 10 người vào lớp Full
        for i in range(10):
            enroll(users[i], full_class)

        # --- Đăng ký ngẫu nhiên cho các lớp còn lại ---
        # 90 user còn lại, mỗi người học random 0-2 lớp
        remaining_users = users[10:]
        remaining_classes = all_classes[1:]

        for u in remaining_users:
            if random.random() > 0.3:  # 70% có đi học
                # Chọn ngẫu nhiên 1 lớp
                cls = random.choice(remaining_classes)
                enroll(u, cls)

        print("✅ KHỞI TẠO THÀNH CÔNG! (Admin: admin / 123456)")


def enroll(user, cls):
    """Hàm đăng ký học và nhập điểm giả"""
    try:
        # Tạo hóa đơn
        r = Receipt(user_id=user.id, is_paid=True)
        db.session.add(r)
        db.session.commit()
        db.session.add(ReceiptDetails(receipt_id=r.id, class_id=cls.id, price=cls.course.price))

        # Tạo bảng điểm
        g = Grade(student_id=user.id, class_id=cls.id)
        db.session.add(g)
        db.session.commit()

        # Nhập điểm chi tiết
        cols = GradeColumn.query.filter_by(class_id=cls.id).all()
        total, total_w = 0, 0
        for col in cols:
            val = round(random.uniform(5.0, 9.5), 1)
            db.session.add(GradeScore(grade_id=g.id, grade_column_id=col.id, value=val))
            total += val * col.weight
            total_w += col.weight

        # Tính điểm tổng
        if total_w > 0:
            g.final_average = round(total / total_w * 10, 1)  # Quy về thang 10
            # Hoặc nếu nhập weight là 30, 70 thì chia 100
            g.final_average = round(total / 100, 1)

        db.session.commit()
    except Exception:
        db.session.rollback()


if __name__ == '__main__':
    clean_database()
    init_data()