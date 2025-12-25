from flask import request, jsonify, url_for, flash, redirect
from markupsafe import Markup
from flask_admin import Admin, BaseView, expose, AdminIndexView
from flask_admin.contrib.sqla import ModelView
from flask_admin.actions import action
from flask_login import current_user, logout_user
from datetime import datetime,timedelta
from eapp.Models import Course, UserRole, Category, User, Class, Grade, Attendance, GradeColumn, GradeScore, TimeSlot,Receipt
from eapp import app, db, dao


class AdminView(ModelView):
    def is_accessible(self): return current_user.is_authenticated and current_user.user_role == UserRole.ADMIN


class TeacherModelView(ModelView):
    def is_accessible(self):
        # Cho phép nếu là Admin HOẶC Teacher
        return current_user.is_authenticated and \
               (current_user.user_role == UserRole.ADMIN or current_user.user_role == UserRole.TEACHER)
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


class ClassView(AdminView):
    column_list = ['name', 'course', 'teacher', 'time_slot', 'max_students', 'start_date', 'is_finished']
    column_labels = {
        'name': 'Tên Lớp',
        'course': 'Khóa Học',
        'teacher': 'Giáo Viên',
        'time_slot': 'Ca Học',
        'max_students': 'Sĩ Số',
        'start_date': 'Ngày Khai Giảng',
        'is_finished': 'Đã Kết Thúc'
    }
    column_editable_list = ['name', 'start_date']

    form_excluded_columns = ['is_finished', 'receipt_details', 'grades', 'attendances', 'grade_columns']

    def on_model_change(self, form, model, is_created):
        if is_created:
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
                for col in old.grade_columns:
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


class GradeColumnView(TeacherModelView):
    column_list = ['study_class', 'name', 'weight']
    column_labels = {'study_class': 'Lớp học', 'name': 'Tên cột điểm', 'weight': 'Trọng số (%)'}

    form_columns = ['study_class', 'name', 'weight']


    can_create = True
    can_edit = True
    can_delete = True


    def on_model_change(self, form, model, is_created):

        if model.weight < 0 or model.weight > 100:
            raise Exception('Trọng số phải từ 0 đến 100!')


class ReceiptView(AdminView):
    column_searchable_list = ['user_id']

    def is_accessible(self):
        return current_user.is_authenticated and \
            (current_user.user_role == UserRole.ADMIN or current_user.user_role == UserRole.STAFF)

    column_list = ['id', 'user', 'created_date', 'total_amount',
                   'status_alert']

    column_labels = {
        'id': 'Mã HĐ',
        'user': 'Học viên',
        'created_date': 'Ngày đăng ký',
        'total_amount': 'Tổng tiền',
        'status_alert': 'Trạng thái (Cần xử lý)'
    }

    can_create = False
    can_edit = True
    can_delete = True


    def _status_formatter(view, context, model, name):

        if model.is_paid:
            return Markup('<span class="badge bg-success text-white">✅ Đã thanh toán</span>')


        time_diff = datetime.now() - model.created_date

        if time_diff > timedelta(hours=48):
            return Markup(f'''
                <span class="badge bg-danger text-white">⚠️ QUÁ HẠN 48H</span>
                <br><small class="text-danger">Cần hủy gấp</small>
            ''')

        return Markup('<span class="badge bg-warning text-dark">⏳ Chờ thanh toán</span>')

    # Gán hàm formatter vào cột
    column_formatters = {
        'status_alert': _status_formatter,
        'total_amount': lambda v, c, m, n: "{:,.0f} VNĐ".format(m.total_amount)
    }

    def on_model_delete(self, model):
        if model.is_paid:
            flash('CẢNH BÁO: Bạn vừa xóa một hóa đơn ĐÃ THANH TOÁN!', 'warning')

        from eapp.Models import ReceiptDetails, Grade
        details = ReceiptDetails.query.filter_by(receipt_id=model.id).all()
        for d in details:
            g = Grade.query.filter_by(student_id=model.user_id, class_id=d.class_id).first()
            if g: db.session.delete(g)


