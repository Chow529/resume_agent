#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MySQL 数据库连接管理类
提供统一的数据库连接池和管理功能
"""

import pymysql
from typing import Optional, Dict, Any, List, Tuple
from contextlib import contextmanager


class MySQLConnector:
    """
    数据库连接管理类

    特点：
    - 单例模式管理连接（可根据需要改为连接池）
    - 自动提交/回滚事务控制
    - 安全的参数化查询防止 SQL 注入
    - 支持上下文管理器（with 语句）
    """

    _instance = None

    def __new__(cls, host: str, user: str, password: str, database: str, port: int = 3306):
        """单例模式实例化"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, host: str, user: str, password: str, database: str, port: int = 3306):
        """初始化连接配置（注意：单例模式下只会初始化一次）"""
        # 防止重复初始化
        if hasattr(self, '_initialized'):
            return

        self.host = host
        self.user = user
        self.password = password
        self.database = database
        self.port = port
        self.connection = None
        self._initialized = True

        try:
            self._connect()
        except Exception as e:
            # 连接失败时重置单例，以便下次尝试
            MySQLConnector.reset_singleton()
            raise

    def _connect(self) -> None:
        """建立数据库连接"""
        try:
            self.connection = pymysql.connect(
                host=self.host,
                user=self.user,
                password=self.password,
                database=self.database,
                port=self.port,
                charset='utf8mb4',
                cursorclass=pymysql.cursors.DictCursor,
                autocommit=False  # 手动控制事务
            )
            print(f"✓ 成功连接到 MySQL 数据库: {self.database}")
        except pymysql.Error as e:
            print(f"✗ 连接 MySQL 数据库失败: {e}")
            raise

    @contextmanager
    def get_cursor(self):
        """获取数据库游标的上下文管理器（自动提交或回滚）"""
        # 如果连接无效或关闭，尝试重新连接
        if self.connection is None or getattr(self.connection, 'closed', False):
            self._connect()
        cursor = None
        try:
            cursor = self.connection.cursor()
            yield cursor
            self.connection.commit()  # 默认提交事务
        except Exception as e:
            if cursor:
                self.connection.rollback()
            raise
        finally:
            if cursor:
                cursor.close()

    def execute_query(self, sql: str, params: tuple = ()) -> List[Dict[str, Any]]:
        """
        执行 SELECT 查询，返回结果列表

        Args:
            sql: SQL 语句
            params: 参数元组

        Returns:
            结果字典列表
        """
        with self.get_cursor() as cursor:
            cursor.execute(sql, params)
            return cursor.fetchall()

    def execute_update(self, sql: str, params: tuple) -> int:
        """
        执行 INSERT/UPDATE/DELETE 操作，受影响的行数

        Args:
            sql: SQL 语句
            params: 参数元组

        Returns:
            受影响的行数
        """
        with self.get_cursor() as cursor:
            cursor.execute(sql, params)
            return cursor.rowcount

    def execute_insert(self, sql: str, params: tuple) -> int:
        """
        执行 INSERT 操作，返回新插入记录的ID

        Args:
            sql: SQL 语句
            params: 参数元组

        Returns:
            新记录的主键ID
        """
        with self.get_cursor() as cursor:
            cursor.execute(sql, params)
            return cursor.lastrowid

    def close(self) -> None:
        """关闭数据库连接"""
        if self.connection:
            self.connection.close()
            print("✓ MySQL 连接已关闭")
            self.connection = None

    def show_database_structure(self):
        """显示数据库中所有表的字段信息"""
        try:
            with self.get_cursor() as cursor:
                cursor.execute("SELECT TABLE_NAME FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_SCHEMA = %s", (self.database,))
                tables = cursor.fetchall()

                if not tables:
                    print("✗ 数据库中无表")
                    return

                print(f"\n数据库: {self.database}")
                print(f"共找到 {len(tables)} 个表\n")

                for table_row in tables:
                    table_name = table_row['TABLE_NAME']
                    print("-" * 60)
                    print(f"表名: {table_name}")
                    print("-" * 60)

                    cursor.execute(f"SHOW COLUMNS FROM `{table_name}`")
                    fields = cursor.fetchall()

                    if not fields:
                        print("  ✗ 无法获取字段信息")
                        continue

                    print(f"{'字段名':<20} {'类型':<30} {'Null':<10} {'键':<10} {'默认':<20} {'额外'}")
                    print("-" * 110)

                    for field in fields:
                        default_str = field['Default'] if field['Default'] is not None else 'NULL'
                        print(f"{field['Field']:<20} {field['Type']:<30} {field['Null']:<10} {field['Key']:<10} {default_str:<20} {field['Extra']:<20}")

                    print()

        except Exception as e:
            print(f"✗ 获取表结构失败: {e}")

    @staticmethod
    def reset_singleton():
        """重置单例实例（用于测试或切换连接）"""
        MySQLConnector._instance = None


