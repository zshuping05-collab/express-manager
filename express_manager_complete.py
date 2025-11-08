#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
==============================================
快递管家 - 完整版
==============================================

功能介绍：
1. 自动解析快递短信，提取取件码、取件地点和快递标识
2. 将快递信息存储到 SQLite 数据库
3. 提供 Web 界面管理快递（添加、查看、标记已领取）

==============================================
安装依赖：
==============================================
请在运行本程序前，先安装 Streamlit：

    pip install streamlit

==============================================
启动程序：
==============================================
在终端/命令行中运行：

    streamlit run express_manager_complete.py

程序会自动在浏览器中打开，地址通常是：http://localhost:8501

==============================================
"""

import re
import sqlite3
from datetime import datetime
from typing import Dict, Optional, List
import streamlit as st


# ============================================
# 第一部分：短信解析功能
# ============================================

def parse_sms(sms_content: str) -> Optional[Dict[str, str]]:
    """
    解析快递短信，提取关键信息

    从快递短信中提取取件码、取件地点和快递标识

    参数:
        sms_content (str): 短信内容字符串

    返回:
        Dict[str, str]: 包含以下键的字典：
            - pickup_code: 取件码
            - pickup_location: 取件地点
            - tracking_id: 快递标识
        如果解析失败，返回 None

    示例:
        >>> sms = "【递管家】您的快递:*83226已到燕山区4栋快递站，请凭6A28前往人工货架领取"
        >>> result = parse_sms(sms)
        >>> print(result)
        {'pickup_code': '6A28', 'pickup_location': '燕山区4栋快递站', 'tracking_id': '83226'}
    """

    if not sms_content:
        return None

    result = {}

    # 1. 提取快递标识 (tracking_id)
    # 匹配模式：快递后面跟着冒号，然后是可能的星号，再跟数字
    tracking_pattern = r'快递[:：]\*?(\d+)'
    tracking_match = re.search(tracking_pattern, sms_content)
    if tracking_match:
        result['tracking_id'] = tracking_match.group(1)

    # 2. 提取取件地点 (pickup_location)
    # 匹配模式："已到" 后面跟着的地点信息
    location_pattern = r'(?:已到|送至|存放在|到达)([^，,。.请]+(?:快递站|驿站|代收点|菜鸟|丰巢|速递易))'
    location_match = re.search(location_pattern, sms_content)
    if location_match:
        result['pickup_location'] = location_match.group(1).strip()

    # 3. 提取取件码 (pickup_code)
    # 支持多种格式：6A28、1234、AB12等
    code_patterns = [
        r'请凭([A-Za-z0-9]{4,8})(?:前往|领取)',  # 请凭XXXX前往/领取
        r'取件码[:：\s]*([A-Za-z0-9]{4,8})',    # 取件码:XXXX
        r'验证码[:：\s]*([A-Za-z0-9]{4,8})',    # 验证码:XXXX
        r'凭([A-Za-z0-9]{4,8})取件',           # 凭XXXX取件
    ]

    for pattern in code_patterns:
        code_match = re.search(pattern, sms_content)
        if code_match:
            result['pickup_code'] = code_match.group(1)
            break

    # 如果至少提取到一个关键信息，返回结果；否则返回 None
    if result:
        return result
    else:
        return None


# ============================================
# 第二部分：数据库操作功能
# ============================================

# 数据库文件名
DB_FILE = 'express_manager.db'


def init_database():
    """
    初始化数据库，创建 packages 表

    如果表已存在，则不会重复创建
    """
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    # 创建 packages 表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS packages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tracking_id TEXT,
            pickup_code TEXT,
            pickup_location TEXT,
            status TEXT DEFAULT '待领取',
            added_time TEXT NOT NULL
        )
    ''')

    conn.commit()
    conn.close()


def add_package(data: Dict[str, str]) -> int:
    """
    将快递信息添加到数据库

    参数:
        data (Dict[str, str]): parse_sms 函数返回的字典

    返回:
        int: 新插入记录的 id
    """
    # 确保数据库已初始化
    init_database()

    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    # 获取当前时间
    current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    # 插入数据
    cursor.execute('''
        INSERT INTO packages (tracking_id, pickup_code, pickup_location, status, added_time)
        VALUES (?, ?, ?, ?, ?)
    ''', (
        data.get('tracking_id', ''),
        data.get('pickup_code', ''),
        data.get('pickup_location', ''),
        '待领取',
        current_time
    ))

    package_id = cursor.lastrowid
    conn.commit()
    conn.close()

    return package_id


def get_pending_packages() -> List[Dict]:
    """
    查询所有待领取的快递

    返回:
        List[Dict]: 待领取快递的列表
    """
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute('''
        SELECT id, tracking_id, pickup_code, pickup_location, status, added_time
        FROM packages
        WHERE status = '待领取'
        ORDER BY added_time DESC
    ''')

    rows = cursor.fetchall()
    conn.close()

    # 将 Row 对象转换为字典列表
    packages = [dict(row) for row in rows]
    return packages


def mark_as_picked_up(package_id: int) -> bool:
    """
    标记快递为已领取

    参数:
        package_id (int): 快递记录的 id

    返回:
        bool: 如果更新成功返回 True，否则返回 False
    """
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    cursor.execute('''
        UPDATE packages
        SET status = '已领取'
        WHERE id = ?
    ''', (package_id,))

    rows_affected = cursor.rowcount
    conn.commit()
    conn.close()

    return rows_affected > 0


# ============================================
# 第三部分：Streamlit Web 界面
# ============================================

def main():
    """
    主函数 - 运行 Streamlit Web 应用
    """
    # 设置页面配置
    st.set_page_config(
        page_title="快递管家",
        page_icon="📦",
        layout="wide"
    )

    # 初始化数据库
    init_database()

    # 页面标题
    st.title("📦 我的快递管家")
    st.markdown("---")

    # ========== 第一部分：添加新快递 ==========
    st.header("➕ 添加新快递")

    col1, col2 = st.columns([4, 1])

    with col1:
        sms_input = st.text_area(
            "请粘贴快递短信内容：",
            placeholder="例如：【递管家】您的快递:*83226已到燕山区4栋快递站，请凭6A28前往人工货架领取...",
            height=100,
            key="sms_input"
        )

    with col2:
        st.write("")  # 用于对齐
        st.write("")  # 用于对齐
        add_button = st.button("📥 添加快递", use_container_width=True, type="primary")

    # 处理添加快递的逻辑
    if add_button:
        if sms_input.strip():
            # 解析短信
            parsed_data = parse_sms(sms_input)

            if parsed_data:
                # 添加到数据库
                package_id = add_package(parsed_data)

                # 显示成功消息
                st.success(f"✅ 添加成功！快递 ID: {package_id}")

                # 显示解析的信息
                with st.expander("查看解析的信息"):
                    st.write(f"**取件码：** {parsed_data.get('pickup_code', '未识别')}")
                    st.write(f"**取件地点：** {parsed_data.get('pickup_location', '未识别')}")
                    st.write(f"**快递标识：** {parsed_data.get('tracking_id', '未识别')}")

                # 清空输入框（通过 rerun）
                st.rerun()
            else:
                st.error("❌ 无法解析短信内容，请检查格式是否正确。")
        else:
            st.warning("⚠️ 请输入快递短信内容。")

    st.markdown("---")

    # ========== 第二部分：待领取的快递列表 ==========
    st.header("📋 待领取的快递")

    # 获取所有待领取的快递
    pending_packages = get_pending_packages()

    if pending_packages:
        st.write(f"共有 **{len(pending_packages)}** 个待领取快递：")
        st.write("")  # 空行

        # 遍历每个快递，显示卡片式界面
        for pkg in pending_packages:
            # 创建一个容器来显示每个快递
            with st.container():
                col1, col2, col3 = st.columns([3, 3, 1.5])

                with col1:
                    st.markdown(f"### 📍 {pkg['pickup_location'] or '地点未识别'}")
                    st.caption(f"添加时间: {pkg['added_time']}")

                with col2:
                    st.markdown(f"### 🔑 取件码: `{pkg['pickup_code'] or '未识别'}`")
                    if pkg['tracking_id']:
                        st.caption(f"快递标识: {pkg['tracking_id']}")

                with col3:
                    st.write("")  # 用于对齐
                    # 为每个快递创建一个唯一的按钮
                    if st.button(
                        "✅ 我已领取",
                        key=f"pickup_{pkg['id']}",
                        use_container_width=True,
                        type="secondary"
                    ):
                        # 标记为已领取
                        success = mark_as_picked_up(pkg['id'])
                        if success:
                            st.success(f"已将快递 ID {pkg['id']} 标记为已领取！")
                            # 刷新页面
                            st.rerun()
                        else:
                            st.error(f"标记失败，请重试。")

                # 分隔线
                st.markdown("---")
    else:
        st.info("🎉 太棒了！目前没有待领取的快递。")

    # ========== 页面底部信息 ==========
    st.markdown("")
    st.markdown("")
    st.caption("💡 提示：添加新快递后，页面会自动刷新。标记快递为已领取后，该快递将从列表中移除。")


# ============================================
# 程序入口
# ============================================

if __name__ == "__main__":
    main()
