from aiogram.fsm.state import State, StatesGroup


# FSM States
class UploadSession(StatesGroup):
    """
    Конечный автомат для загрузки сессии

    Состояния:
    waiting_for_session - ожидание загрузки файла сессии
    """
    waiting_for_session = State()


class AdminSettings(StatesGroup):
    """
    Конечный автомат для настроек администратора

    Состояния:
    waiting_for_channel - ожидание ввода канала
    waiting_for_interval - ожидание ввода интервала
    """
    waiting_for_channel = State()
    waiting_for_interval = State()
