"""
В данном модуле описана глобальная подсистема радиосвязи, которая будет передавать сигналы между спутниками.
"""
from copy import deepcopy
from typing import List, Dict, Optional
import logging
from integral_d.imitation_experiment.interfaces.resource_manager import IResourceManagerGlobal

from auxiliary_classes import (Radiosignal,ListenEtherTask, FrequencyType, MemoryBlock)


class RadioTransmissionMediumConsumerProperties:
    """
    Класс свойств устройства, отправляющего или принимающего радиосигнал.
    """
    def __init__(self, frequency, id_consumer):
        self.frequency: FrequencyType = frequency # частота несущей [МГц]
        self.id_consumer: int = id_consumer  # id Потребителя


class RadioTransmissionMediumConsumer:
    """
    Класс устройства, отправляющего или принимающего радиосигнал.
    """

    def __init__(self, properties):
        self.__properties = deepcopy(properties)

        # Словарь: ключи - id приёмника, значения - список сигналов, которые предназчены для данного приёмника
        self.dict_id_receiver_signals_to_send: Dict[int, List[Radiosignal]] = {}

        # Словарь: ключи - частота несущей, на которой перадётся сигнал для Потребителя на имитационном шаге,
        # значение - список блоков памяти, передаваемых на данной частоте
        self.dict_frequency_signal_to_receive: Dict[int, List[Radiosignal]] = {}

        # Список каналов, на которых может работать Потребитель для приёма сигнала и ретрансляции
        self.listen_ether_tasks: List[ListenEtherTask] = []

        # Словарь: ключи - ключи - частота несущей, на которой перадётся сигнал для Потребителя на имитационном шаге,
        # значение - список всех сигналов, полученных Потребителем за имитационный шаг на данной частоте.
        # Необходим для того, чтобы избежать ситуации, когда два ретранслятора зацикленно передают друг другу
        # один и тот же сигнал
        self.dict_getting_information: Dict[int, List[Radiosignal]] = {}

    def clear_tasks(self):
        """
        Метод, вызываемый в конце каждого имитационного шага системы среды радиосвязи после того,
        как все сигналы от передатчиков были отправлены.
        Очищает словарь сигналов, отправленных с передатчика, и список каналов, которыми пользовался Потребитель
        для приёма сигналов и ретрансляции.
        """
        self.dict_id_receiver_signals_to_send = {}
        self.listen_ether_tasks = []

    @property
    def properties(self):
        return self.__properties

    @properties.setter
    def properties(self, properties):
        self.__properties = deepcopy(properties)

    def send_signal(self, id_receiver, memory: MemoryBlock, frequency: Optional[FrequencyType],
                    id_antenna_receiver: Optional[int] = None) -> bool:
        """
        Метод, который вызывается Потребителем, когда он хочет отправить сигнал.

        :param id_receiver: id приёмника
        :param memory: блок памяти, в котором хранится сигнал
        :param frequency: частота несущей, на которой передаётся сигнал
        :param id_antenna_receiver: id антенны приёмника, которая должна принять сигнал
        :return: True, если удалось отправить сигнал, False - в противном случае
        """
        # Если frequency не задана, то присваиваем ей значение частоты Потребителя
        frequency = frequency or self.__properties.frequency

        id_transmitter = self.properties.id_consumer

        # Проверка, что Потребитель не отправляет сигнал сам себе
        if id_transmitter == id_receiver:
            return False

        signal = Radiosignal(id_transmitter=id_transmitter, id_receiver=id_receiver,
                             memory=memory, frequency=frequency, id_antenna_receiver=id_antenna_receiver)

        # Записываем сигнал в словарь, которые затем передадим в систему среды радиосвязи
        self.dict_id_receiver_signals_to_send.setdefault(signal.id_receiver, ([]))
        self.dict_id_receiver_signals_to_send[signal.id_receiver].append(signal)
        return True

    def receive_signal(self, frequency: FrequencyType = None) -> List[Radiosignal]:
        """
        Метод, который вызывается Потребителем для получения списка сигналов,
        полученных от других Потребителей на частоте frequency.

        :param frequency: частота, на которой Потребитель принимает сигнал
        :return: список сигналов, предназначенных для данного Потребителя
        """
        frequency = frequency or self.__properties.frequency
        # Возвращаем из словаря список сигналов, который соответствует ключу frequency
        return self.dict_frequency_signal_to_receive.get(int(frequency), [])

    def listen_ether(self, id_antenna_receiver: int, frequency_recipiency: FrequencyType = None) -> bool:
        """
        Потребитель заявляет, что он слушает эфир на заданной частоте frequency.
        Если этот метод не был выполнен, то сигнал не сможет быть получен, даже если передавался.
        Добавляем в список каналов прослушки Потребителя новый канал с заданной частотой frequency.

        :param id_antenna_receiver: id антенны приёмника, которая должна принять сигнал
        :param frequency_recipiency: частота на которой слушается эфир.
        :return: True - елсли удалось создать канал прослушки с заданнымми требованиями; False - в противном случае
        """
        # Проверяем, если уже данный канал в списке каналов прослушки Потребителя
        if ListenEtherTask(id_antenna_receiver=id_antenna_receiver,
                           frequency_recipiency=(frequency_recipiency or self.__properties.frequency)
                           ) not in self.listen_ether_tasks:
            # добавляем в массив каналов прослушки новый канал с заданной частотой
            self.listen_ether_tasks.append(ListenEtherTask(id_antenna_receiver=id_antenna_receiver,
                                                           frequency_recipiency=(frequency_recipiency or (
                                                               self.__properties.frequency))))
            return True
        else:
            return False

    def i_am_repeater(self, id_destination_relay,
                      id_antenna_receiver: int,
                      id_antenna_destination_relay: Optional[int] = None,
                      frequency_recipiency: Optional[FrequencyType] = None,
                      frequency_transmission_relay: Optional[FrequencyType] = None,
                      save_relayed_signals_locally_relay: bool = False) -> bool:
        """
        Метод, который вызывается Потребителем, когда он назначается ретранслятором.
        :param id_destination_relay: id приёмника, на который будет ретранслироваться сигнал
        :param id_antenna_receiver: id антенны приёмника, которая должна принять сигнал
        :param id_antenna_destination_relay: id антенны приёмника, на которую будет отправлен сигнал при ретрансляции
        :param frequency_recipiency: частота, на которой ретранслятор принимает сигналы
        :param frequency_transmission_relay: частота, на которой ретранслятор передаёт сигналы
        :param save_relayed_signals_locally_relay: индикатор, отвечающий за то,
        будут ли в локальных Потребителях радиосвязи сохраняться ретранслируемые сигналы
        :return: True, если Потребителя удалось назначить ретранслятором, False - в противном случае
        """
        # Игнорируем ошибки Too many arguments
        # pylint: disable=R0913

        # Проверяем, не пытается ли ретранслятор отправить сигнал сам себе
        if self.properties.id_consumer == id_destination_relay:
            return False

        self.listen_ether_tasks.append(
            ListenEtherTask(
                id_antenna_receiver=id_antenna_receiver,
                frequency_recipiency=frequency_recipiency or self.__properties.frequency,
                frequency_transmission_relay=frequency_transmission_relay or self.__properties.frequency,
                id_antenna_destination_relay=id_antenna_destination_relay,
                id_destination_relay=id_destination_relay,
                save_relayed_signals_locally_relay=save_relayed_signals_locally_relay))
        return True

    def release(self):
        """
        Метод, который следует вызвать, если потребление ресурсов больше не нужно
        """
        self.dict_id_receiver_signals_to_send = {}
        self.dict_frequency_signal_to_receive = {}


