# eapp/admin.py (Copy đè toàn bộ)
from flask import request, jsonify, url_for, flash, redirect
from markupsafe import Markup
from flask_admin import Admin, BaseView, expose, AdminIndexView
from flask_admin.contrib.sqla import ModelView
from flask_admin.actions import action
from flask_login import current_user, logout_user
from datetime import datetime
from eapp.Models import Course, UserRole, Category, User, Class, Grade, Attendance, GradeColumn, GradeScore, TimeSlot
from eapp import app, db, dao
from sqlalchemy import func


class AdminView(ModelView):
    def is_accessible(self): return current_user.is_authenticated and current_user.user_role == UserRole.ADMIN

class TeacherBaseView(BaseView):
    def is_accessible(self):
        # Cho phép nếu đã đăng nhập VÀ (là Admin HOẶC là Teacher)
        return current_user.is_authenticated and \
               (current_user.user_role == UserRole.ADMIN or current_user.user_role == UserRole.TEACHER)

class LogOutView(BaseView):
    @expose('/')
    def index(self): logout_user(); return redirect('/admin')

    def is_accessible(self): return current_user.is_authenticated


class BackHomeView(BaseView):
    @expose('/')
    def index(self): return redirect('/')

    def is_accessible(self): return current_user.is_authenticated


class CourseView(AdminView):
    column_list = ['id', 'name', 'price', 'active', 'category']
    column_searchable_list = ['name']
    column_editable_list = ['name', 'price', 'active']


# VIEW LỚP HỌC (Tự động tạo cột điểm)
class ClassView(AdminView):
    column_list = ['name', 'course', 'teacher', 'time_slot', 'max_students', 'start_date', 'is_finished']
    column_labels = {
        'name': 'Tên Lớp',
        'course': 'Khóa Học',
        'teacher': 'Giáo Viên',
        'time_slot': 'Ca Học',  # Hiển thị "Ca Học" thay vì "Time Slot"
        'max_students': 'Sĩ Số',
        'start_date': 'Ngày Khai Giảng',
        'is_finished': 'Đã Kết Thúc'
    }
    column_editable_list = ['name', 'start_date']

    form_excluded_columns = ['is_finished', 'receipt_details', 'grades', 'attendances', 'grade_columns']

    def on_model_change(self, form, model, is_created):
        if is_created:  # Tự tạo 3 cột mặc định
            db.session.add_all([
                GradeColumn(name='Chuyên cần', weight=10, study_class=model),
                GradeColumn(name='Giữa kỳ', weight=30, study_class=model),
                GradeColumn(name='Cuối kỳ', weight=60, study_class=model)
            ])

    @action('clone_class', 'Nhân Bản Lớp', 'Copy cấu hình?')
    def action_clone(self, ids):
        try:
            for cid in ids:
                old = Class.query.get(cid)
                new_c = Class(name=f"{old.name} (Copy)", schedule=old.schedule, max_students=old.max_students,
                              course_id=old.course_id, teacher_id=old.teacher_id, start_date=datetime.now().date())
                db.session.add(new_c);
                db.session.flush()
                for col in old.grade_columns:  # Copy cấu trúc điểm
                    db.session.add(GradeColumn(name=col.name, weight=col.weight, class_id=new_c.id))
            db.session.commit()
            flash('Đã nhân bản thành công!', 'success')
        except Exception as e:
            db.session.rollback(); flash(str(e), 'error')

    @action('close_class', 'Kết Thúc', 'Chốt lớp?')
    def action_close(self, ids):
        for cid in ids: Class.query.get(cid).is_finished = True
        db.session.commit()
        flash('Đã khóa lớp!', 'success')


class GradeColumnView(AdminView):
    column_list = ['study_class', 'name', 'weight']
    column_editable_list = ['name', 'weight']
    column_filters = ['class_id']

    def get_query(self):
        q = super(GradeColumnView, self).get_query()
        if current_user.user_role == UserRole.TEACHER: q = q.join(Class).filter(Class.teacher_id == current_user.id)
        return q


