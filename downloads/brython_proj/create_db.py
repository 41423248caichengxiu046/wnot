# pip install flask peewee flask-bcrypt
from peewee import *
import bcrypt
import datetime

# 設定 SQLite 資料庫
db = SqliteDatabase('robot.sqlite')

# 定義 User 模型
class User(Model):
    account = CharField(unique=True)
    password = CharField()
    
    class Meta:
        database = db

# 定義 Program 模型
class Program(Model):
    time = DateTimeField(default=datetime.datetime.now)
    user = ForeignKeyField(User, backref='programs')
    brython = TextField()
    from_where = CharField(default='web')
    memo = TextField(null=True)
    desp = TextField(null=True) 
    
    class Meta:
        database = db

# 初始化資料庫
db.connect()
db.create_tables([User, Program])
