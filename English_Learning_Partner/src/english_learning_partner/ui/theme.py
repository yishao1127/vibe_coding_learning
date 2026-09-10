"""Shared visual theme for the Windows desktop application."""

APP_STYLESHEET = """
QMainWindow {
    background: #F5F7FB;
    color: #1F2937;
    font-family: "Source Han Sans CN", "Microsoft YaHei UI", "Segoe UI";
}
QWidget {
    color: #1F2937;
    font-family: "Source Han Sans CN", "Microsoft YaHei UI", "Segoe UI";
}
QLabel { background: transparent; }
QWidget#translationKeyValueRow { background: transparent; }
QDialog {
    background: #F5F7FB;
    color: #1F2937;
}
QDialog QWidget { background: transparent; }
QDialog QSpinBox {
    background: #FFFFFF;
    border: 1px solid #D7DFEC;
    border-radius: 8px;
    color: #1F2937;
    font-size: 12pt;
    min-height: 36px;
    padding: 2px 10px;
}
QDialog QDialogButtonBox { background: transparent; }
QToolBar {
    background: #FFFFFF;
    border: none;
    border-bottom: 1px solid #E5EAF2;
    padding: 10px 18px;
    spacing: 8px;
}
QTabWidget::pane {
    border: none;
    background: transparent;
}
QTabBar::tab {
    background: transparent;
    color: #5D6B82;
    border: none;
    border-bottom: 3px solid transparent;
    font-size: 12pt;
    font-weight: 600;
    min-width: 88px;
    padding: 13px 18px 11px;
    margin-right: 4px;
}
QTabBar::tab:hover { color: #155EEF; }
QTabBar::tab:selected {
    color: #155EEF;
    border-bottom-color: #155EEF;
}
QToolButton#settingsButton {
    background: transparent;
    border: none;
    border-radius: 18px;
    color: #56677F;
    font-family: "Segoe UI Symbol", "Microsoft YaHei UI";
    font-size: 17pt;
    font-weight: 400;
    min-height: 36px;
    max-height: 36px;
    min-width: 40px;
    max-width: 40px;
    margin: 4px 18px 0 0;
}
QToolButton#settingsButton:hover { background: #EAF1FF; color: #155EEF; }
QToolButton#settingsButton:pressed { background: #DCEAFF; }
QFrame#inputCard, QFrame#resultCard, QFrame#reviewCard {
    background: #FFFFFF;
    border: 1px solid #E2E8F2;
    border-radius: 12px;
}
QScrollArea#translationResult, QScrollArea#polishResult, QScrollArea#reviewDetail {
    background: #F7F9FC;
    border: none;
}
QWidget#translationResultContainer, QWidget#translationCardGrid, QWidget#polishResultContainer, QWidget#reviewDetailContainer {
    background: #F7F9FC;
}
QFrame#translationPrimaryCard, QFrame#translationSectionCard, QFrame#translationSourceCard, QFrame#translationErrorCard {
    background: #FFFFFF;
    border: 1px solid #C9D5E5;
    border-radius: 10px;
}
QFrame#translationPrimaryCard {
    background: #F1F6FF;
    border: 2px solid #A9C7FA;
}
QFrame#translationSourceCard {
    background: #F8FAFD;
    border-color: #DCE4EF;
}
QFrame#translationErrorCard {
    background: #FFF8ED;
    border-color: #E9BC70;
}
QLabel#translationCardTitle {
    color: #34445C;
    font-size: 11.5pt;
    font-weight: 700;
}
QLabel#translationHeadword {
    color: #172B4D;
    font-family: "Segoe UI", "Microsoft YaHei UI";
    font-size: 19pt;
    font-weight: 700;
}
QLabel#translationHero {
    background: #E8F1FF;
    border-left: 4px solid #155EEF;
    border-radius: 6px;
    color: #123B80;
    font-size: 14pt;
    font-weight: 600;
    padding: 11px 13px;
}
QLabel#translationMeta, QLabel#translationExampleChinese, QLabel#translationAlternativeNote {
    color: #66758A;
    font-size: 10.5pt;
}
QWidget#pronunciationRow { background: transparent; }
QToolButton#pronunciationButton {
    background: #FFFFFF;
    border: 1px solid #B9CAE2;
    border-radius: 14px;
    color: #155EEF;
    min-height: 28px;
    min-width: 28px;
    max-height: 28px;
    max-width: 28px;
    padding: 2px;
}
QToolButton#pronunciationButton:hover { background: #EAF1FF; border-color: #75A7FF; }
QToolButton#pronunciationButton:disabled { background: #E9EDF4; border-color: #E1E7F0; }
QToolButton#reviewItemMenuButton, QToolButton#issueMenuButton {
    background: transparent;
    border: none;
    border-radius: 12px;
    color: #66758A;
    font-size: 15pt;
    font-weight: 700;
    min-width: 28px;
    max-width: 28px;
    min-height: 28px;
    max-height: 28px;
    padding: 0;
}
QToolButton#reviewItemMenuButton:hover, QToolButton#issueMenuButton:hover {
    background: #EAF1FF;
    color: #155EEF;
}
QToolButton#reviewItemMenuButton::menu-indicator, QToolButton#issueMenuButton::menu-indicator {
    image: none;
    width: 0;
}
QMenu {
    background: #FFFFFF;
    border: 1px solid #D7DFEC;
    border-radius: 8px;
    color: #34445C;
    font-size: 11pt;
    padding: 5px;
}
QMenu::item { border-radius: 5px; padding: 7px 24px 7px 10px; }
QMenu::item:selected { background: #FFF1F0; color: #B42318; }
QLabel#translationCardText, QLabel#translationBullet, QLabel#translationValue {
    color: #26354C;
    font-size: 11.5pt;
}
QLabel#translationBullet { padding: 2px 0; }
QLabel#translationKey {
    color: #66758A;
    font-size: 10.5pt;
    min-width: 88px;
}
QWidget#translationKeyValueRow { border-bottom: 1px solid #E8EDF4; }
QFrame#translationMicroCard {
    background: #F8FAFD;
    border: 1px solid #E1E8F1;
    border-radius: 7px;
}
QFrame#translationIssueCard {
    background: #FFF9EF;
    border: 1px solid #F0D49E;
    border-left: 4px solid #E59B16;
    border-radius: 7px;
}
QLabel#translationIssueBadge {
    background: #FEEDC7;
    border-radius: 9px;
    color: #935700;
    font-size: 9.5pt;
    font-weight: 700;
    padding: 2px 8px;
}
QLabel#translationIssueCaption {
    color: #786444;
    font-size: 9.5pt;
    font-weight: 700;
    padding-top: 3px;
}
QLabel#translationIssueText, QLabel#translationIssueCorrection {
    color: #3D4654;
    font-size: 11pt;
}
QLabel#translationIssueCorrection { color: #087443; font-weight: 700; }
QLabel#translationExampleEnglish, QLabel#translationAlternativeExpression {
    color: #223B61;
    font-size: 11.5pt;
    font-weight: 600;
}
QLabel#translationEmptyState {
    color: #748196;
    font-size: 11pt;
    padding: 14px;
}
QLabel#pageTitle {
    color: #16233A;
    font-size: 20pt;
    font-weight: 700;
}
QLabel#sectionTitle {
    color: #27364E;
    font-size: 12pt;
    font-weight: 700;
}
QLabel#hintLabel {
    color: #63738A;
    font-size: 11pt;
    line-height: 1.45;
}
QLabel#statusLabel, QLabel#globalStatusLabel {
    color: #63738A;
    font-size: 10.5pt;
    font-weight: 600;
    padding: 4px 0;
}
QLabel#globalStatusLabel { min-width: 170px; text-align: right; }
QLabel#statusLabel[status="loading"], QLabel#globalStatusLabel[status="loading"] { color: #155EEF; }
QLabel#statusLabel[status="success"], QLabel#globalStatusLabel[status="success"] { color: #087443; }
QLabel#statusLabel[status="warning"], QLabel#globalStatusLabel[status="warning"] { color: #A15C00; }
QLabel#statusLabel[status="error"], QLabel#globalStatusLabel[status="error"] { color: #B42318; }
QPlainTextEdit, QTextBrowser, QLineEdit, QComboBox, QListWidget {
    background: #FFFFFF;
    border: 1px solid #D7DFEC;
    border-radius: 8px;
    color: #1F2937;
    font-size: 12pt;
    selection-background-color: #B9D3FF;
}
QPlainTextEdit#translationInput {
    background: #FFFFFF;
    color: #1F2937;
    selection-background-color: #B9D3FF;
    selection-color: #1F2937;
}
QPlainTextEdit#translationInput:disabled { color: #93A1B5; }
QPlainTextEdit, QTextBrowser {
    padding: 12px;
    line-height: 1.55;
}
QPlainTextEdit:focus, QTextBrowser:focus, QLineEdit:focus, QComboBox:focus, QListWidget:focus {
    border: 1px solid #D7DFEC;
}
QLineEdit, QComboBox {
    min-height: 36px;
    padding: 2px 10px;
}
QComboBox::drop-down { border: none; width: 30px; }
QPushButton {
    background: #FFFFFF;
    border: 1px solid #CCD7E7;
    border-radius: 8px;
    color: #334155;
    font-size: 11.5pt;
    font-weight: 600;
    min-height: 38px;
    padding: 0 16px;
}
QPushButton:hover { background: #F0F5FF; border-color: #9BBEFF; }
QPushButton:pressed { background: #E2ECFF; }
QPushButton:disabled { background: #E9EDF4; border-color: #E1E7F0; color: #93A1B5; }
QPushButton#primaryButton {
    background: #155EEF;
    border-color: #155EEF;
    color: #FFFFFF;
    min-height: 42px;
    padding: 0 22px;
}
QPushButton#primaryButton:hover { background: #004EEB; border-color: #004EEB; }
QPushButton#primaryButton:pressed { background: #0040C1; }
QListWidget { padding: 6px; outline: none; }
QListWidget::item {
    border-radius: 8px;
    margin: 3px 0;
}
QListWidget::item:hover { background: #F0F5FF; }
QListWidget::item:selected { background: #DCEAFF; }
QWidget#reviewListRow { background: transparent; }
QLabel#reviewListTitle {
    color: #1A365D;
    font-family: "Segoe UI", "Source Han Sans CN", "Microsoft YaHei UI";
    font-size: 14pt;
    font-weight: 600;
}
QLabel#reviewListMetadata {
    color: #718096;
    font-size: 9.5pt;
}
QSplitter::handle { background: #E6EBF3; width: 1px; }
QSplitter#polishSplitter::handle {
    background: #F5F7FB;
    width: 16px;
}
QScrollBar:vertical { background: transparent; width: 12px; margin: 4px; }
QScrollBar::handle:vertical { background: #C6D0DF; border-radius: 5px; min-height: 28px; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
"""


def set_status(label, text: str, status: str) -> None:
    """Set a semantically styled status label."""
    label.setText(text)
    label.setProperty("status", status)
    label.style().unpolish(label)
    label.style().polish(label)
