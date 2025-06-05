import psycopg2
import pandas as pd

DB_PARAMS = {
    "dbname": "postgres",
    "user": "postgres",
    "password": "0000",
    "host": "localhost",
    "port": 5433,
}

def get_connection():
    return psycopg2.connect(**DB_PARAMS)

# Профили
def create_profile(name: str, max_pairs: int) -> int:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO profiles (name, max_pairs) VALUES (%s, %s) RETURNING id;",
                (name, max_pairs)
            )
            profile_id = cur.fetchone()[0]
            conn.commit()
            return profile_id

def list_profiles() -> list:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT id, name, max_pairs FROM profiles ORDER BY id;")
            return cur.fetchall()

# Интервалы пар
def set_profile_times(profile_id: int, intervals: list):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM profile_times WHERE profile_id = %s;", (profile_id,))
            cur.executemany(
                """
                INSERT INTO profile_times (profile_id, pair_number, start_time, end_time)
                VALUES (%s, %s, %s, %s);
                """,
                [(profile_id, num, st, et) for num, st, et in intervals]
            )
        conn.commit()

def get_profile_times(profile_id: int) -> list:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT pair_number, start_time, end_time
                FROM profile_times
                WHERE profile_id = %s
                ORDER BY pair_number;
                """,
                (profile_id,)
            )
            return cur.fetchall()

# Справочники
def list_rooms() -> list:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT name FROM rooms ORDER BY name;")
            return [r[0] for r in cur.fetchall()]

def list_teachers() -> list:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT name FROM teachers ORDER BY name;")
            return [t[0] for t in cur.fetchall()]

def get_room_id(name: str) -> int:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT id FROM rooms WHERE name = %s;", (name,))
            r = cur.fetchone()
            return r[0] if r else None

def get_teacher_id(name: str) -> int:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT id FROM teachers WHERE name = %s;", (name,))
            t = cur.fetchone()
            return t[0] if t else None

# Расписания
def list_schedules(profile_id: int) -> list:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, name, schedule_type FROM schedules_list WHERE profile_id = %s ORDER BY id;",
                (profile_id,)
            )
            return cur.fetchall()

def create_schedule(profile_id: int, name: str, schedule_type: str) -> int:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO schedules_list (profile_id, name, schedule_type)
                VALUES (%s, %s, %s) RETURNING id;
                """,
                (profile_id, name, schedule_type)
            )
            sid = cur.fetchone()[0]
            conn.commit()
            return sid

def save_schedule_entries(schedule_id: int, entries: list):
    """
    entries = [
      (day_of_week:str, pair_number:int, room:str, teacher:str,
       lesson_type:str, discipline:str, week_type:int)
    ]
    """
    try:
        with get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("DELETE FROM schedules WHERE schedule_id = %s;", (schedule_id,))

                for row in entries:
                    day, pair_number, room, teacher, lesson_type, discipline, week_type = row

                    room_id = get_room_id(room.strip()) if room else None
                    teacher_id = get_teacher_id(teacher.strip()) if teacher else None

                    cursor.execute(
                        """
                        SELECT start_time, end_time
                        FROM profile_times
                        WHERE profile_id = (
                            SELECT profile_id FROM schedules_list WHERE id = %s
                        ) AND pair_number = %s;
                        """,
                        (schedule_id, pair_number)
                    )
                    result = cursor.fetchone()
                    if not result:
                        continue
                    start_time, end_time = result
                    time_interval = f"{start_time.strftime('%H:%M')} - {end_time.strftime('%H:%M')}"
                    cursor.execute("""
                        INSERT INTO schedules (
                          schedule_id, week_day, pair_number,
                          room_id, teacher_id, lesson_type,
                          discipline, week_type, time_interval
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s);
                    """, (
                        schedule_id, day, pair_number,
                        room_id, teacher_id, lesson_type or "",
                        discipline or "", week_type, time_interval
                    ))

        conn.commit()
    except Exception as e:
        print(f"[Ошибка сохранения]: {e}")
        raise

def delete_profile(profile_id):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM schedules WHERE schedule_id IN (SELECT id FROM schedules_list WHERE profile_id = %s);", (profile_id,))
            cur.execute("DELETE FROM schedules_list WHERE profile_id = %s;", (profile_id,))
            cur.execute("DELETE FROM profile_times WHERE profile_id = %s;", (profile_id,))
            cur.execute("DELETE FROM profiles WHERE id = %s;", (profile_id,))
        conn.commit()

