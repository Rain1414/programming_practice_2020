"""
В данном модуле описана система, которая будет вести учёт бортового оборудования для радиосвязи и
учёт использования этого оборудования.
"""
from copy import deepcopy
from typing import List, Dict, NamedTuple, Optional, Type
from enum import Enum
import numpy as np
from dataclasses import dataclass
from global_system import RadioTransmissionMediumConsumer
from auxiliary_classes import Radiosignal, FrequencyType, ListenEtherTask, MemoryBlock


class CommunicationModeType(Enum):
    """
    Тип, задающий режим работы приёмо-передающего устройства (ППУ) - антенны.
    Доступно 5 режимов:
    1) "TRANSMISSION" - ППУ в этом режиме передаёт сигнал
    2) "RECEPTION" - ППУ в этом режиме принимает сигнал
    3) "RELAYING_IN" - ППУ в режиме ретрансляции принимает сигнал
    4) "RELAYING_OUT" - ППУ в режиме ретрансляции передаёт сигнал
    5) "FREE" - режим не назначен
    """
    TRANSMISSION = "TRANSMISSION"
    RECEPTION = "RECEPTION"
    RELAYING_IN = "RELAYING_IN"
    RELAYING_OUT = "RELAYING_OUT"
    FREE = "FREE"


class RadiotransmissionConsumerProperties:
    """
    Класс свойств локального Потребителя ресурсов Системы радиосвязи.
    """
    def __init__(self, frequency):
        self.frequency: FrequencyType = frequency  # частота несущей [МГц]


