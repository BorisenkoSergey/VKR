from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QDialog, QWidget, QLabel, QPushButton, QLineEdit,
    QVBoxLayout, QHBoxLayout, QComboBox, QMessageBox, QSpinBox, QTimeEdit,
    QTabWidget, QTableWidget, QTableWidgetItem, QFileDialog, QCompleter, QLineEdit
)
from PyQt5.QtCore import Qt, QTime
import db


# Главное окно
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Составление учебного расписания")
        self.setFixedSize(400, 200)

        label = QLabel("Добро пожаловать! Выберите или создайте профиль.")
        button = QPushButton("Выбрать / создать профиль")
        button.clicked.connect(self.open_profile_dialog)

        central = QWidget()
        layout = QVBoxLayout(central)
        layout.addWidget(label)
        layout.addWidget(button)
        self.setCentralWidget(central)

    def open_profile_dialog(self):
        dlg = ProfileSelectionDialog(self)
        if dlg.exec_() == QDialog.Accepted:
            profile_id, profile_name = dlg.get_selected_profile()
            ScheduleSelectionDialog(profile_id, profile_name, self).exec_()


# Выбор профиля
class ProfileSelectionDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Выбор профиля")
        self.setFixedSize(400, 200)

        self.selected_profile = None
        layout = QVBoxLayout()
        self.setLayout(layout)
        layout.addWidget(QLabel("Существующие профили:"))

        self.profile_combo = QComboBox()
        self.profile_combo.addItem("-- Выберите профиль --")
        self.profiles = db.list_profiles()
        for pid, name, _ in self.profiles:
            self.profile_combo.addItem(name, userData=pid)
        layout.addWidget(self.profile_combo)

        buttons = QHBoxLayout()
        select_btn = QPushButton("Выбрать профиль")
        create_btn = QPushButton("Создать профиль")
        delete_btn = QPushButton("Удалить профиль")
        buttons.addWidget(select_btn)
        buttons.addWidget(create_btn)
        buttons.addWidget(delete_btn)
        layout.addLayout(buttons)

        select_btn.clicked.connect(self.select_profile)
        create_btn.clicked.connect(self.create_profile)
        delete_btn.clicked.connect(self.delete_profile)

    def select_profile(self):
        index = self.profile_combo.currentIndex()
        if index <= 0:
            QMessageBox.warning(self, "Ошибка", "Сначала выберите профиль из списка.")
            return
        pid = self.profile_combo.currentData()
        name = self.profile_combo.currentText()
        self.selected_profile = (pid, name)
        self.accept()

    def create_profile(self):
        dlg = ProfileCreationDialog(self)
        if dlg.exec_() == QDialog.Accepted:
            self.profile_combo.clear()
            self.profile_combo.addItem("-- Выберите профиль --")
            self.profiles = db.list_profiles()
            for pid, name, _ in self.profiles:
                self.profile_combo.addItem(name, userData=pid)

    def delete_profile(self):
        index = self.profile_combo.currentIndex()
        if index <= 0:
            QMessageBox.warning(self, "Ошибка", "Сначала выберите профиль.")
            return

        pid = self.profile_combo.currentData()
        confirm = QMessageBox.question(self, "Подтверждение", "Удалить выбранный профиль со всеми его расписаниями?",
                                       QMessageBox.Yes | QMessageBox.No)
        if confirm == QMessageBox.Yes:
            db.delete_profile(pid)
            QMessageBox.information(self, "Удалено", "Профиль удалён.")
            self.profile_combo.clear()
            self.profile_combo.addItem("-- Выберите профиль --")
            self.profiles = db.list_profiles()
            for pid, name, _ in self.profiles:
                self.profile_combo.addItem(name, userData=pid)

    def get_selected_profile(self):
        return self.selected_profile