class RadioTransmissionMediumSystem:
    """
    Класс системы среды распространения радиосигнала.
    """

    def __init__(self):
        # Словарь: ключи - id Потребителя, значения - экземляр класс Потребителя с данным id
        self.__consumers: Dict[int, 'RadioTransmissionMediumConsumer'] = {}

        # Максимальная точность, с которой должны совпадать частота сигнала и частота,
        # на которую настроен Приёмник при получении этого сигнала
        self.frequency_accuracy: FrequencyType = FrequencyType(1e1)

    @property
    def consumer_properties_type(self):
        """
        Тип который следует использовать для задания свойств потребителя.
        """
        return RadioTransmissionMediumConsumerProperties

    def imitation_step(self, duration: float) -> bool:
        """
        Данный метод вызывается каждый шаг имитационного моделирования
        :param duration: длительность шага по времени
        :return: True - если имитационный шаг завершился успешно
        """
        # Обнуляем словарь, в котором хранятся списки сигналов для приёма
        for id_consumer in self.__consumers:
            self.__consumers[id_consumer].dict_frequency_signal_to_receive = {}
            self.__consumers[id_consumer].dict_getting_information = {}

        # Цикл передачи всех сигналов от Отправителей Приёмникам включая циклы ретрансляции
        for id_consumer in self.__consumers:
            consumer = self.__consumers[id_consumer]
            # Для каждого сигнала, который хотел отправить Потребитель, проводим цикл передачи
            for id_receiver in consumer.dict_id_receiver_signals_to_send:
                for signal in consumer.dict_id_receiver_signals_to_send[id_receiver]:
                    self.add_signal(signal)

        # У каждого Потребителя очищаем словарь сигналов, которые он отправил, и
        # список каналов, которыми он пользовался для приёма сигналов и ретрансляции.
        for id_consumer in self.__consumers:
            self.__consumers[id_consumer].clear_tasks()
        return True

    def add_signal(self, signal: Radiosignal) -> None:
        """
        Метод отправки сигнала от передатчика конечному приёмнику с учётом ретрансляции.
        :param signal: сигнал, который хотим добавить
        """

        # Проверяем, есть ли необходимый Приёмник в списке Потребителей
        if signal.id_receiver not in self.__consumers:
            return

        recipient = self.__consumers[signal.id_receiver]
        # Проверяем, может ли какой-то из активных каналов Приёмника получить данный сигнал
        # Проходим цикл по всем активным каналам Приёмника
        for listener in recipient.listen_ether_tasks:
            # Проверяем соответствие частот Приёмника и сигнала с заданной точностью frequency_accurac
            assert listener.id_antenna_receiver is not None
            if listener.id_antenna_receiver is None:
                raise Exception("Attribute id_antenna_receiver is None.")
            if self.can_consumer_receive_signal_by_frequency(signal.frequency, listener.frequency_recipiency) and (
                    self.can_consumer_receive_signal_by_antenna(
                        signal.id_antenna_receiver, listener.id_antenna_receiver)):
                key = int(listener.frequency_recipiency)
                # Проверяем, приходил ли нам уже этот сигнал.
                # Если сигнала ещё не было, то записываем в словарь всех полученных сигналов по соотвествующему ключу.
                # Если такой сигнал уже был, то что-то тут не то. Вероятно ретрансляторы циклично передают друг другу.
                if signal not in recipient.dict_getting_information.setdefault(key, ([])):
                    recipient.dict_getting_information[key].append(signal)
                    # Проверяем, является данный канал передачи ретранслирующим. Если да, то запускаем цикл ретрансляций
                    if listener.id_destination_relay is not None:
                        # Запускаем цикл ретрансляций
                        # Проверяем, необходимо ли локальному Потребителю передавать ретранслируемые сигналы
                        if listener.save_relayed_signals_locally_relay:
                            recipient.dict_frequency_signal_to_receive.setdefault(key, ([]))
                            recipient.dict_frequency_signal_to_receive[key].append(signal)
                        # Запускаем рекурсию, если Приёмник, который получил сигнал является ретранслятором
                        signal.id_receiver = listener.id_destination_relay
                        assert listener.frequency_transmission_relay is not None
                        if listener.frequency_transmission_relay is None:
                            raise Exception("Attribute frequency_transmission_relay is None.")
                        signal.frequency = listener.frequency_transmission_relay
                        signal.id_antenna_receiver = listener.id_antenna_destination_relay
                        self.add_signal(signal)
                    else:
                        # Если ретранслировать сигнал не надо, то сохраняем его в данном глобальном приёмнике,
                        # чтобы потом сигнал попал в локального Потребителя радиосвязи
                        recipient.dict_frequency_signal_to_receive.setdefault(key, ([]))
                        recipient.dict_frequency_signal_to_receive[key].append(signal)

    def register_consumer(self, consumer_properties: RadioTransmissionMediumConsumerProperties
                          ) -> RadioTransmissionMediumConsumer:
        """
        Добавляет нового Потребителя в систему.
        :param consumer_properties: свойства Потребителя
        :return: Потребитель, добавленный в систему
        """
        id_consumer = consumer_properties.id_consumer
        if id_consumer not in self.__consumers:
            consumer = RadioTransmissionMediumConsumer(consumer_properties)
            self.__consumers[id_consumer] = consumer
        return self.__consumers[id_consumer]

    def can_consumer_receive_signal_by_frequency(self, signal_frequency: FrequencyType,
                                                 receiver_frequency: FrequencyType) -> bool:
        """
        Метод, проверяющий совпадение частот сигнала и приёмника с некоторой заданной погрешностью frequency_accuracy

        :param signal_frequency: частота, на которой передаётся сигнал
        :param receiver_frequency: частота, на которой слушает приёмник

        :return: True - если частоты совпадают с заданной погрешностью; False - если частоты не совпадают
        """
        return abs(signal_frequency - receiver_frequency) < self.frequency_accuracy

    def can_consumer_receive_signal_by_antenna(self, signal_id_antenna: Optional[int],
                                               receiver_id_antenna: int) -> bool:
        """
        Метод, проверяющий работает ли в режиме прослушивания антенна, id которой указан в радиосигнале.
        Если id антенны, указанный в сигнале равен None, то значит он не был указан при отправке и
        данная проверка игнорируется.

        :param signal_id_antenna: id антенны, записанный в радиосигнале
        :param receiver_id_antenna: id антенны приёмника, слушающей эфир

        :return: True - если указанные id совпадают, False - если id не совпадают
        """
        # pylint: disable=R0201
        return signal_id_antenna == receiver_id_antenna