class RadiotransmissionConsumer:
    """
    Класс локального Потребителя ресурсов Системы радиосвязи.
    """

    def __init__(self, properties: 'RadiotransmissionConsumerProperties'):
        self.__properties = properties

        # Словарь: ключи - id приёмника, которому необходимо отправить сигнал,
        # значения - список сигналов с информацией, которые предназначены для данного приёмника
        self.dict_id_receiver_signals_to_send: Dict[int, List[Radiosignal]] = {}

        # Список каналов, на которых может работать Потребитель для приёма сигнала и ретрансляции
        self.listen_ether_tasks: List[ListenEtherTask] = []

        # Локальная Система радиосвязи (для метода get_antennas_info, get_antennas_signals, assign_device_as...)
        self.radiotransmission_system: Optional[RadiotransmissionSystem] = None

    @property
    def properties(self):
        return self.__properties

    @properties.setter
    def properties(self, properties):
        self.__properties = deepcopy(properties)

    def receive_signal(self, frequency: Optional[FrequencyType] = None) -> List[MemoryBlock]:
        pass

    def clear_tasks(self):
        """
        Метод, вызываемый в конце каждого имитационного шага системы среды радиосвязи после того,
        как все сигналы от передатчиков были отправлены.
        Очищает словарь сигналов, отправленных с передатчика, и список каналов, которыми пользовался Потребитель
        для приёма сигналов и ретрансляции.
        """
        self.dict_id_receiver_signals_to_send = {}
        self.listen_ether_tasks = []

    def release(self):
        """
        Метод, который следует вызвать, если потребление ресурсов больше не нужно.
        """
        self.dict_id_receiver_signals_to_send = {}

    def send_signal(self, id_receiver: int, memory: MemoryBlock, frequency: FrequencyType) -> Radiosignal:
        """
        Метод, который вызывается Потребителем, когда он хочет отправить сигнал.

        :param id_receiver: id приёмника
        :param memory: блок памяти, в котором хранится сигнал
        :param frequency: частота, на которой нужно передать сигнал
        :return: True, если удалось отправить сигнал, False - в противном случае
        """
        # Создаём сигнал
        # id_transmitter=-1 - заглушка. При передаче сигнала глобальному Потребителю будет назначен id данного КА
        signal = Radiosignal(id_transmitter=-1, id_receiver=id_receiver, memory=memory, frequency=frequency)
        self.dict_id_receiver_signals_to_send.setdefault(id_receiver, ([]))
        self.dict_id_receiver_signals_to_send[id_receiver].append(signal)
        return signal

    def listen_ether(self, frequency_recipiency: Optional[FrequencyType] = None) -> bool:
        """
        Потребитель заявляет, что он слушает эфир на заданной частоте frequency.
        Если этот метод не был выполнен, то сигнал не сможет быть получен, даже если передавался.
        Добавляем в список каналов прослушки Потребителя новый канал с заданной частотой frequency.

        :param frequency_recipiency: частота на которой слушается эфир.
        :return: True - если удалось создать канал прослушки с заданнымми требованиями; False - в противном случае
        """
        # Проверяем, есть ли уже данный канал в списке каналов прослушки
        if ListenEtherTask(frequency_recipiency=(
                frequency_recipiency or self.__properties.frequency)) not in self.listen_ether_tasks:
            # Добавляем в список каналов прослушки новый канал с заданной частотой
            self.listen_ether_tasks.append(
                ListenEtherTask(frequency_recipiency=(frequency_recipiency or self.__properties.frequency)))
            return True
        else:
            return False

    def i_am_repeater(self, id_destination_relay: int,
                      frequency_recipiency: Optional[FrequencyType] = None,
                      frequency_transmission_relay: Optional[FrequencyType] = None,
                      save_relayed_signals_locally_relay: bool = False) -> bool:
        """
        Вызывается Потребителем, когда он хочет создать канал радиосвязи для ретрансляции данных.

        :param id_destination_relay: id приёмника, на который будет ретранслироваться сигнал
        :param frequency_recipiency: частота, на которой ретранслятор принимает сигналы
        :param frequency_transmission_relay: частота, на которой ретранслятор передаёт сигналы
        :param save_relayed_signals_locally_relay: индикатор, отвечающий за то,
                                                   будут ли в локальных Потребителях радиосвязи
                                                   сохраняться ретранслируемые сигналы
        :return: True, если канал был создан; False - в противном случае
        """
        # Проверяем, что данного канала уже нет в списке прослушки
        if ListenEtherTask(
                frequency_recipiency=frequency_recipiency or self.__properties.frequency,
                frequency_transmission_relay=frequency_transmission_relay or self.__properties.frequency,
                id_destination_relay=id_destination_relay,
                save_relayed_signals_locally_relay=save_relayed_signals_locally_relay) in self.listen_ether_tasks:
            return False
        else:
            self.listen_ether_tasks.append(ListenEtherTask(
                frequency_recipiency=frequency_recipiency or self.__properties.frequency,
                frequency_transmission_relay=frequency_transmission_relay or self.__properties.frequency,
                id_destination_relay=id_destination_relay,
                save_relayed_signals_locally_relay=save_relayed_signals_locally_relay))
            return True

    def get_antennas_signals(self, id_antenna: int) -> List[MemoryBlock]:
        """
        Возвращает сигналы, которые были приняты антенной с id_antenna.

        :param id_antenna: id антенны, которая слушала эфир на своей частоте
        :return: список сигналов, принятых антенной
        """
        assert self.radiotransmission_system is not None
        if self.radiotransmission_system is None:
            raise Exception('''Attribute radiotransmission_system is None.
            Should be class object Radiotransmission system''')
        return self.radiotransmission_system.dict_id_device_memory_blocks_to_receive.get(id_antenna, [])

    def assign_device_as_transmitter(self, memory_block: MemoryBlock, id_antenna: int,
                                     id_receiver: int, frequency: Optional[FrequencyType] = None,
                                     id_antenna_receiver: Optional[int] = None) -> bool:
        """
        Метод, для назначения приёмо-передающего устройства на отправку сигнала.
        Если этот метод не был вызван, соответствующий сигнал не будет передан от локальной системы радиосвязи
        в глобальную.

        :param memory_block: блок памяти, который нужно отправить с данного КА
        :param id_antenna: id ППУ, который должен отправить сигнал
        :param id_receiver: id приёмника
        :param frequency: частота, на которой нужно передать сигнал
        :param id_antenna_receiver: id антенны приёмника, которая должна принять сигнал
        """
        # Игнорируем ошибки Too many arguments
        # pylint: disable=R0913

        assert self.radiotransmission_system is not None
        if self.radiotransmission_system is None:
            raise Exception('''Attribute radiotransmission_system is None.
            Should be class object Radiotransmission system''')
        return self.radiotransmission_system.assign_device_as_transmitter(memory_block=memory_block,
                                                                          id_antenna=(
                                                                              id_antenna),
                                                                          id_receiver=id_receiver,
                                                                          frequency=frequency,
                                                                          id_antenna_receiver=id_antenna_receiver)

    def assign_device_as_receiver(self, id_antenna: int,
                                  frequency: Optional[FrequencyType] = None) -> bool:
        """
        Метод, для назначения приёмо-передающего устройства на приём сигнала.
        Если этот метод не был вызван, соответствующий сигнал не будет передан от локальной системы радиосвязи
        в глобальную.

        :param id_antenna: id ППУ, который должен принять сигнал
        :param frequency: частота, на которой нужно принимать сигнал
        """
        assert self.radiotransmission_system is not None
        if self.radiotransmission_system is None:
            raise Exception('''Attribute radiotransmission_system is None.
            Should be class object Radiotransmission system''')
        return self.radiotransmission_system.assign_device_as_receiver(id_antenna, frequency)

    def assign_device_as_repeater(self, id_antenna_in: int, id_antenna_out: int,
                                  id_destination_relay: int, id_antenna_destination_relay: Optional[int] = None,
                                  frequency_in: Optional[FrequencyType] = None,
                                  frequency_out: Optional[FrequencyType] = None,
                                  save_relayed_signals_locally_relay: bool = False) -> bool:
        """
        Метод, для назначения приёмо-передающего устройства на ретрансляцию сигнала.
        Если этот метод не был вызван, соответствующий сигнал не будет передан от локальной системы радиосвязи
        в глобальную.

        :param id_antenna_in: id ППУ, который должен принять ретранслируемый сигнал
        :param id_antenna_out: id ППУ, который должен отправить ретранслируемый сигнал
        :param id_destination_relay: id приёмника, на который нацелен ретранслятор
        :param id_antenna_destination_relay: id антенны приёмника, на которую будет отправлен сигнал при ретрансляции
        :param frequency_in: частота, на которой нужно принимать ретранслируемый сигнал
        :param frequency_out: частота, на которой нужно отправлять ретранслируемый сигнал
        :param save_relayed_signals_locally_relay: индикатор, отвечающий за то,
                                                   будут ли в локальных Потребителях радиосвязи
                                                   сохраняться ретранслируемые сигналы
        """
        # Игнорируем ошибки Too many arguments
        # pylint: disable=R0913

        assert self.radiotransmission_system is not None
        if self.radiotransmission_system is None:
            raise Exception('''Attribute radiotransmission_system is None.
            Should be class object Radiotransmission system''')
        return self.radiotransmission_system.assign_device_as_repeater(
            id_antenna_in=id_antenna_in,
            id_antenna_out=id_antenna_out,
            id_destination_relay=id_destination_relay,
            id_antenna_destination_relay=id_antenna_destination_relay,
            frequency_in=frequency_in,
            frequency_out=frequency_out,
            save_relayed_signals_locally_relay=save_relayed_signals_locally_relay)

    match_database_table = {"guid_time": "Время наведения",
                            "channel_capacity_transmit": "Пропускная способность на передачу",
                            "channel_capacity_receive": "Пропускная способность на прием",
                            "frequency_range_min": "Левая граница диапазона частот",
                            "frequency_range_max": "Правая граница диапазона частот",
                            "consumption": "Мощность потребляемая",
                            "mass": "Масса",
                            "koef_receive": "Коэффициент потери для приема",
                            "koef_transmit": "Коэффициент потери для передачи",
                            "receive_power_consumption": "Потери в принимающем тракте",
                            "transmit_power_consumption": "Потери в передающем тракте",
                            "receive_radio_noise": "Отношение сигнал/шум",
                            "network_id": "Маркер антенны в сети",
                            "offset_angle": "Угол раскрытия сигнала антенны",
                            "consumption_transmission": "Потребление мощности при передаче сигнала",
                            "consumption_reception": "Потребление мощности при приеме сигнала"}