class GradeManagerView(TeacherBaseView):
    @expose('/')
    def index(self):
        class_id = request.args.get('class_id')
        chosen_class, columns, rows = None, [], []

        if current_user.user_role == UserRole.ADMIN:
            classes = Class.query.all()
        else:
            classes = Class.query.filter(Class.teacher_id == current_user.id).all()

        if class_id:
            chosen_class = Class.query.get(class_id)
            if chosen_class:
                columns = GradeColumn.query.filter_by(class_id=class_id).all()

                grades = Grade.query.filter_by(class_id=class_id).all()

                for g in grades:
                    row = {
                        'student_name': g.student.name,
                        'student_code': g.student.username,
                        'grade_id': g.id,
                        'final': g.final_average,
                        'result': g.result,
                        'scores': {}
                    }
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

            try:
                val = float(d.get('value'))
            except ValueError:
                return jsonify({'status': 'error', 'msg': 'Điểm phải là số!'})

            if val < 0 or val > 10:
                return jsonify({'status': 'error', 'msg': 'Điểm không hợp lệ (Phải từ 0 đến 10)!'})

            score = GradeScore.query.filter_by(grade_id=grade_id, grade_column_id=col_id).first()
            if score:
                score.value = val
            else:
                db.session.add(GradeScore(grade_id=grade_id, grade_column_id=col_id, value=val))
            db.session.commit()

            self.recalculate(grade_id)

            g = Grade.query.get(grade_id)
            return jsonify({'status': 'success', 'new_avg': g.final_average, 'new_res': g.result})

        except Exception as e:
            return jsonify({'status': 'error', 'msg': str(e)})

    def recalculate(self, grade_id):
        scores = GradeScore.query.filter_by(grade_id=grade_id).all()
        total_score_weighted = 0
        total_weight = 0

        for s in scores:
            w = s.column_info.weight
            total_score_weighted += s.value * w
            total_weight += w

        g = Grade.query.get(grade_id)

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



class StatsView(BaseView):
    @expose('/')
    def index(self):
        year_str = request.args.get('year')
        month_str = request.args.get('month')

        current_year = datetime.now().year
        selected_year = int(year_str) if year_str and year_str.isdigit() else current_year
        selected_month = int(month_str) if month_str and month_str.isdigit() else None

        return self.render('admin/stats.html',
                           revenue_time=dao.stats_revenue_style_time(year=selected_year),

                           student_stats=dao.stats_student_count_by_course(year=selected_year, month=selected_month),

                           pass_stats=dao.stats_pass_rate_by_course(year=selected_year, month=selected_month),

                           available_years=dao.get_revenue_years(),
                           selected_year=selected_year,
                           selected_month=selected_month)

    def is_accessible(self):
        return current_user.is_authenticated and \
               (current_user.user_role == UserRole.ADMIN or current_user.user_role == UserRole.STAFF)

class TimeSlotView(AdminView):
    column_list = ['name', 'days', 'start_time', 'end_time']
    column_labels = {'name': 'Tên Ca', 'days': 'Thứ', 'start_time': 'Giờ BĐ', 'end_time': 'Giờ KT'}
    column_editable_list = ['name', 'days', 'start_time', 'end_time']

    def on_model_change(self, form, model, is_created):
        if model.start_time >= model.end_time:
            raise Exception('Giờ bắt đầu phải nhỏ hơn giờ kết thúc!')
class UserView(AdminView):
    def is_accessible(self):
        return current_user.is_authenticated and \
               (current_user.user_role == UserRole.ADMIN or current_user.user_role == UserRole.STAFF)

    column_list = ['name', 'username', 'user_role', 'active']
    column_editable_list = ['active']
    can_create = True
    can_edit = True
class MyAdmin(AdminIndexView):
    @expose('/')
    def index(self): return self.render('admin/index.html', course_count=dao.count_course_by_cate())


admin = Admin(app=app, name='Trung Tâm Ngoại Ngữ', index_view=MyAdmin())
admin.add_view(CourseView(Course, db.session, name='Khóa học'))
admin.add_view(ReceiptView(Receipt, db.session, name='Quản lí hóa đơn'))
admin.add_view(AdminView(Category, db.session, name='Danh mục'))
admin.add_view(ClassView(Class, db.session, name='Lớp học', endpoint='class_manager'))
admin.add_view(UserView(User, db.session, name='Quản lý người dùng'))
admin.add_view(GradeManagerView(name='Quản Lý Điểm', endpoint='grade_manager'))
admin.add_view(GradeColumnView(GradeColumn, db.session, name='Cấu Hình Cột Điểm'))
admin.add_view(AttendanceManagerView(name='Điểm Danh', endpoint='attendance'))
admin.add_view(TimeSlotView(TimeSlot, db.session, name='Quản Lý Ca Học'))
admin.add_view(StatsView(name='Thống kê'))
admin.add_view(LogOutView(name='Đăng Xuất'))
admin.add_view(BackHomeView(name='Về Trang Chủ'))