def delete_schedule(schedule_id):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM schedules WHERE schedule_id = %s;", (schedule_id,))
            cur.execute("DELETE FROM schedules_list WHERE id = %s;", (schedule_id,))
        conn.commit()

# Загрузка
def load_schedule_entries(schedule_id: int) -> list:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT
                  s.week_day, s.pair_number,
                  r.name AS room_name,
                  t.name AS teacher_name,
                  s.lesson_type, s.discipline, s.week_type
                FROM schedules s
                LEFT JOIN rooms r ON s.room_id = r.id
                LEFT JOIN teachers t ON s.teacher_id = t.id
                WHERE s.schedule_id = %s;
            """, (schedule_id,))
            return cur.fetchall()

# Экспорт

def export_schedule_to_excel(schedule_id: int, path: str) -> bool:
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT schedule_type FROM schedules_list WHERE id = %s;", (schedule_id,))
                schedule_type = cur.fetchone()[0]

                cur.execute("""
                    SELECT s.week_day, s.pair_number, s.week_type,
                           COALESCE(r.name, '') AS room,
                           COALESCE(s.lesson_type, '') AS lesson_type,
                           COALESCE(t.name, '') AS teacher,
                           COALESCE(s.discipline, '') AS discipline,
                           pt.start_time, pt.end_time
                    FROM schedules s
                    LEFT JOIN rooms r ON r.id = s.room_id
                    LEFT JOIN teachers t ON t.id = s.teacher_id
                    JOIN profile_times pt ON pt.profile_id = (SELECT profile_id FROM schedules_list WHERE id = %s)
                                           AND pt.pair_number = s.pair_number
                    WHERE s.schedule_id = %s
                    ORDER BY s.week_day, s.pair_number, s.week_type;
                """, (schedule_id, schedule_id))
                rows = cur.fetchall()

        if schedule_type == "Обычное":
            columns = ["День недели", "№ занятия", "Время", "Аудитория", "Вид занятия", "Преподаватель", "Дисциплина"]
            data = []
            for row in rows:
                if row[2] != 0:
                    continue
                day, pair, _, room, ltype, teacher, disc, start, end = row
                time_range = f"{start} - {end}"
                data.append([day, pair, time_range, room, ltype, teacher, disc])

        else:
            columns = [
                "День недели", "№ занятия", "Время",
                "Аудитория (Нечет)", "Вид занятия (Нечет)", "Преподаватель (Нечет)", "Дисциплина (Нечет)",
                "Аудитория (Чет)", "Вид занятия (Чет)", "Преподаватель (Чет)", "Дисциплина (Чет)"
            ]
            grouped = {}
            for row in rows:
                day, pair, week, room, ltype, teacher, disc, start, end = row
                key = (day, pair, f"{start} - {end}")
                if key not in grouped:
                    grouped[key] = [None, None]
                if week == 1:
                    grouped[key][0] = [room, ltype, teacher, disc]
                elif week == 2:
                    grouped[key][1] = [room, ltype, teacher, disc]

            data = []
            for (day, pair, time_range), (week1, week2) in grouped.items():
                row = [day, pair, time_range]
                row += week1 if week1 else [""] * 4
                row += week2 if week2 else [""] * 4
                data.append(row)

        df = pd.DataFrame(data, columns=columns)
        df.to_excel(path, index=False)
        return True
    except Exception as e:
        print(f"Ошибка экспорта: {e}")
        return False


# Проверка занятости аудитории
def is_room_busy(room_name, day, pair_number, week_type, schedule_id):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT 1 FROM schedules s
                JOIN rooms r ON s.room_id = r.id
                WHERE r.name = %s AND s.week_day = %s AND s.pair_number = %s
                AND s.week_type = %s AND s.schedule_id != %s
                LIMIT 1;
            """, (room_name, day, pair_number, week_type, schedule_id))
            return cur.fetchone() is not None

# Проверка занятости преподавателя
def is_teacher_busy(teacher_name, day, pair_number, week_type, schedule_id):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT 1 FROM schedules s
                JOIN teachers t ON s.teacher_id = t.id
                WHERE t.name = %s AND s.week_day = %s AND s.pair_number = %s
                AND s.week_type = %s AND s.schedule_id != %s
                LIMIT 1;
            """, (teacher_name, day, pair_number, week_type, schedule_id))
            return cur.fetchone() is not None