# ========== 基类：实现通用 CRUD 操作 ==========

from dotenv import load_dotenv
import os

load_dotenv()  # 加载 .env 文件中的环境变量 

class BaseModel:
    """
    数据库模型基类
    所有数据模型类都应继承此类
    """

    def __init__(self, table_name: str, db=None):
        self.table_name = table_name
        # 如果没有提供数据库连接，则获取单例连接
        if db is None:
            self.db = MySQLConnector(os.getenv('DB_HOST',"localhost"), os.getenv('DB_USER','root'), os.getenv('DB_PASSWORD','hwa123456'), os.getenv('DB_LIBRARY','dmmDb') , int(os.getenv('DB_PORT', 3306)) )
        else:
            self.db = db

    def get(self, id: int) -> Optional[Dict[str, Any]]:
        """根据主键获取单条记录"""
        sql = f"SELECT * FROM `{self.table_name}` WHERE id = %s"
        results = self.db.execute_query(sql, (id,))
        return results[0] if results else None

    def get_all(self) -> List[Dict[str, Any]]:
        """获取所有记录"""
        sql = f"SELECT * FROM `{self.table_name}`"
        return self.db.execute_query(sql)

    def get_by(self, field: str, value: Any) -> Optional[Dict[str, Any]]:
        """根据指定字段获取单条记录"""
        sql = f"SELECT * FROM `{self.table_name}` WHERE {field} = %s"
        results = self.db.execute_query(sql, (value,))
        return results[0] if results else None

    def get_all_by(self, field: str, value: Any) -> List[Dict[str, Any]]:
        """根据指定字段获取所有匹配记录"""
        sql = f"SELECT * FROM `{self.table_name}` WHERE {field} = %s"
        return self.db.execute_query(sql, (value,))

    def create(self, data: Dict[str, Any]) -> int:
        """
        创建新记录
        data: 字段名 -> 值 的字典
        返回新记录的 ID
        """
        fields = ', '.join(data.keys())
        placeholders = ', '.join(['%s'] * len(data))
        sql = f"INSERT INTO `{self.table_name}` ({fields}) VALUES ({placeholders})"
        values = tuple(data.values())
        return self.db.execute_insert(sql, values)

    def update(self, id: int, data: Dict[str, Any]) -> int:
        """
        更新记录
        id: 主键值
        data: 字段名 -> 值 的字典
        返回受影响的行数
        """
        set_clause = ', '.join([f"{k} = %s" for k in data.keys()])
        values = tuple(data.values()) + (id,)
        sql = f"UPDATE `{self.table_name}` SET {set_clause} WHERE id = %s"
        return self.db.execute_update(sql, values)

    def delete(self, id: int) -> int:
        """根据主键删除记录，返回受影响的行数"""
        sql = f"DELETE FROM `{self.table_name}` WHERE id = %s"
        return self.db.execute_update(sql, (id,))

    def count(self, where_field: str = None, where_value: Any = None) -> int:
        """记录计数，可选 WHERE 条件"""
        if where_field and where_value is not None:
            sql = f"SELECT COUNT(*) AS count FROM `{self.table_name}` WHERE {where_field} = %s"
            result = self.db.execute_query(sql, (where_value,))
        else:
            sql = f"SELECT COUNT(*) AS count FROM `{self.table_name}`"
            result = self.db.execute_query(sql)
        return result[0]['count'] if result else 0

    def close(self):
        """关闭数据库连接"""
        self.db.close()


# ========== 模型类：用户表操作 ==========

class UserModel(BaseModel):
    """用户模型类，继承自 BaseModel"""

    def __init__(self):
        super().__init__('users')

    def create_user(self, username: str, email: str, password_hash: str, salt: str, is_active: int = 1) -> Optional[int]:
        """创建新用户"""
        # 使用通用的 get_by 方法检查唯一性
        if self.get_by('username', username) or self.get_by('email', email):
            print("✗ 用户名或邮箱已存在")
            return None

        data = {
            'username': username,
            'email': email,
            'password_hash': password_hash,
            'salt': salt,
            'is_active': is_active
        }
        return self.create(data)

    def get_user_by_username(self, username: str) -> Optional[Dict[str, Any]]:
        """通过用户名获取用户信息"""
        return self.get_by('username', username)

    def get_user_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """通过邮箱获取用户信息"""
        return self.get_by('email', email)

    def update_user_password(self, user_id: int, password_hash: str, salt: str) -> bool:
        """更新用户密码"""
        return self.update(user_id, {'password_hash': password_hash, 'salt': salt}) > 0

    def lock_user(self, user_id: int) -> bool:
        """锁定用户"""
        return self.update(user_id, {'is_locked': 1}) > 0

    def unlock_user(self, user_id: int) -> bool:
        """解锁用户"""
        return self.update(user_id, {'is_locked': 0}) > 0

    def deactivate_user(self, user_id: int) -> bool:
        """禁用用户"""
        return self.update(user_id, {'is_active': 0}) > 0

    def activate_user(self, user_id: int) -> bool:
        """激活用户"""
        return self.update(user_id, {'is_active': 1, 'is_locked': 0}) > 0

    def delete_user(self, user_id: int) -> int:
        """删除用户"""
        return self.delete(user_id)