class ReceiptView(AdminView):
    def is_accessible(self):
        # Cho phép ADMIN và CASHIER (Thu ngân) truy cập
        return current_user.is_authenticated and \
            (current_user.user_role == UserRole.ADMIN or current_user.user_role == UserRole.CASHIER)

    column_list = ['id', 'user', 'created_date', 'total_amount', 'is_paid']
    column_labels = {
        'id': 'Mã HĐ',
        'user': 'Học viên',
        'created_date': 'Ngày lập',
        'total_amount': 'Tổng tiền (VNĐ)',
        'is_paid': 'Đã thanh toán'
    }
    column_filters = ['is_paid', 'created_date', 'user.name']

    can_create = False  # Hóa đơn sinh ra tự động, không tạo tay
    can_edit = True
    column_editable_list = ['is_paid']  # Cho phép Thu ngân tick nhanh vào đây khi nhận tiền

    def _format_money(view, context, model, name):
        return "{:,.0f}".format(model.total_amount)

    column_formatters = {
        'total_amount': _format_money
    }

# --- ĐÂY LÀ VIEW QUAN TRỌNG NHẤT: NHẬP ĐIỂM DYNAMIC ---
class GradeManagerView(TeacherBaseView):
    @expose('/')
    def index(self):
        class_id = request.args.get('class_id')
        chosen_class, columns, rows = None, [], []

        # 1. Lấy danh sách lớp để lọc
        classes = Class.query.all() if current_user.user_role == UserRole.ADMIN else Class.query.filter(
            Class.teacher_id == current_user.id).all()

        if class_id:
            chosen_class = Class.query.get(class_id)
            if chosen_class:
                # 2. Lấy các cột điểm của lớp này (Dynamic)
                columns = GradeColumn.query.filter_by(class_id=class_id).all()

                # 3. Lấy danh sách sinh viên và điểm số của họ
                grades = Grade.query.filter_by(class_id=class_id).all()

                for g in grades:
                    # Tạo cấu trúc dữ liệu cho mỗi dòng sinh viên
                    row = {
                        'student_name': g.student.name,
                        'student_code': g.student.username,
                        'grade_id': g.id,
                        'final': g.final_average,
                        'result': g.result,
                        'scores': {}
                    }
                    # Lấy điểm chi tiết
                    details = GradeScore.query.filter_by(grade_id=g.id).all()
                    for s in details:
                        row['scores'][s.grade_column_id] = s.value  # Map: id cột -> điểm

                    rows.append(row)

        return self.render('admin/grade_matrix.html', classes=classes, chosen_class=chosen_class, columns=columns,
                           rows=rows)

    @expose('/update', methods=['POST'])
    def update(self):
        try:
            d = request.json
            grade_id = d.get('grade_id')
            col_id = d.get('column_id')
            val = float(d.get('value'))

            # 1. Lưu điểm chi tiết
            score = GradeScore.query.filter_by(grade_id=grade_id, grade_column_id=col_id).first()
            if score:
                score.value = val
            else:
                db.session.add(GradeScore(grade_id=grade_id, grade_column_id=col_id, value=val))
            db.session.commit()

            # 2. Tính lại trung bình ngay lập tức
            self.recalculate(grade_id)

            # 3. Trả về kết quả mới
            g = Grade.query.get(grade_id)
            return jsonify({'status': 'success', 'new_avg': g.final_average, 'new_res': g.result})
        except Exception as e:
            return jsonify({'status': 'error', 'msg': str(e)})

    def recalculate(self, grade_id):
        # 1. Lấy tất cả điểm của sinh viên này
        scores = GradeScore.query.filter_by(grade_id=grade_id).all()

        total_score_weighted = 0  # Tổng điểm nhân hệ số
        total_weight = 0  # Tổng trọng số thực tế

        for s in scores:
            w = s.column_info.weight  # Lấy trọng số của cột (VD: 10, 30, 60...)

            # Chỉ tính những cột đã có điểm (nếu muốn bỏ qua cột chưa nhập)
            # Hoặc tính tất cả (coi như 0 điểm). Ở đây mình tính tất cả.
            total_score_weighted += s.value * w
            total_weight += w

        g = Grade.query.get(grade_id)

        # --- ĐÂY LÀ DÒNG QUAN TRỌNG NHẤT ---
        # Cũ: Chia cho 100 (Cứng nhắc, lỗi nếu tổng > 100)
        # g.final_average = round(total_score_weighted / 100, 1)

        # Mới: Chia cho tổng trọng số thực tế (Linh hoạt)
        if total_weight > 0:
            g.final_average = round(total_score_weighted / total_weight, 2)
        else:
            g.final_average = 0.0

        db.session.commit()