@dataclass()
class TransmitReceiveDeviceProperties:
    """
    Класс свойств приёмо-передающего устройства (ППУ).
    """
    # Игнорируем ошибки Too many instance attributes
    # pylint: disable=R0902

    channel_capacity_transmit: float  # пропускная способность приёмо-передающего тракта на передачу [МБит/с]
    channel_capacity_receive: float  # пропускная способность приёмо-передающего тракта на приём [МБит/с]
    frequency_range_min: FrequencyType  # левая граница диапазона частот, в которой передаёт сигнал данный тракт [МГц]
    frequency_range_max: FrequencyType  # правая граница диапазона частот, в которой передаёт сигнал данный тракт [Мгц]

    consumption: float  # мощность потребления электроэнергии
    mass: float  # масса ППУ

    guid_time: float  # Время наведения
    koef_receive: float  # коэффициент потери для приема Вт/м^2
    koef_transmit: float  # коэффициент потери для передачи Вт/м^2
    receive_power_consumption: float  # потери в принимающем траекте Вт
    transmit_power_consumption: float  # потери в передающем тракте Вт
    receive_radio_noise: float  # Отношение сигнал/шум
    network_id: Optional[int] = None  # маркер антенны в сети
    offset_angle: float = np.pi / 4  # угол раскрытия сигнала антнеты

    # Нельзя пока что написать Optional, так как из-за integral_d\satellite_storage\properties_object.py
    # вылазит ошибка
    # E       TypeError: Cannot instantiate typing.Union
    consumption_transmission: Optional[float] = None  # потребление мощности при передаче сигнала
    consumption_reception: Optional[float] = None  # потребление мощности при приёме сигнала

    def __post_init__(self):
        # Должно выполняться: frequency_range_min <= frequency_range_max
        if self.frequency_range_min > self.frequency_range_max:
            raise Exception('''Must be frequency_range_min <= frequency_range_max. Now frequency_range_min = %f,
            frequency_range_max = %f''', self.frequency_range_min, self.frequency_range_max)
        # Если потребление при передаче не задано, то задаём его значением consumption
        if self.consumption_transmission is None:
            self.consumption_transmission = self.consumption
        # Если потребление при приёме не задано, то задаём его значением consumption
        if self.consumption_reception is None:
            self.consumption_reception = self.consumption