# ========== 使用示例 ==========

if __name__ == '__main__':
    # ========== 演示 1: 使用 BaseModel 基类和 UserModel 子类 ==========
    print("\n" + "="*60)
    print("演示 1: 使用 BaseModel 基类和 UserModel 子类")
    print("="*60)

    user_model = UserModel()

    try:
        # 1. 新增测试用户
        print("\n步骤 1: 新增测试用户")
        test_username = 'test_user_' + '20260730'
        test_email = f'test_{test_username}@example.com'
        test_password_hash = 'e10adc3949ba59abbe56e057f20f883e'
        test_salt = 'test_salt_' + '20260730'

        user_id = user_model.create_user(test_username, test_email, test_password_hash, test_salt)
        print(f"✓ 用户创建成功，ID: {user_id}")

        if user_id:
            # 2. 查询用户（使用通用方法 get()）
            print("\n步骤 2: 查询用户（使用通用方法 get()）")
            user = user_model.get(user_id)
            print(f"  查询结果: {user}")

            # 3. 查询用户（使用专用方法）
            print("\n步骤 3: 查询用户（使用专用方法 get_by_username()）")
            user_by_username = user_model.get_user_by_username(test_username)
            print(f"  查询结果: {user_by_username}")

            # 4. 更新用户数据
            print("\n步骤 4: 更新用户数据（使用 update()）")
            updated_rows = user_model.update(user_id, {'is_active': 0})
            print(f"  更新受影响的行数: {updated_rows}")

            # 5. 删除用户
            print("\n步骤 5: 删除用户（使用 delete()）")
            deleted_rows = user_model.delete_user(user_id)
            print(f"  删除成功！删除行数: {deleted_rows}")

            # 6. 验证删除
            print("\n步骤 6: 验证删除结果")
            verify_user = user_model.get(user_id)
            print(f"  查询结果: {verify_user} (应为 None)")

            # 7. 使用 BaseModel 的通用计数方法
            print("\n步骤 7: 使用 BaseModel 的计数方法")
            total_count = user_model.count()
            print(f"  用户表总记录数: {total_count}")

            active_count = user_model.count(where_field='is_active', where_value=1)
            print(f"  激活用户数: {active_count}")

    except Exception as e:
        print(f"\n✗ 操作失败: {e}")
    finally:
        user_model.close()
        print("\n✓ 连接已关闭")

    # ========== 演示 2: 直接使用单例连接类 ==========
    # print("\n" + "="*60)
    # print("演示 2: 直接使用 MySQLConnector 单例类")
    # print("="*60)

    # from mysql_connector import MySQLConnector as MC
    # db = MC('localhost', 'root', 'hwa123456', 'dmmDb')

    # try:
    #     # 新增数据
    #     insert_sql = """
    #         INSERT INTO users (username, email, password_hash, salt, is_active)
    #         VALUES (%s, %s, %s, %s, %s)
    #     """
    #     test_username2 = 'test_user2_' + '20260730'
    #     test_email2 = f'test_{test_username2}@example.com'
    #     new_id = db.execute_insert(insert_sql, (test_username2, test_email2, test_password_hash, test_salt, 1))
    #     print(f"✓ 新增成功，ID: {new_id}")

    #     # 查询数据
    #     query_sql = "SELECT * FROM users WHERE username = %s"
    #     results = db.execute_query(query_sql, (test_username2,))
    #     print(f"查询结果 ({len(results)} 条):")
    #     for row in results:
    #         print(f"  {row}")

    #     # 删除数据
    #     delete_sql = "DELETE FROM users WHERE id = %s"
    #     deleted_rows = db.execute_update(delete_sql, (new_id,))
    #     print(f"✓ 删除成功，行数: {deleted_rows}")

    # except Exception as e:
    #     print(f"操作失败: {e}")
    # finally:
    #     db.close()