class AttendanceManagerView(TeacherBaseView):
    @expose('/')
    def index(self):
        class_id, date_str = request.args.get('class_id'), request.args.get('date', str(datetime.now().date()))
        chosen, students, att_map = None, [], {}
        classes = Class.query.all() if current_user.user_role == UserRole.ADMIN else Class.query.filter(
            Class.teacher_id == current_user.id).all()
        if class_id:
            chosen = Class.query.get(class_id)
            students = User.query.join(Grade).filter(Grade.class_id == class_id).all()
            for r in Attendance.query.filter_by(class_id=class_id, date=date_str).all(): att_map[
                r.student_id] = r.present
        return self.render('admin/attendance.html', classes=classes, chosen_class=chosen, students=students,
                           today=date_str, att_map=att_map)

    @expose('/save', methods=['POST'])
    def save(self):
        cid, d_str = request.form.get('class_id'), request.form.get('date')
        if Class.query.get(cid).is_finished: return redirect(url_for('attendance.index', class_id=cid, date=d_str))
        for s in User.query.join(Grade).filter(Grade.class_id == cid).all():
            p = request.form.get(f'present_{s.id}') == 'on'
            att = Attendance.query.filter_by(class_id=cid, student_id=s.id, date=d_str).first()
            if att:
                att.present = p
            else:
                db.session.add(Attendance(class_id=cid, student_id=s.id, date=d_str, present=p))
        db.session.commit()
        return redirect(url_for('attendance.index', class_id=cid, date=d_str))


# eapp/admin.py

class StatsView(BaseView):
    @expose('/')
    def index(self):
        year_str = request.args.get('year')
        month_str = request.args.get('month')

        current_year = datetime.now().year
        selected_year = int(year_str) if year_str and year_str.isdigit() else current_year
        selected_month = int(month_str) if month_str and month_str.isdigit() else None

        return self.render('admin/stats.html',
                           # Doanh thu: Luôn xem theo Năm (để vẽ đủ 12 tháng)
                           revenue_time=dao.stats_revenue_style_time(year=selected_year),

                           # Học viên: Lọc theo Năm + Tháng (Đã có từ trước)
                           student_stats=dao.stats_student_count_by_course(year=selected_year, month=selected_month),

                           # Tỷ lệ đạt: Lọc theo Năm + Tháng (MỚI SỬA)
                           pass_stats=dao.stats_pass_rate_by_course(year=selected_year, month=selected_month),

                           available_years=dao.get_revenue_years(),
                           selected_year=selected_year,
                           selected_month=selected_month)

    def is_accessible(self):
        return current_user.is_authenticated and current_user.user_role == UserRole.ADMIN

class TimeSlotView(AdminView):
    column_list = ['name', 'days', 'start_time', 'end_time']
    column_labels = {'name': 'Tên Ca', 'days': 'Thứ', 'start_time': 'Giờ BĐ', 'end_time': 'Giờ KT'}
    column_editable_list = ['name', 'days', 'start_time', 'end_time']

    # Validate không cho nhập giờ sai (VD: Bắt đầu 25h)
    def on_model_change(self, form, model, is_created):
        if model.start_time >= model.end_time:
            raise Exception('Giờ bắt đầu phải nhỏ hơn giờ kết thúc!')

class MyAdmin(AdminIndexView):
    @expose('/')
    def index(self): return self.render('admin/index.html', course_count=dao.count_course_by_cate())


admin = Admin(app=app, name='Trung Tâm Ngoại Ngữ', index_view=MyAdmin())
admin.add_view(CourseView(Course, db.session, name='Khóa học'))
admin.add_view(AdminView(Category, db.session, name='Danh mục'))
admin.add_view(ClassView(Class, db.session, name='Lớp học', endpoint='class_manager'))
admin.add_view(AdminView(User, db.session, name='Người dùng'))
# 3 VIEW QUAN TRỌNG:
admin.add_view(GradeManagerView(name='Quản Lý Điểm', endpoint='grade_manager'))  # <-- View nhập điểm ma trận
admin.add_view(GradeColumnView(GradeColumn, db.session, name='Cấu Hình Cột Điểm'))  # <-- Để thêm cột tùy ý
admin.add_view(AttendanceManagerView(name='Điểm Danh', endpoint='attendance'))
admin.add_view(TimeSlotView(TimeSlot, db.session, name='Quản Lý Ca Học'))
admin.add_view(StatsView(name='Thống kê'))
admin.add_view(LogOutView(name='Đăng Xuất'))
admin.add_view(BackHomeView(name='Về Trang Chủ'))