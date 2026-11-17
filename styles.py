
def get_stylesheet(theme="dark"):

    if theme == "light":
        return """
        QMainWindow, QWidget {
            background-color: #f2f4f8;
            color: #202735;
            font-family: "Segoe UI";
            font-size: 13px;
        }

        QLabel#mainTitle {
            color: #202735;
            font-size: 30px;
            font-weight: 800;
            letter-spacing: 2px;
        }

        QLabel#mainSubtitle {
            color: #7b8494;
            font-size: 10px;
            font-weight: bold;
            letter-spacing: 3px;
        }

        QLabel#sectionTitle {
            color: #697487;
            font-size: 11px;
            font-weight: bold;
            letter-spacing: 1.5px;
            padding-top: 8px;
        }

        QLabel#connectionStatus {
            color: #32845f;
            background-color: #e1f3e9;
            border: 1px solid #c5e7d3;
            border-radius: 7px;
            padding: 9px 12px;
        }

        QFrame#temperatureCard {
            background-color: #ffffff;
            border: 1px solid #dfe4ed;
            border-radius: 13px;
        }

        QLabel#cardTitle {
            color: #697487;
            font-size: 11px;
            font-weight: bold;
            letter-spacing: 1px;
        }

        QLabel#temperatureValue {
            font-size: 34px;
            font-weight: bold;
        }

        QLabel#sensorStatus {
            color: #929baa;
            font-size: 11px;
        }

        QFrame#usageCard {
            background-color: #ffffff;
            border: 1px solid #dfe4ed;
            border-radius: 10px;
        }

        QLabel#usageTitle {
            color: #7b8494;
            font-size: 10px;
            font-weight: bold;
        }

        QLabel#usageValue {
            color: #202735;
            font-size: 23px;
            font-weight: bold;
        }

        QFrame#driveRow {
            background-color: #ffffff;
            border: 1px solid #dfe4ed;
            border-radius: 8px;
        }

        QLabel#driveName {
            color: #303949;
            font-size: 12px;
            font-weight: bold;
        }

        QLabel#driveTemperature {
            color: #328b6c;
            font-size: 15px;
            font-weight: bold;
        }

        QLabel#emptyMessage {
            color: #929baa;
            padding: 12px;
        }

        QLabel#settingLabel {
            color: #596476;
            font-weight: bold;
        }

        QLabel#footerLabel {
            color: #929baa;
            font-size: 10px;
            padding-top: 8px;
        }

        QPushButton {
            background-color: #e5eaf2;
            color: #263143;
            border: 1px solid #d4dce8;
            border-radius: 7px;
            padding: 9px 15px;
            font-weight: bold;
        }

        QPushButton:hover {
            background-color: #d8e2f1;
        }

        QPushButton:pressed {
            background-color: #cbd7e8;
        }

        QPushButton#themeButton {
            background-color: #ffffff;
        }

        QKeySequenceEdit {
            background-color: #ffffff;
            color: #202735;
            border: 1px solid #d4dce8;
            border-radius: 7px;
            padding: 7px;
            min-width: 110px;
        }

        QScrollArea {
            border: none;
            background-color: transparent;
        }

        QScrollBar:vertical {
            background-color: #e8ecf2;
            width: 9px;
            margin: 2px;
            border-radius: 4px;
        }

        QScrollBar::handle:vertical {
            background-color: #b6c0cf;
            min-height: 25px;
            border-radius: 4px;
        }

        QScrollBar::add-line:vertical,
        QScrollBar::sub-line:vertical {
            height: 0px;
        }
        """

    return """
    QMainWindow, QWidget {
        background-color: #11141b;
        color: #e7eaf0;
        font-family: "Segoe UI";
        font-size: 13px;
    }

    QLabel#mainTitle {
        color: #f0f3f8;
        font-size: 30px;
        font-weight: 800;
        letter-spacing: 2px;
    }

    QLabel#mainSubtitle {
        color: #788397;
        font-size: 10px;
        font-weight: bold;
        letter-spacing: 3px;
    }

    QLabel#sectionTitle {
        color: #9ba6b8;
        font-size: 11px;
        font-weight: bold;
        letter-spacing: 1.5px;
        padding-top: 8px;
    }

    QLabel#connectionStatus {
        color: #65d6a5;
        background-color: #192b27;
        border: 1px solid #29483d;
        border-radius: 7px;
        padding: 9px 12px;
    }

    QFrame#temperatureCard {
        background-color: #1a1f29;
        border: 1px solid #2a3240;
        border-radius: 13px;
    }

    QLabel#cardTitle {
        color: #9ba6b8;
        font-size: 11px;
        font-weight: bold;
        letter-spacing: 1px;
    }

    QLabel#temperatureValue {
        font-size: 34px;
        font-weight: bold;
    }

    QLabel#sensorStatus {
        color: #778398;
        font-size: 11px;
    }

    QFrame#usageCard {
        background-color: #1a1f29;
        border: 1px solid #2a3240;
        border-radius: 10px;
    }

    QLabel#usageTitle {
        color: #8e9aaf;
        font-size: 10px;
        font-weight: bold;
    }

    QLabel#usageValue {
        color: #edf1f8;
        font-size: 23px;
        font-weight: bold;
    }

    QFrame#driveRow {
        background-color: #1a1f29;
        border: 1px solid #2a3240;
        border-radius: 8px;
    }

    QLabel#driveName {
        color: #d8deea;
        font-size: 12px;
        font-weight: bold;
    }

    QLabel#driveTemperature {
        color: #55d6a0;
        font-size: 15px;
        font-weight: bold;
    }

    QLabel#emptyMessage {
        color: #778398;
        padding: 12px;
    }

    QLabel#settingLabel {
        color: #b4bdcc;
        font-weight: bold;
    }

    QLabel#footerLabel {
        color: #68758a;
        font-size: 10px;
        padding-top: 8px;
    }

    QPushButton {
        background-color: #252d3a;
        color: #e7ebf2;
        border: 1px solid #354052;
        border-radius: 7px;
        padding: 9px 15px;
        font-weight: bold;
    }

    QPushButton:hover {
        background-color: #303c4e;
    }

    QPushButton:pressed {
        background-color: #1e2632;
    }

    QPushButton#themeButton {
        background-color: #202a38;
    }

    QKeySequenceEdit {
        background-color: #1a1f29;
        color: #e7eaf0;
        border: 1px solid #354052;
        border-radius: 7px;
        padding: 7px;
        min-width: 110px;
    }

    QScrollArea {
        border: none;
        background-color: transparent;
    }

    QScrollBar:vertical {
        background-color: #171c25;
        width: 9px;
        margin: 2px;
        border-radius: 4px;
    }

    QScrollBar::handle:vertical {
        background-color: #39465a;
        min-height: 25px;
        border-radius: 4px;
    }

    QScrollBar::add-line:vertical,
    QScrollBar::sub-line:vertical {
        height: 0px;
    }
    """
