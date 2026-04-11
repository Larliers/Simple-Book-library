from __future__ import annotations


APP_STYLE = """
QWidget {
    background: #f4f5f7;
    color: #1f2937;
    font-family: "Segoe UI", "Microsoft YaHei";
    font-size: 14px;
}
#Sidebar {
    background: #eceff3;
    border-right: 1px solid #d9dfe8;
}
#SidebarTitle {
    font-size: 28px;
    font-weight: 700;
    margin-bottom: 8px;
}
QPushButton {
    border: 1px solid transparent;
    border-radius: 4px;
    padding: 7px 10px;
    text-align: left;
    background: transparent;
}
QPushButton:hover {
    background: #dce3ee;
}
QPushButton:checked {
    background: #d7e3f7;
    color: #1b4f9b;
    font-weight: 600;
}
#PrimarySideButton, #PrimaryButton {
    background: #0f69be;
    color: white;
    border-color: #0f69be;
    text-align: center;
    font-weight: 600;
}
#PrimarySideButton:hover, #PrimaryButton:hover {
    background: #0b5ca8;
}
#DangerButton {
    color: #b91c1c;
    border-color: #efc2c2;
}
#TopBar {
    background: #f7f8fa;
    border-bottom: 1px solid #d9dfe8;
}
QLineEdit, QComboBox, QTextEdit, QListWidget, QTableWidget {
    background: #ffffff;
    border: 1px solid #cfd8e3;
    border-radius: 4px;
    padding: 5px 8px;
}
#PageTitle {
    font-size: 44px;
    font-weight: 700;
}
#PageSubtitle {
    color: #6b7280;
}
#BookCard {
    background: #ffffff;
    border: 1px solid #d6dde9;
    border-radius: 4px;
}
#BookCover {
    background: #e6eaf0;
    color: #6b7280;
    border: 1px dashed #c8d1df;
}
#BookTitle {
    font-size: 16px;
    font-weight: 650;
}
#BookMeta {
    color: #6b7280;
}
#BookStatus {
    color: #0f69be;
    font-weight: 700;
}
#AddCard {
    color: #6b7280;
    border: 1px dashed #cad4e2;
    background: #f7f9fc;
}
QHeaderView::section {
    background: #f0f3f8;
    border: none;
    border-right: 1px solid #e2e8f0;
    padding: 8px;
    font-weight: 600;
}
"""

