from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from peewee import *
from flask_bcrypt import Bcrypt
import datetime
import os
import urllib.parse
from functools import wraps
from functools import reduce
import operator

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', os.urandom(24))
bcrypt = Bcrypt(app)

db = SqliteDatabase('robot.sqlite')

class BaseModel(Model):
    class Meta:
        database = db

class User(BaseModel):
    account = CharField(unique=True)
    password = CharField()

class Program(BaseModel):
    time = DateTimeField(default=datetime.datetime.now)
    user = ForeignKeyField(User, backref='programs')
    brython = TextField()
    from_where = CharField(default='web')
    memo = TextField(null=True)
    desp = TextField(null=True)

db.connect()
db.create_tables([User, Program], safe=True)

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash("請先登入")
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# ==============================
# 路由
# ==============================

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        account = request.form['account'].strip()
        password = request.form['password']
        confirm_password = request.form['confirm_password']
        if not (len(account) == 8 and account.isdigit()):
            flash("學號必須是 8 位數字！")
            return redirect(url_for('register'))
        if password != confirm_password:
            flash("兩次密碼不一致！")
            return redirect(url_for('register'))
        if User.select().where(User.account == account).exists():
            flash("此學號已被註冊！")
            return redirect(url_for('register'))
        hashed_pw = bcrypt.generate_password_hash(password).decode('utf-8')
        User.create(account=account, password=hashed_pw)
        flash("註冊成功！請登入")
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        account = request.form['account'].strip()
        password = request.form['password']
        try:
            user = User.get(User.account == account)
        except User.DoesNotExist:
            flash("帳號或密碼錯誤")
            return redirect(url_for('login'))
        if bcrypt.check_password_hash(user.password, password):
            session['user_id'] = user.id
            flash("登入成功！")
            return redirect(url_for('brython_test'))
        else:
            flash("帳號或密碼錯誤")
            return redirect(url_for('login'))
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash("已成功登出")
    return redirect(url_for('index'))

# ==============================
# 編輯器主頁（不再傳 load_code）
# ==============================

@app.route('/brython_test')
@login_required
def brython_test():
    # 完全不使用 session 載入程式碼
    return render_template('brython_test.html')

# ==============================
# 儲存程式
# ==============================

@app.route('/save_program', methods=['POST'])
@login_required
def save_program():
    data = request.get_json()
    brython_code = data.get('brython_code', '').strip()
    desp = data.get('desp', '').strip()

    if not brython_code:
        return jsonify({"message": "程式碼不能為空"}), 400

    try:
        user = User.get(User.id == session['user_id'])
        program = Program.create(
            user=user,
            brython=brython_code,
            from_where='',
            memo='',
            desp=desp
        )
        return jsonify({
            "message": "程式碼與描述已儲存到資料庫！",
            "desp": program.desp
        }), 200
    except Exception as e:
        return jsonify({"message": f"儲存失敗: {str(e)}"}), 500

# ==============================
# 載入程式（舊路由 → 導向新方式）
# ==============================

@app.route('/load_program/<int:program_id>')
@login_required
def load_program(program_id):
    try:
        Program.get(Program.id == program_id)   # 只檢查存在
        return redirect(f"{url_for('brython_test')}?load={program_id}")
    except Program.DoesNotExist:
        flash("程式不存在")
        return redirect(url_for('programs'))

# ==============================
# API：取得單一程式（用於自動載入）
# ==============================

@app.route('/api/program/<int:program_id>')
@login_required
def api_get_program(program_id):
    try:
        # 這裡仍然只檢查程式是否存在（不檢查 user），因為已登入即可看全部
        program = Program.get(Program.id == program_id)
        return jsonify({
            'brython': program.brython,
            'desp': program.desp or ''
        })
    except Program.DoesNotExist:
        return jsonify({'error': 'Not found'}), 404

# ==============================
# 程式清單
# ==============================

@app.route('/programs')
@login_required
def programs():
    page = request.args.get('page', 1, type=int)
    per_page = 20
    # 移除 user 過濾
    total_programs = Program.select().count()
    total_pages = (total_programs + per_page - 1) // per_page
    has_next = page < total_pages
    has_prev = page > 1
    programs = Program.select() \
                  .order_by(Program.time.desc()).paginate(page, per_page)
    # 為了在模板中顯示 account，預先 join User
    programs = programs.join(User)
    return render_template('programs.html',
                           programs=programs,
                           page=page,
                           total_pages=total_pages,
                           has_next=has_next,
                           has_prev=has_prev,
                           per_page=per_page)

# ==============================
# 搜尋程式
# ==============================

@app.route('/search_programs')
@login_required
def search_programs():
    q = request.args.get('q', '').strip()
    page = request.args.get('page', 1, type=int)
    per_page = 5
    # 移除 user 過濾，改成 join User 以取得 account
    base = Program.select(Program, User.account).join(User)

    if q:
        conditions = [
            User.account.contains(q),
            Program.brython.contains(q),
            Program.from_where.contains(q),
            Program.memo.contains(q),
            Program.desp.contains(q)
        ]
        base = base.where(reduce(operator.or_, conditions))

    total = base.count()
    total_pages = (total + per_page - 1) // per_page
    has_next = page < total_pages
    has_prev = page > 1
    programs = base.order_by(Program.time.desc()).paginate(page, per_page)

    result = []
    for p in programs:
        result.append({
            'id': p.id,
            'time': p.time.strftime('%Y-%m-%d %H:%M'),
            'account': p.user.account,          # 這裡直接取 join 後的 account
            'brython_snippet': (p.brython or '')[:70].replace('\n', ' ') + ('...' if len(p.brython or '') > 70 else ''),
            'from_where': p.from_where or '',
            'memo': (p.memo or '')[:40] + ('...' if p.memo and len(p.memo) > 40 else ''),
            'desp': (p.desp or '')[:50] + ('...' if p.desp and len(p.desp) > 50 else ''),
        })
    return jsonify({
        'programs': result,
        'page': page,
        'total_pages': total_pages,
        'has_next': has_next,
        'has_prev': has_prev,
        'total': total
    })

# ==============================
# 啟動
# ==============================

if __name__ == '__main__':
    app.run(debug=True)