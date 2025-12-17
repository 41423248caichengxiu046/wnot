from peewee import *
import datetime

# 設定資料庫
new_db = SqliteDatabase('robot_new.sqlite')
old_db = SqliteDatabase('robot.sqlite')

# === 新資料庫模型（已包含 desp）===
class BaseModel(Model):
    class Meta:
        database = new_db

class User(BaseModel):
    account = CharField(unique=True)
    password = CharField()

class Program(BaseModel):
    time = DateTimeField(default=datetime.datetime.now)
    user = ForeignKeyField(User, backref='programs')
    brython = TextField()
    from_where = CharField(default='web')
    memo = TextField(null=True)
    desp = TextField(null=True)  # 新增欄位

# === 舊資料庫模型（不定義 desp）===
class OldBaseModel(Model):
    class Meta:
        database = old_db

class OldUser(OldBaseModel):
    account = CharField(unique=True)
    password = CharField()

    class Meta:
        table_name = 'user'

class OldProgram(OldBaseModel):
    time = DateTimeField()
    user = ForeignKeyField(OldUser, backref='programs')
    brython = TextField()
    from_where = CharField(default='web')
    memo = TextField(null=True)
    # 注意：這裡故意不加 desp

    class Meta:
        table_name = 'program'


# === 主程式 ===
def main():
    print("開始資料搬移...")

    # 1. 建立新資料庫
    new_db.connect()
    new_db.create_tables([User, Program], safe=True)
    print("新資料庫表格建立完成")

    # 2. 連接舊資料庫
    old_db.connect()
    tables = old_db.get_tables()
    print(f"舊資料庫中的資料表：{tables}")

    if 'user' not in tables or 'program' not in tables:
        print("錯誤：缺少 user 或 program 表")
        return

    # 3. 嘗試新增 desp 欄位（忽略錯誤）
    try:
        old_db.execute_sql('ALTER TABLE program ADD COLUMN desp TEXT')
        print("成功新增 desp 欄位")
    except Exception as e:
        print(f"新增 desp 失敗（可能已存在）：{e}")

    # 4. 開始搬移
    try:
        user_map = {}

        # --- 搬移 User ---
        print("正在搬移 User 資料...")
        for old_user in OldUser.select():
            new_user, created = User.get_or_create(
                account=old_user.account,
                defaults={'password': old_user.password}
            )
            if not created:
                new_user.password = old_user.password
                new_user.save()
            user_map[old_user.id] = new_user.id
            print(f"{'新增' if created else '更新'} User: {old_user.account}")

        # --- 搬移 Program（使用原始 SQL 讀取 desp）---
        print("正在搬移 Program 資料...")
        cursor = old_db.execute_sql("""
            SELECT id, time, user_id, brython, from_where, memo, desp 
            FROM program
            ORDER BY id
        """)

        for row in cursor.fetchall():
            (prog_id, time, user_id, brython, from_where, memo, desp) = row

            if user_id not in user_map:
                print(f"警告：Program ID {prog_id} 的 user_id {user_id} 不存在，跳過")
                continue

            new_user = User.get(User.id == user_map[user_id])

            Program.create(
                time=time,
                user=new_user,
                brython=brython,
                from_where=from_where,
                memo=memo,
                desp=desp  # 直接從 SQL 讀取
            )
            print(f"搬移 Program ID: {prog_id}")

        print("所有資料搬移完成！")

    except Exception as e:
        print(f"資料搬移失敗：{e}")
        import traceback
        traceback.print_exc()
    finally:
        old_db.close()
        new_db.close()
        print("資料庫連接已關閉")


if __name__ == '__main__':
    main()