class TransmitReceiveDevice:
    """
    Класс приёмо-передающего устройства (ППУ).
    Моделирует комбинацию антенна-усилитель.
    """
    # Игнорируем ошибки Too many instance attributes
    # pylint: disable=R0902

    def __init__(self,
                 id_antenna: int,
                 properties: TransmitReceiveDeviceProperties):
        # id ППУ
        self.__id_antenna = id_antenna

        self.__properties = deepcopy(properties)

        # Рабочая частота ППУ. Изначально задаётся как среднее в диапазоне. Изменяется с помощью метода set_frequency
        self.__frequency: FrequencyType = FrequencyType(
            (self.properties.frequency_range_max + self.properties.frequency_range_min) / 2)

        # Режим работы ППУ (передача/приём/передача при ретрансляции/приём при ретрансляции). Изначально не задан
        self.communication_mode: CommunicationModeType = CommunicationModeType.FREE

    @property
    def id_antenna(self):
        return self.__id_antenna

    @property
    def properties(self):
        return self.__properties

    @property
    def frequency(self):
        return self.__frequency

    def set_frequency(self, frequency: FrequencyType):
        """
        Устанавливает рабочую частоту антенны приёмо-передающего устройства.
        Должно выполняться: frequency_range_min <= frequency <= frequency_range_max

        :param frequency: частота, на которую настроена антенна
        """
        if frequency < self.properties.frequency_range_min:
            raise Exception('''Must be: frequency >= frequency_range_min. Now frequency = %f,
            frequency_range_min = %f''', self.frequency, self.properties.frequency_range_min)
        elif frequency > self.properties.frequency_range_max:
            raise Exception('''Must be: frequency <= frequency_range_max. Now frequency = %f,
            frequency_range_min = %f''', self.frequency, self.properties.frequency_range_max)

        self.__frequency = frequency

    def set_consumption(self):
        """
        Установка мощности, потребляемой устройством на протяжении всего данного шага моделирования.
        Между шагами устанавливается значение, переданное при создании потребителя мощности.

        Задаётся в зависимости от текущего режима работы антенны CommunicationModeType
        """
        if self.communication_mode == CommunicationModeType.TRANSMISSION or (
                self.communication_mode == CommunicationModeType.RELAYING_OUT):
            # Убрал, так как для этого нужен доступ к другим модулям
            # self.__energy_consumer.set_consumption(self.properties.consumption_transmission)
            return
        elif self.communication_mode == CommunicationModeType.RECEPTION or (
                self.communication_mode == CommunicationModeType.RELAYING_IN):
            # Убрал, так как для этого нужен доступ к другим модулям
            # self.__energy_consumer.set_consumption(self.properties.consumption_reception)
            return


class RelayChannel(NamedTuple):
    """
    Класс, отвечающий каналу, предназначенному для ретрансляции данных
    """
    # ППУ для приёма сигналов
    antenna_in: TransmitReceiveDevice
    # ППУ для отправки сигналов
    antenna_out: TransmitReceiveDevice
    # id КА, куда ретранслируется сигнал
    id_destination_relay: int
    # id антенны КА, на которую ретранслируется сигнал
    id_antenna_destination_relay: Optional[int] = None
    # индикатор, отвечающий за то, будут ли в локальных Потребителях радиосвязи сохраняться ретранслируемые сигналы.
    # "True" - будут, "False"  - нет
    save_relayed_signals_locally_relay: bool = False

    def __eq__(self, other):
        return ((self.antenna_in == other.antenna_in) and (
            self.antenna_out == other.antenna_out) and (
                self.id_destination_relay == other.id_destination_relay) and (
                    self.id_antenna_destination_relay == other.id_antenna_destination_relay) and (
                        self.save_relayed_signals_locally_relay == other.save_relayed_signals_locally_relay))