# Создание профиля
class ProfileCreationDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Создание нового профиля")
        self.resize(500, 600)

        self.layout = QVBoxLayout(self)

        self.name_input = QLineEdit()
        self.pair_spin = QSpinBox()
        self.pair_spin.setRange(1, 10)
        self.pair_spin.setValue(6)

        self.layout.addWidget(QLabel("Название профиля:"))
        self.layout.addWidget(self.name_input)

        self.layout.addWidget(QLabel("Максимальное количество занятий в день:"))
        self.layout.addWidget(self.pair_spin)

        self.layout.addWidget(QLabel("Время проведения каждого занятия:"))
        self.time_inputs = []
        self.time_layouts = QVBoxLayout()
        self.layout.addLayout(self.time_layouts)

        self.pair_spin.valueChanged.connect(self.update_time_fields)
        self.update_time_fields(self.pair_spin.value())

        self.save_btn = QPushButton("Сохранить профиль")
        self.save_btn.clicked.connect(self.save_profile)
        self.layout.addWidget(self.save_btn)

    def update_time_fields(self, count):
        for layout in self.time_inputs:
            for i in reversed(range(layout.count())):
                widget = layout.itemAt(i).widget()
                if widget:
                    widget.setParent(None)
        self.time_inputs.clear()

        for i in range(count):
            layout = QHBoxLayout()

            start_edit = QTimeEdit()
            start_edit.setDisplayFormat("HH:mm")
            start_edit.setTime(QTime(9 + i, 0))

            end_edit = QTimeEdit()
            end_edit.setDisplayFormat("HH:mm")
            end_edit.setTime(QTime(10 + i, 30))

            layout.addWidget(QLabel(f"{i+1} занятие:"))
            layout.addWidget(QLabel("Начало"))
            layout.addWidget(start_edit)
            layout.addWidget(QLabel("Конец"))
            layout.addWidget(end_edit)

            self.time_inputs.append(layout)
            self.time_layouts.addLayout(layout)

    def save_profile(self):
        profile_name = self.name_input.text().strip()
        pair_count = self.pair_spin.value()

        if not profile_name:
            QMessageBox.warning(self, "Ошибка", "Введите название профиля.")
            return

        existing_profiles = [p[1] for p in db.list_profiles()]
        if profile_name in existing_profiles:
            QMessageBox.critical(self, "Ошибка", f"Профиль с названием «{profile_name}» уже существует.")
            return

        intervals = []
        prev_end = None

        for i, layout in enumerate(self.time_inputs):
            start_edit = None
            end_edit = None
            for j in range(layout.count()):
                widget = layout.itemAt(j).widget()
                if isinstance(widget, QTimeEdit):
                    if not start_edit:
                        start_edit = widget
                    else:
                        end_edit = widget

            if not start_edit or not end_edit:
                QMessageBox.critical(self, "Ошибка", f"Не удалось найти поля времени для занятия {i + 1}")
                return

            start = start_edit.time()
            end = end_edit.time()

            if start >= end:
                QMessageBox.critical(
                    self,
                    "Ошибка времени",
                    f"У занятия {i + 1} время начала не может быть позже или равно времени окончания."
                )
                return

            if prev_end and start < prev_end:
                QMessageBox.critical(
                    self,
                    "Ошибка пересечения",
                    f"У занятия {i + 1} начало раньше окончания предыдущего занятия."
                )
                return

            intervals.append((i + 1, start.toString("HH:mm"), end.toString("HH:mm")))
            prev_end = end

        profile_id = db.create_profile(profile_name, pair_count)
        db.set_profile_times(profile_id, intervals)

        QMessageBox.information(self, "Готово", "Профиль успешно создан.")
        self.accept()

