#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
==============================================
快递管家 - 浏览器会话存储版
==============================================

功能介绍：
1. 自动解析快递短信，提取取件码、取件地点和快递标识
2. 数据保存在浏览器会话中（浏览器不关闭就不会丢失）
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

    streamlit run express_manager_session.py

程序会自动在浏览器中打开，地址通常是：http://localhost:8501

==============================================
特点：
- ✅ 数据在当前浏览器会话中保持
- ✅ 适合部署到 Streamlit Cloud
- ✅ 每个用户独立数据
- ✅ 支持数据导出备份
- ⚠️ 关闭浏览器标签页会丢失数据
==============================================
"""

import re
import json
from datetime import datetime
from typing import Dict, Optional, List
import streamlit as st


# ============================================
# 第一部分：短信解析功能
# ============================================

def parse_sms(sms_content: str) -> Optional[Dict[str, str]]:
    """
    解析快递短信，提取关键信息
    """
    if not sms_content:
        return None

    result = {}

    # 1. 提取快递标识 (tracking_id)
    tracking_pattern = r'快递[:：]\*?(\d+)'
    tracking_match = re.search(tracking_pattern, sms_content)
    if tracking_match:
        result['tracking_id'] = tracking_match.group(1)

    # 2. 提取取件地点 (pickup_location)
    location_pattern = r'(?:已到|送至|存放在|到达)([^，,。.请]+(?:快递站|驿站|代收点|菜鸟|丰巢|速递易))'
    location_match = re.search(location_pattern, sms_content)
    if location_match:
        result['pickup_location'] = location_match.group(1).strip()

    # 3. 提取取件码 (pickup_code)
    code_patterns = [
        r'请凭([A-Za-z0-9]{4,8})(?:前往|领取)',
        r'取件码[:：\s]*([A-Za-z0-9]{4,8})',
        r'验证码[:：\s]*([A-Za-z0-9]{4,8})',
        r'凭([A-Za-z0-9]{4,8})取件',
    ]

    for pattern in code_patterns:
        code_match = re.search(pattern, sms_content)
        if code_match:
            result['pickup_code'] = code_match.group(1)
            break

    if result:
        return result
    else:
        return None


# ============================================
# 第二部分：数据管理功能
# ============================================

def init_session_state():
    """
    初始化 Session State
    """
    if 'packages' not in st.session_state:
        st.session_state.packages = []
    if 'next_id' not in st.session_state:
        st.session_state.next_id = 1


def add_package(data: Dict[str, str]) -> int:
    """
    添加快递到会话存储
    """
    current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    package = {
        'id': st.session_state.next_id,
        'tracking_id': data.get('tracking_id', ''),
        'pickup_code': data.get('pickup_code', ''),
        'pickup_location': data.get('pickup_location', ''),
        'status': '待领取',
        'added_time': current_time
    }

    st.session_state.packages.append(package)
    package_id = st.session_state.next_id
    st.session_state.next_id += 1

    return package_id


def get_pending_packages() -> List[Dict]:
    """
    获取所有待领取的快递
    """
    return [pkg for pkg in st.session_state.packages if pkg['status'] == '待领取']


def mark_as_picked_up(package_id: int) -> bool:
    """
    标记快递为已领取
    """
    for pkg in st.session_state.packages:
        if pkg['id'] == package_id:
            pkg['status'] = '已领取'
            return True
    return False


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

    # 初始化 Session State
    init_session_state()

    # 页面标题
    st.title("📦 我的快递管家")
    st.caption("💾 数据保存在当前浏览器会话中")
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
                # 添加到会话存储
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

    # ========== 数据管理功能 ==========
    st.markdown("")
    st.markdown("")

    with st.expander("🔧 数据管理"):
        col1, col2, col3 = st.columns(3)

        with col1:
            st.write("**导出数据**")
            if st.session_state.packages:
                data_json = json.dumps(st.session_state.packages, ensure_ascii=False, indent=2)
                st.download_button(
                    label="📥 下载数据备份",
                    data=data_json,
                    file_name=f"express_manager_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                    mime="application/json",
                    use_container_width=True
                )
            else:
                st.info("暂无数据可导出")

        with col2:
            st.write("**导入数据**")
            uploaded_file = st.file_uploader("上传备份文件", type="json", key="upload_backup")
            if uploaded_file is not None:
                try:
                    data = json.load(uploaded_file)
                    st.session_state.packages = data
                    if data:
                        max_id = max([pkg['id'] for pkg in data])
                        st.session_state.next_id = max_id + 1
                    st.success("✅ 数据导入成功！")
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ 导入失败：{str(e)}")

        with col3:
            st.write("**清空数据**")
            if st.button("🗑️ 清空所有快递记录", type="secondary", use_container_width=True):
                st.session_state.packages = []
                st.session_state.next_id = 1
                st.success("数据已清空！")
                st.rerun()

    # 页面底部信息
    st.markdown("")
    st.caption("💡 提示：")
    st.caption("  • 数据在浏览器关闭前会一直保存")
    st.caption("  • 建议定期使用'导出数据'功能备份")
    st.caption("  • 可以在其他设备导入备份文件继续使用")


# ============================================
# 程序入口
# ============================================

if __name__ == "__main__":
    main()