class RadiotransmissionSystem:
    """
    Система учёта Приёмо-Передающих Устройств (ППУ) космического аппарата
    """
    # Игнорируем ошибки Too many instance attributes
    # pylint: disable=R0902

    def __init__(self, global_consumer: RadioTransmissionMediumConsumer):
        # Глобальная система радиосвязи
        self.__global_consumer = global_consumer
        # Словарь: ключ - id Потребителя, значение - экземляр класса Потребителя радиосвязи с данным id
        self.__consumers: Dict[int, 'RadiotransmissionConsumer'] = {}

        # Словарь: ключ - id приёмо-передающего устройства (ППУ),
        # значение - экземляр класса приёмо-передающего устройства с данным id
        self.__antennas: Dict[int, 'TransmitReceiveDevice'] = {}

        # Максимальная точность, с которой должны совпадать частота сигнала и частота,
        # на которую настроен Приёмник при получении этого сигнала
        self.frequency_accuracy: FrequencyType = FrequencyType(1)

        # Список каналов (ППУ), предназначенных для отправки сигналов
        self.list_transmission_channel: List['TransmitReceiveDevice'] = []

        # Словарь: ключ - id канала (ППУ), предназначенного для приёма сигналов
        # значение - канал (ППУ)
        self.dict_reception_channel: Dict[int, 'TransmitReceiveDevice'] = {}

        # Копия словаря, предназначенного для каналов приёма сигналов
        # Ключ - id канала (ППУ), предназначенного для приёма сигналов
        # значение - канал (ППУ)
        # Нужна для сохранения списка на следущий шаг моделирования, чтобы принять сигналы от глобальный потребителей
        self.dict_reception_channel_from_prev_step: Dict[int, 'TransmitReceiveDevice'] = {}

        # Список каналов, предназначенных для ретрансляции данных.
        self.list_relay_channel: List[RelayChannel] = []

        # Словарь: ключ - id ППУ, которое будет отправлять сигналы,
        # значение - список сигналов, которые должно отправить данное ППУ
        self.__dict_signals_to_send: Dict[int, List[Radiosignal]] = {}

        # # Словарь: ключ - частота, на которой пришёл сигнал,
        # # значение - список сигналов, пришедших на данной частоте, которые нужно ретранслировать другому КА
        # self.dict_frequency_signals_to_relay: Dict[int, List[Radiosignal]] = {}

        # Словарь: ключ - id антенны, которая приняла данный сигнал,
        # значение - список блоков памяти, полученных данной антенной
        self.dict_id_device_memory_blocks_to_receive: Dict[int, List[MemoryBlock]] = {}

        # Время имитационного шага
        self.__duration: Optional[int] = None

    @property
    def antennas(self):
        return self.__antennas

    def register_consumer(self,
                          consumer_properties: RadiotransmissionConsumerProperties) -> RadiotransmissionConsumer:
        """
        Метод регистрации (добавления в Систему) Потребителя ресурсов Системы радиосвязи

        :param consumer_properties: свойства Потребителя ресурсов Системы радиосвязи
        :return: Потребитель, добавленный в систему
        """
        id_consumer = len(self.__consumers)
        consumer = RadiotransmissionConsumer(consumer_properties)
        consumer.radiotransmission_system = self
        self.__consumers[id_consumer] = consumer
        return consumer

    def add_device(self, device_properties: TransmitReceiveDeviceProperties):
        """
        Добавление устройства в Систему радиосвязи.
        """
        # Убрал, так как для этого нужен доступ к другим модулям
        # energy_consumer_properties = select_applicable_consumer_props(IElectricityConsumerProperties,
        #                                                               available_consumer_props)
        # layout_consumer_properties = select_applicable_consumer_props(ILayoutDeviceConsumerProperties,
        #                                                               available_consumer_props)

        # Добавляем устройство в Систему радиосвязи, назначая ему id
        id_ = len(self.__antennas)
        self.__antennas[id_] = TransmitReceiveDevice(id_, device_properties)

    @property
    def consumer_properties_type(self) -> Type[RadiotransmissionConsumerProperties]:
        """
        Возвращает тип структуры, которая используется для задания свойств Потребителя Системы радиосвязи.
        """
        return RadiotransmissionConsumerProperties

    @property
    def categories_match(self):
        """
        Метод, возвращающий сведения о категориях объектов которые могут быть добавлены в Систему радиосвязи.

        :return: словарь, в котором ключ - это категории интересующих объектов,
        а значение - класс, который вы ожидаете получить при присоединении этого объекта к Системе.
        """
        categories_match = {"ППУ": TransmitReceiveDeviceProperties}
        return categories_match

    def get_state(self):
        """
        Возвращает структуру с данными полностью характеризующими состояние Системы в текущий момент.

        :return: словарь, в котором ключ - имя переменной, характеризующей состояние Системы в текущий момент,
        а значение - это значение данной перменной.
        """
        # current_state: Dict = {
        # return current_state

    def get_configuration(self):
        """
        Возвращает структуру, в которой описываются характеристики получившейся Системы после добавления всех устройств.

        :return: словарь, в котором ключ - имя характеристики Системы, а значение - значение данной характеристики
        """
        configuration: Dict = {"Число приёмо передающих устройств": len(self.__antennas),
                               "Число каналов, отправляющих сигналы": len(self.list_transmission_channel),
                               "Число каналов, принимающих сигналы": len(self.dict_reception_channel),
                               "Число каналов, ретранслирующих сигналы": len(self.list_relay_channel)}
        return configuration

    def assign_device_as_transmitter(self, memory_block: MemoryBlock, id_antenna: int,
                                     id_receiver: int, frequency: Optional[FrequencyType] = None,
                                     id_antenna_receiver: Optional[int] = None) -> bool:
        """
        Метод, для назначения приёмо-передающего устройства на отправку сигнала.
        Если этот метод не был вызван, соответствующий сигнал не будет передан от локальной системы радиосвязи
        в глобальную.

        :param memory_block: блок памяти, который нужно отправить с данного КА
        :param id_antenna: id ППУ, который должен отправить сигнал
        :param id_receiver: id приёмника
        :param frequency: частота, на которой нужно передать сигнал
        :param id_antenna_receiver: id антенны приёмника, которая должна принять сигнал
        """
        # Игнорируем ошибки Too many arguments
        # pylint: disable=R0913

        antenna = self.__antennas[id_antenna]
        # Проверяем, что данное ППУ уже не работает в другом режиме: ретрансляции или приёме
        if (antenna.communication_mode != CommunicationModeType.FREE) and (
                antenna.communication_mode != CommunicationModeType.TRANSMISSION):
            raise Exception('''The transmit-receive device with id = %d assigning for Transmission mode works on
            another mode on the imitation step''', id_antenna)
        # Проверяем, что данное ППУ уже не работает на другой частоте на данном имитационном шаге в том же режиме
        elif antenna in self.list_transmission_channel and (
                antenna.frequency != frequency and frequency is not None):
            raise Exception('''The transmit-receive device with id = %d assigning for Transmission mode
             is going to work on another frequency on the imitation step''', id_antenna)
        else:
            # Задаём режим работы ППУ
            antenna.communication_mode = CommunicationModeType.TRANSMISSION
            # Устанавливаем рабочую частоту ППУ
            if frequency:
                antenna.set_frequency(frequency)
            # Записываем сигнал в словарь c сигналами, которые нужно передать
            self.__dict_signals_to_send.setdefault(antenna.id_antenna, ([]))
            signal = Radiosignal(id_transmitter=-1, id_receiver=id_receiver, memory=memory_block,
                                 frequency=antenna.frequency, id_antenna_receiver=id_antenna_receiver)
            self.__dict_signals_to_send[antenna.id_antenna].append(signal)
            # Добавляем данное ППУ в список ППУ, которые отправляют сигнал
            if antenna not in self.list_transmission_channel:
                self.list_transmission_channel.append(antenna)
            return False

    def assign_device_as_receiver(self, id_antenna: int,
                                  frequency: Optional[FrequencyType] = None) -> bool:
        """
        Метод, для назначения приёмо-передающего устройства на приём сигнала.
        Если этот метод не был вызван, соответствующий сигнал не будет передан от локальной системы радиосвязи
        в глобальную.

        :param id_antenna: id ППУ, который должен принять сигнал
        :param frequency: частота, на которой нужно принимать сигнал
        """
        antenna = self.__antennas[id_antenna]
        # Проверяем, что данное ППУ уже не работает в другом режиме: ретрансляции или отправке
        if (antenna.communication_mode != CommunicationModeType.FREE) and (
                antenna.communication_mode != CommunicationModeType.RECEPTION):
            raise Exception('''The transmit-receive device with id = %d assigning for Reception mode works
            on another mode on the imitation step''', id_antenna)
        # Проверяем, что данное ППУ уже не работает на другой частоте на данном имитационном шаге в том же режиме
        elif antenna in self.dict_reception_channel.values() and (
                antenna.frequency != frequency):
            raise Exception('''The transmit-receive device with id = %d assigning for Reception mode is
            going to work on another frequency on the imitation step''', id_antenna)
        else:
            # Задаём режим работы ППУ
            antenna.communication_mode = CommunicationModeType.RECEPTION
            # Устанавливаем рабочую частоту ППУ
            if frequency:
                antenna.set_frequency(frequency)
            # Добавляем данное ППУ в список ППУ, которые принимают сигнал
            if id_antenna not in self.dict_reception_channel:
                self.dict_reception_channel[id_antenna] = antenna
            return True

    def assign_device_as_repeater(self, id_antenna_in: int, id_antenna_out: int,
                                  id_destination_relay: int, id_antenna_destination_relay: Optional[int] = None,
                                  frequency_in: Optional[FrequencyType] = None,
                                  frequency_out: Optional[FrequencyType] = None,
                                  save_relayed_signals_locally_relay: bool = False) -> bool:
        """
        Метод, для назначения приёмо-передающего устройства на ретрансляцию сигнала.
        Если этот метод не был вызван, соответствующий сигнал не будет передан от локальной системы радиосвязи
        в глобальную.

        :param id_antenna_in: id ППУ, который должен принять ретранслируемый сигнал
        :param id_antenna_out: id ППУ, который должен отправить ретранслируемый сигнал
        :param id_destination_relay: id приёмника, на который нацелен ретранслятор
        :param id_antenna_destination_relay: id антенны приёмника, на которую будет отправлен сигнал при ретрансляции
        :param frequency_in: частота, на которой нужно принимать ретранслируемый сигнал
        :param frequency_out: частота, на которой нужно отправлять ретранслируемый сигнал
        :param save_relayed_signals_locally_relay: индикатор, отвечающий за то,
                                                   будут ли в локальных Потребителях радиосвязи
                                                   сохраняться ретранслируемые сигналы
        """
        # Игнорируем ошибки Too many arguments
        # pylint: disable=R0913

        antenna_in = self.__antennas[id_antenna_in]
        antenna_out = self.__antennas[id_antenna_out]
        # Проверяем, что данное ППУ уже не работает в другом режиме: приёме при рентрансляции или просто приёме
        if (antenna_in.communication_mode != CommunicationModeType.FREE) and (
                antenna_in.communication_mode != CommunicationModeType.RELAYING_IN):
            raise Exception('''The transmit-receive device with id = %d assigning for Relaying_in mode
            works on another mode on the imitation step''', id_antenna_in)
        # Проверяем, что данное ППУ уже не работает в другом режиме: отправке при рентрансляции или просто отправке
        elif (antenna_in.communication_mode != CommunicationModeType.FREE) and (
                antenna_in.communication_mode != CommunicationModeType.RELAYING_OUT):
            raise Exception('''The transmit-receive device with id = %d assigning for Relaying_out mode
            works on another mode on the imitation step''', id_antenna_out)
        # Проверяем, что данное ППУ уже не работает на другой частоте на данном имитационном шаге
        elif (antenna_in in [
                device.antenna_in for device in self.list_relay_channel] and (
                    antenna_in.frequency)):
            raise Exception('''The transmit-receive device with id = %d assigning for Relaying_in mode
             is going to work on another frequency on the imitation step''', id_antenna_in)
        # Проверяем, что данное ППУ уже не работает на другой частоте на данном имитационном шаге
        elif (antenna_out in [
                device.antenna_out for device in self.list_relay_channel] and (
                    antenna_out.frequency)):
            raise Exception('''The transmit-receive device with id = %d assigning for Relaying_out mode
             is going to work on another frequency on the imitation step''', id_antenna_out)
        else:
            # Задаём режим работы ППУ
            antenna_in.communication_mode = CommunicationModeType.RELAYING_IN
            antenna_out.communication_mode = CommunicationModeType.RELAYING_OUT
            # Устанавливаем рабочую частоту ППУ
            if frequency_in:
                antenna_in.set_frequency(frequency_in)
            if frequency_out:
                antenna_out.set_frequency(frequency_out)
            # Добавляем данный набор ППУ в список каналов ретрансляции
            relay_channel = RelayChannel(antenna_in=antenna_in,
                                         antenna_out=antenna_out,
                                         id_destination_relay=id_destination_relay,
                                         id_antenna_destination_relay=id_antenna_destination_relay,
                                         save_relayed_signals_locally_relay=save_relayed_signals_locally_relay)
            if relay_channel not in self.list_relay_channel:
                self.list_relay_channel.append(relay_channel)
            return True

    def finalize_step(self):
        """
        Метод, передающий принятые сигналы от глобального Потребителя в локальную Систему радиосвязи
        """
        # Получаем от глобального Потребителя сигналы,
        # которые пришли на данный КА с имитационного шага глобальной Системы
        for id_antenna in self.dict_reception_channel_from_prev_step:
            antenna = self.dict_reception_channel_from_prev_step[id_antenna]
            for signal in self.__global_consumer.receive_signal(
                    frequency=antenna.frequency):
                # Проверяем совпадают ли номер антенны с указанным в сигнале номером антенны,
                # на которую должен прийти сигнал,
                # и что у антенны достаточно пропускной способности, чтобы принять сигнал
                if (signal.id_antenna_receiver == id_antenna) and (
                        antenna.properties.channel_capacity_receive >= (
                        signal.memory.size / self.__duration)):
                    self.dict_id_device_memory_blocks_to_receive.setdefault(
                        id_antenna, ([]))
                    self.dict_id_device_memory_blocks_to_receive[id_antenna].append(
                        signal.memory)

    def imitation_step(self, duration: float):
        """
        Метод, имитирующий работу Системы, который вызывается каждый шаг имитационного моделирования.

        :param duration: время шага в секундах
        """
        self.__duration = duration
        # Игнорируем ошибки Too many branches
        # pylint: disable=R0912

        # Цикл отправки сигналов от Потребителей Системы радиосвязи
        for id_antenna in self.__dict_signals_to_send:
            antenna = self.__antennas[id_antenna]
            for signal in self.__dict_signals_to_send[id_antenna]:
                # Проверяем, что у ППУ достаточно пропускной способности,
                # чтобы передать данный объём информации за шаг моделирования
                if (antenna.properties.channel_capacity_transmit >= (
                        signal.memory.size / duration)):
                    # Задаём режим работы ППУ
                    antenna.communication_mode = CommunicationModeType.TRANSMISSION
                    # Включаем энергопотребление ППУ
                    antenna.set_consumption()
                    # Передаём в глобального Потребителя сигнал, который нужно отправить с помощью Потребителя-Адаптера
                    self.__global_consumer.send_signal(id_receiver=signal.id_receiver,
                                                       memory=signal.memory,
                                                       frequency=signal.frequency,
                                                       id_antenna_receiver=signal.id_antenna_receiver)

                # У данного ППУ недостаточно пропускной способности для отправки сигнала за один имитационный шаг
                else:
                    raise Exception('''This transmit-receive device with id = %d has not enough channel
                    capacity to send the signal''', id_antenna)

        # Включаем энергопотребление и задаём режим работы ППУ , которые слушают эфир и
        # отправляем от локальной Системы радиосвязи в глобального Потребителя запрос
        # на прослушивание эфира на заданных частотах, на которые настроены ППУ для приёма сигнала
        for antenna in self.dict_reception_channel.values():
            antenna.communication_mode = CommunicationModeType.RECEPTION
            antenna.set_consumption()
            self.__global_consumer.listen_ether(
                frequency_recipiency=antenna.frequency,
                id_antenna_receiver=antenna.id_antenna)

        # Включаем энергопотребление и задаём режим работы ППУ для ретрансляции и
        # отправляем от локальной Системы радиосвязи в глобального Потребителя запрос
        # на ретрансляцию сигналов с использованием выделенных ППУ
        for channel in self.list_relay_channel:
            antenna_in = channel.antenna_in
            antenna_out = channel.antenna_out
            antenna_in.communication_mode = CommunicationModeType.RELAYING_IN
            antenna_in.set_consumption()
            antenna_out.communication_mode = CommunicationModeType.RELAYING_OUT
            antenna_out.set_consumption()
            self.__global_consumer.i_am_repeater(
                id_destination_relay=channel.id_destination_relay,
                id_antenna_destination_relay=channel.id_antenna_destination_relay,
                frequency_recipiency=antenna_in.frequency,
                frequency_transmission_relay=antenna_out.frequency,
                save_relayed_signals_locally_relay=channel.save_relayed_signals_locally_relay,
                id_antenna_receiver=antenna_in.id_antenna)

        # Обнуляем копию списка каналов для приёма сигналов
        self.dict_reception_channel_from_prev_step.clear()

        # Записываем каналы приёма с этого имитационного шага в копию,
        # чтобы принять сигналы на следующем шаге
        self.dict_reception_channel_from_prev_step = deepcopy(self.dict_reception_channel)

        # Обнуляем словари, в которых хранились принятые Системой сигналы
        self.dict_id_device_memory_blocks_to_receive.clear()

        # Очищаем словарь, в котором хранились сигналы для отправки
        self.__dict_signals_to_send.clear()

        # Очищаем каналы отправки, приёма и ретрансляции сигналов
        self.list_transmission_channel.clear()
        self.dict_reception_channel.clear()
        self.list_relay_channel.clear()

        # Обнуляем режим работы каждого ППУ
        for id_antenna in self.__antennas:
            self.__antennas[id_antenna].communication_mode = CommunicationModeType.FREE

        # Очищаем у Потребителей словарь отправленных сигналов и
        # список, использованных для приёма и ретрансляции каналов связи
        for id_consumer in self.__consumers:
            self.__consumers[id_consumer].clear_tasks()