# Выбор или создание расписания
class ScheduleSelectionDialog(QDialog):
    def __init__(self, profile_id, profile_name, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Расписания для профиля: {profile_name}")
        self.setFixedSize(450, 200)
        self.profile_id = profile_id
        self.profile_name = profile_name

        layout = QVBoxLayout(self)
        self.schedule_combo = QComboBox()
        self.schedule_combo.addItem("-- Выберите расписание --")
        self.refresh_schedules()
        layout.addWidget(QLabel("Список расписаний:"))
        layout.addWidget(self.schedule_combo)

        hlayout = QHBoxLayout()
        self.select_btn = QPushButton("Выбрать расписание")
        self.create_btn = QPushButton("Создать новое расписание")
        self.delete_btn = QPushButton("Удалить расписание")
        hlayout.addWidget(self.select_btn)
        hlayout.addWidget(self.create_btn)
        hlayout.addWidget(self.delete_btn)
        layout.addLayout(hlayout)

        self.select_btn.clicked.connect(self.select_schedule)
        self.create_btn.clicked.connect(self.create_schedule)
        self.delete_btn.clicked.connect(self.delete_schedule)

    def refresh_schedules(self):
        self.schedule_combo.clear()
        self.schedule_combo.addItem("-- Выберите расписание --")
        self.schedules = db.list_schedules(self.profile_id)
        for sid, name, stype in self.schedules:
            self.schedule_combo.addItem(f"{name} ({stype})", userData=(sid, stype))

    def select_schedule(self):
        index = self.schedule_combo.currentIndex()
        if index <= 0:
            QMessageBox.warning(self, "Ошибка", "Выберите расписание из списка.")
            return
        sid, stype = self.schedule_combo.currentData()
        dialog = ScheduleEditDialog(self.profile_id, sid, stype, self)
        dialog.exec_()
        self.accept()

    def create_schedule(self):
        dlg = ScheduleCreationDialog(self.profile_id, self)
        if dlg.exec_() == QDialog.Accepted:
            self.refresh_schedules()

    def delete_schedule(self):
        index = self.schedule_combo.currentIndex()
        if index <= 0:
            QMessageBox.warning(self, "Ошибка", "Выберите расписание.")
            return

        sid, _ = self.schedule_combo.currentData()
        confirm = QMessageBox.question(self, "Подтверждение", "Удалить это расписание?", QMessageBox.Yes | QMessageBox.No)
        if confirm == QMessageBox.Yes:
            db.delete_schedule(sid)
            QMessageBox.information(self, "Удалено", "Расписание удалено.")
            self.refresh_schedules()

# Окно создания расписания
class ScheduleCreationDialog(QDialog):
    def __init__(self, profile_id, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Создание нового расписания")
        self.setFixedSize(400, 200)
        self.profile_id = profile_id

        layout = QVBoxLayout(self)
        self.name_input = QLineEdit()
        self.schedule_type_combo = QComboBox()
        self.schedule_type_combo.addItems(["Обычное", "Двухнедельное"])

        layout.addWidget(QLabel("Название расписания:"))
        layout.addWidget(self.name_input)

        layout.addWidget(QLabel("Тип расписания:"))
        layout.addWidget(self.schedule_type_combo)

        self.create_button = QPushButton("Создать и открыть")
        self.create_button.clicked.connect(self.create_schedule)
        layout.addWidget(self.create_button)

    def create_schedule(self):
        name = self.name_input.text().strip()
        schedule_type = self.schedule_type_combo.currentText()

        if not name:
            QMessageBox.warning(self, "Ошибка", "Введите название расписания.")
            return

        existing_names = [r[1] for r in db.list_schedules(self.profile_id)]
        if name in existing_names:
            QMessageBox.critical(self, "Ошибка", f"Расписание с названием «{name}» уже существует.")
            return

        schedule_id = db.create_schedule(self.profile_id, name, schedule_type)
        QMessageBox.information(self, "Успех", "Расписание создано.")
        self.accept()

        dlg = ScheduleEditDialog(self.profile_id, schedule_id, schedule_type, self)
        dlg.exec_()


class ScheduleEditDialog(QDialog):
    def __init__(self, profile_id, schedule_id, schedule_type, parent=None):
        super().__init__(parent)
        self.profile_id = profile_id
        self.schedule_id = schedule_id
        self.schedule_type = schedule_type
        self.setWindowTitle(f"Редактирование: {schedule_type}")
        self.resize(1100, 650)
        self.setMinimumSize(800, 500)

        self.days = ["Понедельник", "Вторник", "Среда", "Четверг", "Пятница", "Суббота"]
        self.time_intervals = db.get_profile_times(profile_id)
        self.room_list = db.list_rooms()
        self.teacher_list = db.list_teachers()

        layout = QVBoxLayout(self)

        if schedule_type == "Обычное":
            self.table = self.create_table(single=True)
            layout.addWidget(self.table)
        else:
            self.table = self.create_table(single=False)
            layout.addWidget(self.table)

        self.fill_existing_schedule()
        btn_layout = QHBoxLayout()
        self.save_btn = QPushButton("Сохранить расписание")
        self.export_btn = QPushButton("Выгрузить расписание")
        self.save_btn.clicked.connect(self.save_schedule)
        self.export_btn.clicked.connect(self.export_schedule)
        btn_layout.addWidget(self.save_btn)
        btn_layout.addWidget(self.export_btn)

        layout.addLayout(btn_layout)

    def create_table(self, single=True):
        if single:
            headers = ["День", "№ занятия", "Время", "Аудитория", "Вид занятия", "Преподаватель", "Дисциплина"]
            col_count = 7
        else:
            headers = [
                "День", "№ занятия", "Время",
                "Аудитория (Нечет)", "Вид занятия (Нечет)", "Преподаватель (Нечет)", "Дисциплина (Нечет)",
                "Аудитория (Чет)", "Вид занятия (Чет)", "Преподаватель (Чет)", "Дисциплина (Чет)"
            ]
            col_count = 11

        rows = len(self.days) * len(self.time_intervals)
        table = QTableWidget(rows, col_count)
        table.setHorizontalHeaderLabels(headers)

        for d_index, day in enumerate(self.days):
            for p_index, (pair_number, start_time, end_time) in enumerate(self.time_intervals):
                row = d_index * len(self.time_intervals) + p_index

                if p_index == 0:
                    table.setSpan(row, 0, len(self.time_intervals), 1)
                    item = QTableWidgetItem(day)
                    item.setFlags(Qt.ItemIsEnabled)
                    table.setItem(row, 0, item)
                else:
                    table.setItem(row, 0, QTableWidgetItem(""))

                table.setItem(row, 1, QTableWidgetItem(str(pair_number)))
                table.setItem(row, 2, QTableWidgetItem(f"{start_time} - {end_time}"))

                if single:
                    self.add_autocomplete(table, row, 3, self.room_list)
                    table.setItem(row, 4, QTableWidgetItem(""))
                    self.add_autocomplete(table, row, 5, self.teacher_list)
                    table.setItem(row, 6, QTableWidgetItem(""))
                else:
                    self.add_autocomplete(table, row, 3, self.room_list)  # Н
                    table.setItem(row, 4, QTableWidgetItem(""))
                    self.add_autocomplete(table, row, 5, self.teacher_list)
                    table.setItem(row, 6, QTableWidgetItem(""))

                    self.add_autocomplete(table, row, 7, self.room_list)  # Ч
                    table.setItem(row, 8, QTableWidgetItem(""))
                    self.add_autocomplete(table, row, 9, self.teacher_list)
                    table.setItem(row, 10, QTableWidgetItem(""))

        return table

    def add_autocomplete(self, table, row, col, items):
        combo = QComboBox()
        combo.setEditable(True)
        combo.addItems(items)
        completer = QCompleter(items)
        completer.setCaseSensitivity(Qt.CaseInsensitive)
        completer.setFilterMode(Qt.MatchContains)
        combo.setCompleter(completer)
        table.setCellWidget(row, col, combo)

    def get_cell_text(self, table, row, col):
        widget = table.cellWidget(row, col)
        if isinstance(widget, QComboBox):
            return widget.currentText().strip()
        elif isinstance(widget, QLineEdit):
            return widget.text().strip()
        item = table.item(row, col)
        return item.text().strip() if item else ""

    def save_schedule(self):
        data = []
        seen = set()

        last_day = None

        for row in range(self.table.rowCount()):
            day_item = self.table.item(row, 0)
            if day_item and day_item.text().strip():
                last_day = day_item.text().strip()
            day = last_day
            pair_number = int(self.table.item(row, 1).text())

            if self.schedule_type == "Обычное":
                room = self.get_cell_text(self.table, row, 3)
                lesson_type = self.get_cell_text(self.table, row, 4)
                teacher = self.get_cell_text(self.table, row, 5)
                discipline = self.get_cell_text(self.table, row, 6)
                key = (day, pair_number, 0)
                if key in seen:
                    continue
                seen.add(key)

                if room and room not in self.room_list:
                    QMessageBox.critical(self, "Ошибка", f"Аудитория «{room}» не найдена в базе.")
                    return
                if teacher and teacher not in self.teacher_list:
                    QMessageBox.critical(self, "Ошибка", f"Преподаватель «{teacher}» не найден в базе.")
                    return
                if room and db.is_room_busy(room, day, pair_number, 0, self.schedule_id):
                    QMessageBox.critical(self, "Ошибка", f"Аудитория «{room}» занята в {day}, занятие {pair_number}.")
                    return
                if teacher and db.is_teacher_busy(teacher, day, pair_number, 0, self.schedule_id):
                    QMessageBox.critical(self, "Ошибка",
                                         f"Преподаватель «{teacher}» занят в {day}, занятие {pair_number}.")
                    return

                data.append((day, pair_number, room, teacher, lesson_type, discipline, 0))

            else:
                # Нечетная неделя
                room1 = self.get_cell_text(self.table, row, 3)
                ltype1 = self.get_cell_text(self.table, row, 4)
                teach1 = self.get_cell_text(self.table, row, 5)
                disc1 = self.get_cell_text(self.table, row, 6)

                key1 = (day, pair_number, 1)
                if key1 not in seen:
                    seen.add(key1)

                    if room1 and room1 not in self.room_list:
                        QMessageBox.critical(self, "Ошибка", f"Аудитория (нечетная) «{room1}» не найдена в базе.")
                        return
                    if teach1 and teach1 not in self.teacher_list:
                        QMessageBox.critical(self, "Ошибка", f"Преподаватель (нечетная) «{teach1}» не найден в базе.")
                        return
                    if room1 and db.is_room_busy(room1, day, pair_number, 1, self.schedule_id):
                        QMessageBox.critical(self, "Ошибка",
                                             f"Аудитория «{room1}» занята в {day}, занятие {pair_number} (нечетная неделя).")
                        return
                    if teach1 and db.is_teacher_busy(teach1, day, pair_number, 1, self.schedule_id):
                        QMessageBox.critical(self, "Ошибка",
                                             f"Преподаватель «{teach1}» занят в {day}, занятие {pair_number} (нечетная неделя).")
                        return

                    data.append((day, pair_number, room1, teach1, ltype1, disc1, 1))

                # Четная неделя
                room2 = self.get_cell_text(self.table, row, 7)
                ltype2 = self.get_cell_text(self.table, row, 8)
                teach2 = self.get_cell_text(self.table, row, 9)
                disc2 = self.get_cell_text(self.table, row, 10)

                key2 = (day, pair_number, 2)
                if key2 not in seen:
                    seen.add(key2)

                    if room2 and room2 not in self.room_list:
                        QMessageBox.critical(self, "Ошибка", f"Аудитория (четная) «{room2}» не найдена в базе.")
                        return
                    if teach2 and teach2 not in self.teacher_list:
                        QMessageBox.critical(self, "Ошибка", f"Преподаватель (четная) «{teach2}» не найден в базе.")
                        return
                    if room2 and db.is_room_busy(room2, day, pair_number, 2, self.schedule_id):
                        QMessageBox.critical(self, "Ошибка", f"Аудитория «{room2}» занята в {day}, занятие {pair_number} (четная неделя).")
                        return
                    if teach2 and db.is_teacher_busy(teach2, day, pair_number, 2, self.schedule_id):
                        QMessageBox.critical(self, "Ошибка", f"Преподаватель «{teach2}» занят в {day}, занятие {pair_number} (четная неделя).")
                        return
                    data.append((day, pair_number, room2, teach2, ltype2, disc2, 2))
        try:
            db.save_schedule_entries(self.schedule_id, data)
            QMessageBox.information(self, "Успех", "Расписание сохранено.")
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Ошибка при сохранении: {e}")

    def export_schedule(self):
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Сохранить в Excel",
            f"расписание_{self.schedule_id}.xlsx",
            "Excel (*.xlsx)"
        )
        if path:
            try:
                success = db.export_schedule_to_excel(self.schedule_id, path)
                if success:
                    QMessageBox.information(self, "Готово", "Расписание экспортировано.")
                else:
                    QMessageBox.critical(self, "Ошибка", "Не удалось экспортировать.")
            except Exception as e:
                QMessageBox.critical(self, "Ошибка", f"Ошибка экспорта: {e}")

    def fill_existing_schedule(self):
        entries = db.load_schedule_entries(self.schedule_id)
        table = self.table

        for row_data in entries:
            day, pair_number, room, teacher, lesson_type, discipline, week_type = row_data

            day_index = self.days.index(day)
            row = day_index * len(self.time_intervals) + (pair_number - 1)

            if self.schedule_type == "Обычное":
                table.cellWidget(row, 3).setCurrentText(room or "")
                table.setItem(row, 4, QTableWidgetItem(lesson_type or ""))
                table.cellWidget(row, 5).setCurrentText(teacher or "")
                table.setItem(row, 6, QTableWidgetItem(discipline or ""))
            else:
                if week_type == 1:  # Нечетная
                    table.cellWidget(row, 3).setCurrentText(room or "")
                    table.setItem(row, 4, QTableWidgetItem(lesson_type or ""))
                    table.cellWidget(row, 5).setCurrentText(teacher or "")
                    table.setItem(row, 6, QTableWidgetItem(discipline or ""))
                elif week_type == 2:  # Четная
                    table.cellWidget(row, 7).setCurrentText(room or "")
                    table.setItem(row, 8, QTableWidgetItem(lesson_type or ""))
                    table.cellWidget(row, 9).setCurrentText(teacher or "")
                    table.setItem(row, 10, QTableWidgetItem(discipline or ""))